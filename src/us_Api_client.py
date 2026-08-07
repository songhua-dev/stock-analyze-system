# src/us_Api_client.py

import os
import time
import random
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient, NewsClient
from alpaca.data.requests import StockBarsRequest, NewsRequest
from alpaca.data.timeframe import TimeFrame
from src.i18n import t

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

# 載入 .env 環境變數
load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# 初始化 Alpaca Clients
stock_client = None
news_client = None

if ALPACA_API_KEY and ALPACA_SECRET_KEY:
    stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)
    news_client = NewsClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)


# -------------------------------------------------------------------
# 全域快取設定 (In-Memory Cache)
# -------------------------------------------------------------------
TARGET_PRICE_CACHE = {}
TARGET_PRICE_CACHE_TTL = 3600  # 快取過期時間設定為 1 小時 (3600 秒)


# -------------------------------------------------------------------
# 輔助函式
# -------------------------------------------------------------------

def _apply_random_jitter():
    """在發起外部 API 請求前套用隨機浮動延遲，模擬真實操作間隔並降低 Rate Limit 風險"""
    if ENABLE_RANDOM_JITTER:
        delay = random.uniform(JITTER_MIN_SEC, JITTER_MAX_SEC)
        time.sleep(delay)


def _find_key_recursive(data, target_keys: list):
    """在巢狀字典或串列中，遞迴搜尋包含指定名稱的 key"""
    if isinstance(data, dict):
        for k, v in data.items():
            if any(tk in k.lower() for tk in target_keys) and isinstance(v, str) and v.strip():
                return v
            res = _find_key_recursive(v, target_keys)
            if res:
                return res
    elif isinstance(data, list):
        for item in data:
            res = _find_key_recursive(item, target_keys)
            if res:
                return res
    return None


def _format_dataframe_prices(df: pd.DataFrame) -> pd.DataFrame:
    """將 DataFrame 中的價格欄位四捨五入至小數點後兩位"""
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if col in df.columns:
            df[col] = df[col].round(2)
    return df


# -------------------------------------------------------------------
# 1. K線資料抓取 (Tri-Track: Alpaca / Finnhub / yfinance)
# -------------------------------------------------------------------

def fetch_alpaca_bars(symbol: str, days: int = 120, lang: str = "zh") -> pd.DataFrame:
    """從 Alpaca 抓取 K 線並統一欄位格式 (預設 120 天，明確指定 IEX Feed 避開 SIP 免費限制)"""
    if not stock_client:
        raise ValueError(t("ERR_NO_ALPACA_KEY", lang))

    _apply_random_jitter()

    # 免費版限制：歷史資料結束時間須為 16 分鐘以前
    end_time = datetime.now() - timedelta(minutes=16)
    start_time = end_time - timedelta(days=days)

    request_params = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start_time,
        end=end_time,
        feed=DataFeed.IEX  # 明確指定免費版可存取的 IEX 資料源
    )

    bars = stock_client.get_stock_bars(request_params)
    df = bars.df.reset_index()

    df = df.rename(columns={
        "timestamp": "timestamp",
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume"
    })

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    return _format_dataframe_prices(df)


def fetch_finnhub_bars(symbol: str, days: int = 120, lang: str = "zh") -> pd.DataFrame:
    """從 Finnhub 抓取 K 線並統一欄位格式"""
    if not FINNHUB_API_KEY:
        raise ValueError("Missing FINNHUB_API_KEY")

    _apply_random_jitter()
    to_time = int(time.time())
    from_time = int((datetime.now() - timedelta(days=days)).timestamp())

    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&from={from_time}&to={to_time}&token={FINNHUB_API_KEY}"
    res = requests.get(url, timeout=10)
    data = res.json()

    if data.get("s") != "ok":
        raise ValueError(f"Finnhub candle error for {symbol}")

    df = pd.DataFrame({
        "timestamp": pd.to_datetime(data["t"], unit="s"),
        "open": data["o"],
        "high": data["h"],
        "low": data["l"],
        "close": data["c"],
        "volume": data["v"]
    })

    return _format_dataframe_prices(df)


