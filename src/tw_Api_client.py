# src/tw_Api_client.py

import os
import time
import random
from datetime import datetime, timedelta
from io import StringIO
from dotenv import load_dotenv
import pandas as pd
import requests
import yfinance as yf
try:
    from src.i18n import t
except ModuleNotFoundError:
    from i18n import t

# 載入 config 設定
try:
    from config import ENABLE_RANDOM_JITTER, JITTER_MIN_SEC, JITTER_MAX_SEC, get_yfinance_session
except ImportError:
    ENABLE_RANDOM_JITTER = True
    JITTER_MIN_SEC = 0.5
    JITTER_MAX_SEC = 1.2
    from curl_cffi import requests as curl_requests
    def get_yfinance_session():
        return curl_requests.Session(impersonate="chrome110")

load_dotenv()

# -------------------------------------------------------------------
# 全域快取與變數設定
# -------------------------------------------------------------------
TARGET_PRICE_CACHE = {}
TARGET_PRICE_CACHE_TTL = 3600  # 快取 1 小時
TW_STOCK_LIST_CACHE = None
TW_STOCK_LIST_CACHE_AT = 0

# -------------------------------------------------------------------
# 輔助函式
# -------------------------------------------------------------------

def _apply_random_jitter():
    """在發起外部 API 請求前套用隨機浮動延遲"""
    if ENABLE_RANDOM_JITTER:
        delay = random.uniform(JITTER_MIN_SEC, JITTER_MAX_SEC)
        time.sleep(delay)


def _format_tw_symbol(symbol: str) -> str:
    """自動修正台股代碼後綴 (預設優先加 .TW，若已帶 .TW/.TWO 則保留)"""
    symbol_upper = symbol.strip().upper()
    if symbol_upper.endswith(".TW") or symbol_upper.endswith(".TWO"):
        return symbol_upper
    return f"{symbol_upper}.TW"


def _format_dataframe_prices(df: pd.DataFrame) -> pd.DataFrame:
    """將 DataFrame 中的價格欄位四捨五入至小數點後兩位"""
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if col in df.columns:
            df[col] = df[col].round(2)
    return df

# -------------------------------------------------------------------
# 0. 全市場股票清單抓取 (涵蓋 上市/上櫃/ETF/TDR/興櫃)
# -------------------------------------------------------------------

