"""
Flask 主程式（路由層）
包含市場參數 (market) 的分流預留接口、共享快取控制與 Demo 模式開關：
- IS_DEMO_MODE: 讀取環境變數 DEMO_MODE，控制線上展示版與本機全功能版。
- SharedCache: 純後端記憶體共用快取，解決 429 Too Many Requests 問題。
"""

import os
import time
import unicodedata  # 用於全形轉半形
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, render_template

from src.i18n import t
import src.us_Api_client as us_api
import src.tw_Api_client as tw_api

from src.analyzer import analyze_stock
from src.recommendation_engine import format_analysis_output

from src.factors.rr_factor import calculate_rr_score
from src.factors.candlestick_factor import calculate_candlestick_score
from src.factors.volume_factor import calculate_volume_multiplier
from src.factors.news_factor import analyze_news_sentiment
from src.factors.put_call_ratio_factor import calculate_put_call_ratio_score
from src.factors.entry_price_factor import calculate_entry_price


# -----------------------------------------------------------------
# 🚀 0. 純資料層共享快取機制 (SharedCache)
# -----------------------------------------------------------------
class SharedCache:
    """純後端資料快取類別，不處理任何 UI/i18n，僅暫存 API 回傳物件"""
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._timestamp: Dict[str, float] = {}

    def get(self, key: str, ttl: int) -> Optional[Any]:
        if key in self._cache:
            if time.time() - self._timestamp[key] < ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamp[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._timestamp[key] = time.time()


# 全域共用快取實例與 TTL 設定 (秒)
global_cache = SharedCache()
CACHE_TTL_REALTIME = 120        # 即時行情/K線：2 分鐘
CACHE_TTL_NEWS = 300            # 新聞：5 分鐘
CACHE_TTL_AFTER_MARKET = 14400  # 盤後資料 (PCR/名稱)：4 小時


# -----------------------------------------------------------------
# 🌐 Flask 應用程式設定
# -----------------------------------------------------------------
app = Flask(__name__)
IS_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
last_request_time = {}

@app.route('/ping', methods=['GET'])
def ping():
    return 'ok', 200

@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return '', 204

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", is_demo=IS_DEMO_MODE)


@app.route("/api/analyze", methods=["GET"])
def analyze_route():
    lang = request.args.get("lang", "en").lower().strip()
    lang = "en" if lang.startswith("en") else "zh"

    market = request.args.get("market", "us").lower().strip()
    raw_symbol = request.args.get("symbol", "")
    symbol = unicodedata.normalize('NFKC', raw_symbol).upper().strip()

    if not symbol:
        return jsonify({"error": t("MAIN_ERR_SYMBOL_REQUIRED", lang)}), 400

    api_client = tw_api if market == "tw" else us_api

    factors_param = request.args.get("factors", "")
    selected_factors = [f.strip() for f in factors_param.split(",") if f.strip()]
    data_source = request.args.get("source", "alpaca")

    # Demo 模式防護
    if IS_DEMO_MODE:
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if client_ip and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        current_time = time.time()
        if client_ip in last_request_time:
            if current_time - last_request_time[client_ip] < 10:
                return jsonify({"error": t("MAIN_ERR_RATE_LIMIT", lang)}), 429

        last_request_time[client_ip] = current_time

        if "news" in selected_factors:
            return jsonify({"error": t("MAIN_ERR_DEMO_NEWS_BLOCKED", lang)}), 400

    # 1. 股票名稱 (純資料快取)
    cache_key_name = f"name_{market}_{symbol}"
    stock_name = global_cache.get(cache_key_name, ttl=CACHE_TTL_AFTER_MARKET)
    if stock_name is None:
        try:
            stock_info = api_client.fetch_stock_name(symbol)
            stock_name = stock_info.get("stock_name") if isinstance(stock_info, dict) else str(stock_info)
            global_cache.set(cache_key_name, stock_name)
        except Exception:
            stock_name = symbol

    # 2. 基礎 K線資料 (純資料快取)
    cache_key_df = f"df_{market}_{symbol}_{data_source}"
    df = global_cache.get(cache_key_df, ttl=CACHE_TTL_REALTIME)
    if df is None:
        try:
            df = api_client.fetch_stock_data(symbol, days=120, source=data_source, lang=lang)
            global_cache.set(cache_key_df, df)
        except Exception as e:
            err_str = str(e)
            if "Too Many Requests" in err_str or "Rate limited" in err_str or "429" in err_str:
                return jsonify({"error": t("MAIN_ERR_RATE_LIMITED", lang)}), 429
            return jsonify({"error": t("MAIN_ERR_FETCH_DATA_FAILED", lang, source=data_source, symbol=symbol)}), 500

    # 3. 分析師目標價 (純資料快取)
    cache_key_tp = f"tp_{market}_{symbol}_{data_source}"
    target_price_data = global_cache.get(cache_key_tp, ttl=CACHE_TTL_REALTIME)
    if target_price_data is None:
        try:
            target_price_data = api_client.fetch_analyst_target_price(symbol, source=data_source, lang=lang)
            if target_price_data:
                global_cache.set(cache_key_tp, target_price_data)
        except ValueError as e:
            if str(e) == "TARGET_PRICE_RATE_LIMITED":
                return jsonify({"error": t("MAIN_ERR_RATE_LIMITED", lang)}), 429
        except Exception as e:
            print(t("LOG_TARGET_PRICE_SKIPPED", lang, error=e))

    current_price = float(df['close'].iloc[-1])
    strong_support = float(df['close'].min())
    short_support = float(df['close'].iloc[-20:].min()) if len(df) >= 20 else strong_support

    # 4. 因子計算 (在此處才依據 lang 進行 i18n 渲染)
    factor_results = {}

    try:
        factor_results["candlestick"] = calculate_candlestick_score(df, lang=lang)
    except Exception as e:
        print(t("LOG_CANDLESTICK_FAILED", lang, error=e))

    if "rr" in selected_factors:
        rr_success = False
        try:
            if target_price_data and isinstance(target_price_data, dict):
                target_price = target_price_data.get("target_mean")
                if target_price is not None:
                    factor_results["rr"] = calculate_rr_score(current_price, strong_support, target_price, lang=lang)
                    rr_success = True
        except Exception as e:
            print(t("LOG_RR_FAILED", lang, error=e))

        if not rr_success:
            factor_results["rr"] = {
                "score": None,
                "detail": "Unable to obtain analyst target price (not scored)" if lang == "en" else "無法取得分析師目標價資料（不計入評分）"
            }

    if "news" in selected_factors:
        try:
            cache_key_news = f"news_{market}_{symbol}_{data_source}"
            news_res = global_cache.get(cache_key_news, ttl=CACHE_TTL_NEWS)
            if news_res is None:
                news_res = analyze_news_sentiment(symbol, limit=5, source=data_source, lang=lang)
                if news_res:
                    global_cache.set(cache_key_news, news_res)
            if news_res:
                factor_results["news"] = news_res
        except Exception as e:
            print(t("LOG_NEWS_FAILED", lang, error=e))

    if "put_call" in selected_factors:
        pc_success = False
        try:
            cache_key_pcr = f"pcr_{market}_{symbol}"
            options_data = global_cache.get(cache_key_pcr, ttl=CACHE_TTL_AFTER_MARKET)
            if options_data is None:
                options_data = api_client.fetch_options_ratio(symbol, min_days_out=3, lang=lang)
                if options_data and options_data.get("usable"):
                    global_cache.set(cache_key_pcr, options_data)

            if options_data and options_data.get("usable"):
                factor_results["put_call"] = calculate_put_call_ratio_score(
                    options_data.get("put_call_ratio"),
                    data_type=options_data.get("data_type"),
                    lang=lang
                )
                pc_success = True
        except Exception as e:
            print(t("LOG_PUTCALL_FAILED", lang, error=e))

        if not pc_success:
            factor_results["put_call"] = {
                "score": None,
                "detail": "Unable to obtain options data (not scored)" if lang == "en" else "無法取得選擇權資料（不計入評分）"
            }

    # 5. 進場價與算式整合
    try:
        volume_result = calculate_volume_multiplier(df, lang=lang)
    except Exception:
        volume_result = {"multiplier": 1.0, "detail": ""}

    try:
        entry_price_data = calculate_entry_price(current_price, short_support, strong_support, lang=lang)
    except Exception as e:
        print(t("LOG_ENTRY_PRICE_FAILED", lang, error=e))
        entry_price_data = {"available": False, "detail": ""}

    try:
        analysis_result = analyze_stock(
            df=df,
            target_price_data=target_price_data,
            factor_results=factor_results,
            volume_result=volume_result,
            insider_net_sell_ratio=None,
            lang=lang
        )
    except Exception as e:
        return jsonify({"error": t("MAIN_ERR_ANALYSIS_FAILED", lang, error=e)}), 500

    formatted_output = format_analysis_output(analysis_result, entry_price_data=entry_price_data, lang=lang)
    formatted_output["stock_name"] = stock_name
    return jsonify(formatted_output)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = not IS_DEMO_MODE
    app.run(host="0.0.0.0", port=port, debug=debug)