def fetch_yfinance_bars(symbol: str, days: int = 120, lang: str = "zh") -> pd.DataFrame:
    """從 yfinance 抓取 K 線並統一欄位格式 (預設 120 天)"""
    _apply_random_jitter()
    session = get_yfinance_session()
    ticker = yf.Ticker(symbol, session=session)
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


def fetch_stock_data(symbol: str, days: int = 120, source: str = 'alpaca', lang: str = "zh") -> pd.DataFrame:
    """統一切換介面：抓取股票 K 線資料 (防禦機制：指定來源 -> Alpaca -> Finnhub -> yfinance)"""
    sources_to_try = []
    if source.lower() in ['alpaca', 'finnhub', 'yfinance']:
        sources_to_try.append(source.lower())
    
    # 加入後備順序
    for s in ['alpaca', 'finnhub', 'yfinance']:
        if s not in sources_to_try:
            sources_to_try.append(s)

    last_error = None
    for src in sources_to_try:
        try:
            if src == 'alpaca':
                return fetch_alpaca_bars(symbol, days, lang=lang)
            elif src == 'finnhub':
                return fetch_finnhub_bars(symbol, days, lang=lang)
            elif src == 'yfinance':
                return fetch_yfinance_bars(symbol, days, lang=lang)
        except Exception as e:
            last_error = e

    raise last_error or ValueError(t("ERR_UNSUPPORTED_SOURCE", lang, source=source))


# -------------------------------------------------------------------
# 2. 新聞資料抓取
# -------------------------------------------------------------------

def fetch_alpaca_news(symbol: str, limit: int = 5, lang: str = "zh") -> list:
    """從 Alpaca 抓取新聞（精準解構 news 列表）"""
    if not news_client:
        raise ValueError(t("ERR_NO_ALPACA_KEY", lang))

    _apply_random_jitter()

    request_params = NewsRequest(symbols=symbol, limit=limit)
    news_res = news_client.get_news(request_params)

    news_dict = dict(news_res) if not isinstance(news_res, dict) else news_res
    raw_data = news_dict.get('data', {})
    if isinstance(raw_data, dict):
        news_items = raw_data.get('news', [])
    else:
        news_items = getattr(raw_data, 'news', [])

    results = []
    for item in news_items[:limit]:
        if hasattr(item, 'model_dump'):
            item_dict = item.model_dump()
        elif hasattr(item, 'dict'):
            item_dict = item.dict()
        elif hasattr(item, '__dict__'):
            item_dict = item.__dict__
        elif isinstance(item, dict):
            item_dict = item
        else:
            item_dict = {}

        headline = item_dict.get('headline') or getattr(item, 'headline', t("NO_NEWS_TITLE", lang))
        url = item_dict.get('url') or getattr(item, 'url', '')
        created_at = item_dict.get('created_at') or getattr(item, 'created_at', None)

        if isinstance(created_at, datetime):
            formatted_time = created_at.strftime('%Y-%m-%d %H:%M')
        else:
            formatted_time = str(created_at) if created_at else "N/A"

        results.append({
            "created_at": formatted_time,
            "headline": headline,
            "url": url,
            "source": "alpaca"
        })

    return results


def fetch_finnhub_news(symbol: str, limit: int = 5, lang: str = "zh") -> list:
    """從 Finnhub 抓取新聞"""
    if not FINNHUB_API_KEY:
        raise ValueError("Missing FINNHUB_API_KEY")

    _apply_random_jitter()
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"
    res = requests.get(url, timeout=10)
    items = res.json()

    results = []
    if isinstance(items, list):
        for item in items[:limit]:
            pub_time = datetime.fromtimestamp(item.get("datetime", 0)).strftime('%Y-%m-%d %H:%M') if item.get("datetime") else "N/A"
            results.append({
                "created_at": pub_time,
                "headline": item.get("headline", t("NO_NEWS_TITLE", lang)),
                "url": item.get("url", ""),
                "source": "finnhub"
            })
    return results