def get_full_tw_stock_list() -> list:
    """獲取台股全市場清單 (涵蓋上市、上櫃、ETF、TDR、興櫃)"""
    global TW_STOCK_LIST_CACHE, TW_STOCK_LIST_CACHE_AT
    current_time = time.time()

    # 一天內使用記憶體快取
    if TW_STOCK_LIST_CACHE and (current_time - TW_STOCK_LIST_CACHE_AT < 86400):
        return TW_STOCK_LIST_CACHE

    url_configs = [
        {'name': 'listed', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?market=1&issuetype=1&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'dr', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=1&issuetype=J&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'otc', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?market=2&issuetype=4&Page=1&chklike=Y', 'suffix': '.TWO'},
        {'name': 'etf', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=1&issuetype=I&industry_code=&Page=1&chklike=Y', 'suffix': '.TW'},
        {'name': 'rotc', 'url': 'https://isin.twse.com.tw/isin/class_main.jsp?owncode=&stockname=&isincode=&market=E&issuetype=R&industry_code=&Page=1&chklike=Y', 'suffix': '.TWO'},
    ]

    all_items = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for cfg in url_configs:
        try:
            _apply_random_jitter()
            resp = requests.get(cfg['url'], timeout=15, headers=headers)
            df_list = pd.read_html(StringIO(resp.text), header=0)
            if not df_list:
                continue
            df = df_list[0]
            for _, row in df.iterrows():
                code = str(row['有價證券代號']).strip()
                name = str(row['有價證券名稱']).strip()
                if code and '有價證券' not in code:
                    all_items.append({"symbol": f"{code}{cfg['suffix']}", "name": name, "raw_code": code})
        except Exception:
            continue

    TW_STOCK_LIST_CACHE = all_items
    TW_STOCK_LIST_CACHE_AT = current_time
    return all_items

# -------------------------------------------------------------------
# 1. K線資料抓取 (對齊 fetch_stock_data 參數)
# -------------------------------------------------------------------

def fetch_yfinance_bars(symbol: str, days: int = 120, lang: str = "zh") -> pd.DataFrame:
    """從 yfinance 抓取台股 K 線資料"""
    formatted_symbol = _format_tw_symbol(symbol)
    _apply_random_jitter()
    
    session = get_yfinance_session()
    ticker = yf.Ticker(formatted_symbol, session=session)
    df = ticker.history(period=f"{days}d")

    # 若抓不到資料且沒有 .TWO，嘗試切換上櫃 .TWO 再次抓取
    if df.empty and formatted_symbol.endswith(".TW"):
        alt_symbol = formatted_symbol.replace(".TW", ".TWO")
        _apply_random_jitter()
        ticker = yf.Ticker(alt_symbol, session=session)
        df = ticker.history(period=f"{days}d")

    if df.empty:
        raise ValueError(t("ERR_YFINANCE_NO_DATA", lang, symbol=symbol))

    df = df.reset_index()
    df = df.rename(columns={
        "Date": "timestamp",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df = df.dropna(subset=['open', 'high', 'low', 'close']).reset_index(drop=True)

    if df.empty:
        raise ValueError(t("ERR_CLEANED_DATA_EMPTY", lang, symbol=symbol))

    return _format_dataframe_prices(df)


def fetch_stock_data(symbol: str, days: int = 120, source: str = 'yfinance', lang: str = "zh") -> pd.DataFrame:
    """與美股保持完全相同介面：抓取股票 K 線資料"""
    return fetch_yfinance_bars(symbol, days, lang=lang)

# -------------------------------------------------------------------
# 2. 新聞資料抓取 (對齊 fetch_stock_news 參數)
# -------------------------------------------------------------------

def fetch_yfinance_news(symbol: str, limit: int = 5, lang: str = "zh") -> list:
    """從 yfinance 抓取台股相關新聞"""
    formatted_symbol = _format_tw_symbol(symbol)
    _apply_random_jitter()
    
    session = get_yfinance_session()
    ticker = yf.Ticker(formatted_symbol, session=session)
    news_items = ticker.news or []

    results = []
    for item in news_items[:limit]:
        title = ""
        url = ""
        pub_time = "N/A"

        if isinstance(item, dict) and "content" in item and isinstance(item["content"], dict):
            title = item["content"].get("title", "")
            url = item["content"].get("canonicalUrl", {}).get("url", "")
            pub_time = item["content"].get("pubDate", "N/A")

        if not title and isinstance(item, dict):
            title = item.get("title") or item.get("headline", "")
            url = item.get("link") or item.get("url", "")
            if item.get("providerPublishTime"):
                pub_time = datetime.fromtimestamp(item["providerPublishTime"]).strftime('%Y-%m-%d %H:%M')

        results.append({
            "created_at": pub_time,
            "headline": title if title else t("NO_NEWS_TITLE", lang),
            "url": url,
            "source": "yfinance"
        })
    return results


def fetch_stock_news(symbol: str, limit: int = 5, source: str = 'yfinance', lang: str = "zh") -> list:
    """與美股保持完全相同介面：抓取個股新聞"""
    return fetch_yfinance_news(symbol, limit, lang=lang)

# -------------------------------------------------------------------
# 3. 分析師目標價抓取 (對齊 fetch_analyst_target_price 參數)
# -------------------------------------------------------------------

def fetch_analyst_target_price(symbol: str, source: str = 'yfinance', lang: str = "zh") -> dict:
    """與美股保持完全相同介面：抓取分析師目標價"""
    formatted_symbol = _format_tw_symbol(symbol)
    current_time = time.time()

    if formatted_symbol in TARGET_PRICE_CACHE:
        cached_data, cached_at = TARGET_PRICE_CACHE[formatted_symbol]
        if current_time - cached_at < TARGET_PRICE_CACHE_TTL:
            return cached_data

    try:
        _apply_random_jitter()
        session = get_yfinance_session()
        ticker = yf.Ticker(formatted_symbol, session=session)
        info = ticker.info

        target_mean = info.get("targetMeanPrice", None)
        target_high = info.get("targetHighPrice", None)
        target_low = info.get("targetLowPrice", None)

        result = {
            "target_mean": round(target_mean, 2) if isinstance(target_mean, (int, float)) else None,
            "target_high": round(target_high, 2) if isinstance(target_high, (int, float)) else None,
            "target_low": round(target_low, 2) if isinstance(target_low, (int, float)) else None,
            "source": "yfinance"
        }

        TARGET_PRICE_CACHE[formatted_symbol] = (result, current_time)
        return result

    except Exception as e:
        if formatted_symbol in TARGET_PRICE_CACHE:
            return TARGET_PRICE_CACHE[formatted_symbol][0]
        return {
            "target_mean": None,
            "target_high": None,
            "target_low": None,
            "source": "yfinance"
        }

# -------------------------------------------------------------------
# 4. 選擇權比率 (從臺灣期貨交易所 TAIFEX OpenAPI 抓取)
# -------------------------------------------------------------------

def fetch_options_ratio(
    symbol: str = "",
    min_days_out: int = 3,
    source: str = "taifex",
    lang: str = "zh"
) -> dict:
    """
    雙軌備援：優先抓取個股選擇權，若無成交量或 API 拒絕，
    自動降級回大盤 Put/Call Ratio，並透過 i18n 標註狀態。
    """
    _apply_random_jitter()
    clean_symbol = "".join(filter(str.isdigit, str(symbol)))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    # 1. 優先嘗試抓取個股選擇權
    if clean_symbol:
        try:
            stk_url = "https://openapi.taifex.com.tw/v1/DailyStkOPT"
            resp = requests.get(stk_url, headers=headers, timeout=10)
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                c_vol = sum(int(r.get("Volume", 0) or 0) for r in data if clean_symbol in str(r.get("SecurityID") or r.get("UnderlyingID") or "") and str(r.get("CallPut", "")).upper().startswith("C"))
                p_vol = sum(int(r.get("Volume", 0) or 0) for r in data if clean_symbol in str(r.get("SecurityID") or r.get("UnderlyingID") or "") and str(r.get("CallPut", "")).upper().startswith("P"))
                
                if c_vol > 0:
                    return {
                        "put_call_ratio": round(p_vol / c_vol, 3),
                        "expiration": None,
                        "data_type": t("OPTIONS_DATA_TYPE_STOCK", lang),
                        "usable": True,
                        "detail": {"symbol": clean_symbol, "put_vol": p_vol, "call_vol": c_vol},
                        "source": "TAIFEX"
                    }
        except Exception:
            pass  # 個股抓取失敗或無量，自動跳過並降級至大盤

    # 2. 自動降級：抓取全市場大盤 Put/Call Ratio
    try:
        mkt_url = "https://openapi.taifex.com.tw/v1/PutCallRatio"
        resp = requests.get(mkt_url, headers=headers, timeout=10)
        if resp.status_code == 200 and resp.text.strip():
            latest = resp.json()[-1]
            p_vol = int(latest.get("PutVolume", 0))
            c_vol = int(latest.get("CallVolume", 0))
            p_c = float(latest.get("PutCallRatio", 0)) or (p_vol / c_vol if c_vol > 0 else None)
            
            if p_c:
                if p_c > 10: p_c /= 100.0
                return {
                    "put_call_ratio": round(p_c, 3),
                    "expiration": None,
                    "data_type": t("OPTIONS_DATA_TYPE_MARKET_FALLBACK", lang),
                    "usable": True,
                    "detail": {
                        "note": t("OPTIONS_DATA_TYPE_MARKET_FALLBACK", lang),
                        "date": latest.get("Date")
                    },
                    "source": "TAIFEX"
                }
    except Exception:
        pass

    # 3. 極端異常無網路狀態
    return {
        "put_call_ratio": None,
        "expiration": None,
        "data_type": t("OPTIONS_DATA_TYPE_DAILY_VOL", lang),
        "usable": False,
        "detail": t("OPTIONS_NO_MARKET_DATA", lang),
        "source": "TAIFEX"
    }

# -------------------------------------------------------------------
# 5. 股票名稱查詢 (對齊 fetch_stock_name 參數)
# -------------------------------------------------------------------

def fetch_stock_name(symbol: str) -> dict:
    """與美股保持完全相同介面：取得股票基本名稱"""
    formatted_symbol = _format_tw_symbol(symbol)
    try:
        _apply_random_jitter()
        session = get_yfinance_session()
        ticker = yf.Ticker(formatted_symbol, session=session)
        info = ticker.info
        stock_name = info.get("longName") or info.get("shortName") or symbol
        return {"symbol": formatted_symbol, "stock_name": stock_name}
    except Exception:
        return {"symbol": formatted_symbol, "stock_name": symbol}

if __name__ == "__main__":
    test_symbol = "2330"
    print(f"=== 開始測試台股代號: {test_symbol} ===\n")

    # 1. 測試 K線資料與成交量 (Volume & Candlestick 基礎)
    try:
        df_bars = fetch_stock_data(test_symbol, days=30)
        print("【1. K線資料與成交量 (fetch_stock_data)】")
        print(f"數據筆數: {len(df_bars)}")
        print(df_bars.tail(5))
        print(f"最新一日成交量: {df_bars['volume'].iloc[-1]}\n")
    except Exception as e:
        print(f"❌ K線資料抓取失敗: {e}\n")

    # 2. 測試 Put/Call 選擇權比率 (Options Ratio)
    try:
        pcr_data = fetch_options_ratio(test_symbol)
        print("【2. Put/Call 比率 (fetch_options_ratio)】")
        print(pcr_data)
        print()
    except Exception as e:
        print(f"❌ Put/Call 比率抓取失敗: {e}\n")

    # 3. 測試 分析師目標價 (Analyst Target Price)
    try:
        target_data = fetch_analyst_target_price(test_symbol)
        print("【3. 分析師目標價 (fetch_analyst_target_price)】")
        print(target_data)
        print()
    except Exception as e:
        print(f"❌ 分析師目標價抓取失敗: {e}\n")

    # 4. 測試 個股新聞 (Stock News)
    try:
        news_data = fetch_stock_news(test_symbol, limit=3)
        print("【4. 個股新聞 (fetch_stock_news)】")
        for idx, news in enumerate(news_data, 1):
            print(f"新聞 {idx}: {news.get('headline')} | 時間: {news.get('created_at')}")
        print()
    except Exception as e:
        print(f"❌ 個股新聞抓取失敗: {e}\n")

    print("=== 測試完成 ===")