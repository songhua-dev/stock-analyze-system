# main.py
"""
Flask 主程式（路由層）
包含市場參數 (market) 的分流預留接口與 Demo 模式開關控制：
- IS_DEMO_MODE: 讀取環境變數 DEMO_MODE，控制線上展示版與本機全功能版。
"""

import os
import time
import unicodedata  # 用於全形轉半形
from flask import Flask, request, jsonify, render_template

from src.i18n import t
from src.us_Api_client import (
    fetch_stock_data,
    fetch_analyst_target_price,
    fetch_options_ratio,
    fetch_stock_name
)
from src.analyzer import analyze_stock
from src.recommendation_engine import format_analysis_output

from src.factors.rr_factor import calculate_rr_score
from src.factors.candlestick_factor import calculate_candlestick_score
from src.factors.volume_factor import calculate_volume_multiplier
from src.factors.news_factor import analyze_news_sentiment
from src.factors.put_call_ratio_factor import calculate_put_call_ratio_score
from src.factors.entry_price_factor import calculate_entry_price

app = Flask(__name__)
# 讀取環境變數 DEMO_MODE，預設為 False (本機開發時為全功能版)
IS_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# 紀錄每個 IP 上一次發送請求的時間戳記（用作 10 秒 Rate Limit 防禦）
last_request_time = {}

@app.route('/ping', methods=['GET'])
def ping():
    return 'ok', 200

# -----------------------------------------------------------------
# 🛡️ 1. Favicon 防禦路由 (攔截 404 雜訊請求)
# -----------------------------------------------------------------
@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return '', 204

@app.route("/", methods=["GET"])
def index():
    """渲染前端主頁面，將 is_demo 狀態傳給 HTML"""
    return render_template("index.html", is_demo=IS_DEMO_MODE)


@app.route("/api/analyze", methods=["GET"])
def analyze_route():
    """
    範例請求：/api/analyze?market=us&symbol=PLTR&factors=rr,news&lang=en
    """
    # 讀取前端傳來的語言參數（預設為 en）
    lang = request.args.get("lang", "en").lower().strip()
    lang = "en" if lang.startswith("en") else "zh"

    # -----------------------------------------------------------------
    # 🛡️ 2. 頻繁 Request 防禦 (限流 10 秒)
    # -----------------------------------------------------------------
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    current_time = time.time()
    if client_ip in last_request_time:
        elapsed = current_time - last_request_time[client_ip]
        if elapsed < 10:
            return jsonify({
                "error": t("MAIN_ERR_RATE_LIMIT", lang)
            }), 429

    # 更新此 IP 的最新請求時間
    last_request_time[client_ip] = current_time

    market = request.args.get("market", "us").lower().strip()
    raw_symbol = request.args.get("symbol", "")

    # 全形轉半形 + 去空白 + 轉大寫
    symbol = unicodedata.normalize('NFKC', raw_symbol).upper().strip()

    if not symbol:
        return jsonify({"error": t("MAIN_ERR_SYMBOL_REQUIRED", lang)}), 400

    # 市場分流預留接口
    if market == "tw":
        return jsonify({"error": t("MAIN_ERR_TW_API_IN_DEV", lang)}), 501

    factors_param = request.args.get("factors", "")
    selected_factors = [f.strip() for f in factors_param.split(",") if f.strip()]
    data_source = request.args.get("source", "yfinance")

    # Demo 模式安全防護
    if IS_DEMO_MODE:
        if data_source == "alpaca":
            return jsonify({
                "error": t("MAIN_ERR_DEMO_ALPACA_BLOCKED", lang)
            }), 400
        if "news" in selected_factors:
            return jsonify({
                "error": t("MAIN_ERR_DEMO_NEWS_BLOCKED", lang)
            }), 400

    # 抓取公司名稱
    try:
        stock_info = fetch_stock_name(symbol)
        if isinstance(stock_info, dict):
            stock_name = stock_info.get("stock_name") or symbol
        else:
            stock_name = str(stock_info)
    except Exception:
        stock_name = symbol

    # 第1步：抓取美股基礎資料 (K線)
    try:
        df = fetch_stock_data(symbol, days=120, source=data_source, lang=lang)
    except Exception as e:
        err_str = str(e)
        if "Too Many Requests" in err_str or "Rate limited" in err_str or "429" in err_str:
            return jsonify({"error": t("MAIN_ERR_RATE_LIMITED", lang)}), 429
            
        err_msg = t("MAIN_ERR_FETCH_DATA_FAILED", lang, source=data_source, symbol=symbol)
        return jsonify({"error": err_msg}), 500

    # 先將 target_price_data 初始化為 None，避免未宣告引發 NameError
    target_price_data = None

    # 若選取 RR 分析或算式分析需要，抓取分析師目標價
    try:
        target_price_data = fetch_analyst_target_price(symbol, source=data_source, lang=lang)
    except Exception as e:
        print(f"⚠️ 抓取目標價失敗/跳過: {e}")

    # 共用價格基準計算
    current_price = float(df['close'].iloc[-1])
    strong_support = float(df['close'].min())  # 近120日最低收盤
    short_support = float(df['close'].iloc[-20:].min()) if len(df) >= 20 else strong_support  # 近20日最低收盤

    # 第2步：計算因子
    factor_results = {}

    # K線評分
    try:
        factor_results["candlestick"] = calculate_candlestick_score(df, lang=lang)
    except Exception as e:
        print(f"⚠️ Candlestick 計算失敗: {e}")

    # RR評分
    if "rr" in selected_factors:
        try:
            if target_price_data and isinstance(target_price_data, dict):
                target_price = target_price_data.get("target_mean")
                if target_price is not None:
                    factor_results["rr"] = calculate_rr_score(current_price, strong_support, target_price, lang=lang)
        except Exception as e:
            print(f"⚠️ RR 計算失敗: {e}")

    # 新聞評分
    if "news" in selected_factors:
        try:
            factor_results["news"] = analyze_news_sentiment(symbol, limit=5, source=data_source, lang=lang)
        except Exception as e:
            print(f"⚠️ News 計算失敗: {e}")

    # Put/Call 選擇權評分
    if "put_call" in selected_factors:
        try:
            options_data = fetch_options_ratio(symbol, min_days_out=3, lang=lang)
            if options_data.get("usable"):
                data_type = options_data.get("data_type")
                factor_results["put_call"] = calculate_put_call_ratio_score(
                    options_data.get("put_call_ratio"),
                    data_type=data_type,
                    lang=lang
                )
        except Exception as e:
            print(f"⚠️ Put/Call 計算失敗: {e}")

    # 第3步：成交量乘數
    try:
        volume_result = calculate_volume_multiplier(df, lang=lang)
    except Exception:
        volume_result = {"multiplier": 1.0, "detail": ""}

    # 建議進場價計算
    try:
        entry_price_data = calculate_entry_price(current_price, short_support, strong_support, lang=lang)
    except Exception as e:
        print(f"⚠️ Entry Price 計算失敗: {e}")
        entry_price_data = {"available": False, "detail": ""}

    # 第4步：算式整合與分析
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
        err_msg = t("MAIN_ERR_ANALYSIS_FAILED", lang, error=e)
        return jsonify({"error": err_msg}), 500

    # 第5步：格式化輸出
    formatted_output = format_analysis_output(analysis_result, entry_price_data=entry_price_data, lang=lang)
    formatted_output["stock_name"] = stock_name
    return jsonify(formatted_output)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = not IS_DEMO_MODE
    app.run(host="0.0.0.0", port=port, debug=debug)