def fetch_yfinance_news(symbol: str, limit: int = 5, lang: str = "zh") -> list:
    """從 yfinance 抓取新聞 (含多層防禦性解析)"""
    _apply_random_jitter()
    session = get_yfinance_session()
    ticker = yf.Ticker(symbol, session=session)
    news_items = ticker.news

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

        if not title:
            found_title = _find_key_recursive(item, ["title", "headline"])
            title = found_title if found_title else t("NO_NEWS_TITLE", lang)

        if not url:
            found_url = _find_key_recursive(item, ["url", "link"])
            url = found_url if found_url else ""

        results.append({
            "created_at": pub_time,
            "headline": title,
            "url": url,
            "source": "yfinance"
        })
    return results


def fetch_stock_news(symbol: str, limit: int = 5, source: str = 'alpaca', lang: str = "zh") -> list:
    """統一切換介面：抓取個股新聞 (防禦機制：指定來源 -> Alpaca -> Finnhub -> yfinance)"""
    sources_to_try = []
    if source.lower() in ['alpaca', 'finnhub', 'yfinance']:
        sources_to_try.append(source.lower())
    
    for s in ['alpaca', 'finnhub', 'yfinance']:
        if s not in sources_to_try:
            sources_to_try.append(s)

    for src in sources_to_try:
        try:
            if src == 'alpaca':
                return fetch_alpaca_news(symbol, limit, lang=lang)
            elif src == 'finnhub':
                return fetch_finnhub_news(symbol, limit, lang=lang)
            elif src == 'yfinance':
                return fetch_yfinance_news(symbol, limit, lang=lang)
        except Exception:
            continue

    return []


# -------------------------------------------------------------------
# 3. 分析師目標價抓取 (防禦邏輯: Alpaca -> Finnhub -> yfinance)
# -------------------------------------------------------------------

def fetch_finnhub_target_price(symbol: str) -> dict:
    """從 Finnhub API 抓取目標價"""
    if not FINNHUB_API_KEY:
        raise ValueError("Missing FINNHUB_API_KEY")

    _apply_random_jitter()
    url = f"https://finnhub.io/api/v1/stock/price-target?symbol={symbol}&token={FINNHUB_API_KEY}"
    res = requests.get(url, timeout=10)
    data = res.json()

    target_mean = data.get("targetMean")
    target_high = data.get("targetHigh")
    target_low = data.get("targetLow")

    if target_mean is None and target_high is None and target_low is None:
        raise ValueError("Finnhub target price returned empty")

    return {
        "target_mean": round(target_mean, 2) if isinstance(target_mean, (int, float)) else None,
        "target_high": round(target_high, 2) if isinstance(target_high, (int, float)) else None,
        "target_low": round(target_low, 2) if isinstance(target_low, (int, float)) else None,
        "source": "finnhub"
    }


def fetch_yfinance_target_price(symbol: str) -> dict:
    """從 yfinance 抓取目標價"""
    _apply_random_jitter()
    session = get_yfinance_session()
    ticker = yf.Ticker(symbol, session=session)
    info = ticker.info

    target_mean = info.get("targetMeanPrice")
    target_high = info.get("targetHighPrice")
    target_low = info.get("targetLowPrice")

    return {
        "target_mean": round(target_mean, 2) if isinstance(target_mean, (int, float)) else None,
        "target_high": round(target_high, 2) if isinstance(target_high, (int, float)) else None,
        "target_low": round(target_low, 2) if isinstance(target_low, (int, float)) else None,
        "source": "yfinance"
    }


def fetch_analyst_target_price(symbol: str, source: str = 'alpaca', lang: str = "zh") -> dict:
    """
    抓取分析師目標價 (含快取機制與防禦鏈：Alpaca -> Finnhub -> yfinance)。
    註：Alpaca 原生 API 未直接提供目標價，因此內部會自動降級至 Finnhub -> yfinance。
    """
    symbol_upper = symbol.upper()
    current_time = time.time()

    # 1. 檢查快取
    if symbol_upper in TARGET_PRICE_CACHE:
        cached_data, cached_at = TARGET_PRICE_CACHE[symbol_upper]
        if current_time - cached_at < TARGET_PRICE_CACHE_TTL:
            return cached_data

    # 防禦鏈嘗試：Finnhub -> yfinance (Alpaca 無目標價端點)
    result = None

    # 嘗試 Finnhub
    try:
        result = fetch_finnhub_target_price(symbol_upper)
    except Exception as e:
        print(f"[TargetPrice] Finnhub fetch failed for {symbol_upper}: {e}")

    # 嘗試 yfinance
    if not result:
        try:
            result = fetch_yfinance_target_price(symbol_upper)
        except Exception as e:
            err_str = str(e)
            print(f"[TargetPrice] yfinance fetch failed for {symbol_upper}: {e}")
            if "Too Many Requests" in err_str or "Rate limited" in err_str or "429" in err_str:
                if symbol_upper in TARGET_PRICE_CACHE:
                    return TARGET_PRICE_CACHE[symbol_upper][0]
                raise ValueError("TARGET_PRICE_RATE_LIMITED")

    if result:
        TARGET_PRICE_CACHE[symbol_upper] = (result, current_time)
        return result

    # 後備過期快取或預設值
    if symbol_upper in TARGET_PRICE_CACHE:
        return TARGET_PRICE_CACHE[symbol_upper][0]

    return {
        "target_mean": None,
        "target_high": None,
        "target_low": None,
        "source": "none"
    }


# -------------------------------------------------------------------
# 4. Put/Call Ratio 選擇權比率抓取 (單軌：yfinance)
# -------------------------------------------------------------------

def fetch_options_ratio(symbol: str, min_days_out: int = 3, source: str = 'yfinance', lang: str = "zh") -> dict:
    """抓取選擇權鏈資料，計算 Put/Call Ratio"""
    _apply_random_jitter()
    session = get_yfinance_session()
    ticker = yf.Ticker(symbol, session=session)

    try:
        available_dates = ticker.options
    except Exception as e:
        return {"put_call_ratio": None, "expiration": None, "usable": False,
                "detail": t("OPTIONS_ERR_EXPIRATION_LIST", lang, error=e)}

    if not available_dates:
        return {"put_call_ratio": None, "expiration": None, "usable": False,
                "detail": t("OPTIONS_NO_MARKET_DATA", lang)}

    cutoff = datetime.now() + timedelta(days=min_days_out)
    target_date = None
    for date_str in available_dates:
        exp_date = datetime.strptime(date_str, "%Y-%m-%d")
        if exp_date >= cutoff:
            target_date = date_str
            break

    if target_date is None:
        target_date = available_dates[-1]

    try:
        _apply_random_jitter()
        chain = ticker.option_chain(target_date)
        call_vol = chain.calls['volume'].fillna(0).sum()
        put_vol = chain.puts['volume'].fillna(0).sum()
    except Exception as e:
        return {"put_call_ratio": None, "expiration": target_date, "usable": False,
                "detail": t("OPTIONS_ERR_CHAIN_FETCH", lang, error=e)}

    if not call_vol or call_vol == 0:
        return {"put_call_ratio": None, "expiration": target_date, "usable": False,
                "detail": t("OPTIONS_CALL_VOL_ZERO", lang)}

    ratio = round(float(put_vol) / float(call_vol), 3)

    return {
        "put_call_ratio": ratio,
        "expiration": target_date,
        "data_type": t("OPTIONS_DATA_TYPE_DAILY_VOL", lang), 
        "usable": True,
        "detail": t("OPTIONS_DETAIL_SUCCESS", lang, target_date=target_date)
    }


def fetch_stock_name(symbol: str) -> dict:
    """取得股票基本資訊（包含公司名稱）"""
    try:
        _apply_random_jitter()
        session = get_yfinance_session()
        ticker = yf.Ticker(symbol, session=session)
        info = ticker.info
        stock_name = info.get("longName") or info.get("shortName") or symbol
        return {"symbol": symbol, "stock_name": stock_name}
    except Exception:
        return {"symbol": symbol, "stock_name": symbol}