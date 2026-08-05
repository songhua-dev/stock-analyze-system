# main.py
"""
Flask 主程式（路由層）
包含市場參數 (market) 的分流預留接口與 Demo 模式開關控制：
- IS_DEMO_MODE: 讀取環境變數 DEMO_MODE，控制線上展示版與本機全功能版。
"""

import os
import unicodedata  # 用於全形轉半形
from flask import Flask, request, jsonify, render_template

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

app = Flask(__name__)
# 讀取環境變數 DEMO_MODE，預設為 False (本機開發時為全功能版)
IS_DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

@app.route('/ping', methods=['GET'])
def ping():
    return 'ok', 200

@app.route("/", methods=["GET"])
def index():
    """渲染前端主頁面，將 is_demo 狀態傳給 HTML"""
    return render_template("index.html", is_demo=IS_DEMO_MODE)


@app.route("/api/analyze", methods=["GET"])
def analyze_route():
    """
    範例請求：/api/analyze?market=us&symbol=PLTR&factors=rr,news&lang=en
    """
    market = request.args.get("market", "us").lower().strip()
    raw_symbol = request.args.get("symbol", "")
    
    # 🔹 讀取前端傳來的語言參數（預設為 en）
    lang = request.args.get("lang", "en").lower().strip()

    # -----------------------------------------------------------------
    # 全形轉半形 + 去空白 + 轉大寫 (解決手機全形輸入問題)
    # -----------------------------------------------------------------
    symbol = unicodedata.normalize('NFKC', raw_symbol).upper().strip()

    if not symbol:
        return jsonify({"error": "請提供股票代號 (symbol)"}), 400

    # -----------------------------------------------------------------
    # 市場分流預留接口
    # -----------------------------------------------------------------
    if market == "tw":
        return jsonify({"error": "台股 API 分析接口開發中"}), 501

    # 以下為美股 (market == "us") 的既有邏輯
    factors_param = request.args.get("factors", "")
    selected_factors = [f.strip() for f in factors_param.split(",") if f.strip()]
    data_source = request.args.get("source", "yfinance")

    # -----------------------------------------------------------------
    # 🛡️ Demo 模式安全防護（後端第二道防線）
    # -----------------------------------------------------------------
    if IS_DEMO_MODE:
        if data_source == "alpaca":
            return jsonify({
                "error": "🔒 雲端 Demo 版暫不開放 Alpaca API 資料來源，請下載 GitHub 專案於本機執行。"
            }), 400
        if "news" in selected_factors:
            return jsonify({
                "error": "🔒 雲端 Demo 版暫不開放 LLM 新聞情緒分析，避免 API 額度耗盡。請下載 GitHub 專案於本機執行。"
            }), 400

    # 抓取公司名稱（加 try-catch 避免崩潰）
    try:
        stock_info = fetch_stock_name(symbol)
        stock_name = stock_info.get("stock_name", symbol)
    except Exception:
        stock_name = symbol

    # 第1步：抓取美股基礎資料 (K線)
    try:
        df = fetch_stock_data(symbol, days=120, source=data_source)
    except Exception as e:
        return jsonify({"error": f"❌ {data_source} 無法取得 {symbol} 的數據，請輸入正確股票代碼或其他股票。"}), 500

    # 抓取目標價 (安全容錯，被限流時自動跳過不報 500)
    try:
        target_price_data = fetch_analyst_target_price(symbol)
    except Exception as e:
        print(f"⚠️ 分析師目標價抓取受限 ({e})")
        target_price_data = {"target_mean": None, "target_high": None, "target_low": None}

    # 第2步：計算因子 (均帶入 lang 參數進行國際化支援)
    factor_results = {}
    
    # K線評分
    try:
        factor_results["candlestick"] = calculate_candlestick_score(df, lang=lang)
    except Exception as e:
        print(f"⚠️ Candlestick 計算失敗: {e}")

    # RR評分
    if "rr" in selected_factors:
        try:
            current_price = float(df['close'].iloc[-1])
            support_price = float(df['close'].min())
            target_price = target_price_data.get("target_mean")
            if target_price is not None:
                factor_results["rr"] = calculate_rr_score(current_price, support_price, target_price, lang=lang)
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
            options_data = fetch_options_ratio(symbol, min_days_out=3)
            if options_data.get("usable"):
                data_type = options_data.get("data_type", "")
                
                # 🔹 補齊 data_type 的多語系轉換
                if not lang.startswith("zh"):
                    if "成交量" in data_type:
                        data_type = "Daily Volume"
                    elif "未平倉" in data_type:
                        data_type = "Open Interest"

                factor_results["put_call"] = calculate_put_call_ratio_score(
                    options_data.get("put_call_ratio"), 
                    data_type,
                    lang=lang
                )
        except Exception as e:
            print(f"⚠️ Put/Call 計算失敗: {e}")

    # 第3步：成交量乘數
    try:
        volume_result = calculate_volume_multiplier(df, lang=lang)
    except Exception:
        volume_result = {"multiplier": 1.0, "detail": ""}

    # 🔹 第4步：算式整合與分析（帶入 lang 參數）
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
        return jsonify({"error": f"量化分析計算發生錯誤: {e}"}), 500

    # 🔹 第5步：格式化輸出（帶入 lang 參數）
    formatted_output = format_analysis_output(analysis_result, lang=lang)
    formatted_output["stock_name"] = stock_name
    return jsonify(formatted_output)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = not IS_DEMO_MODE
    app.run(host="0.0.0.0", port=port, debug=debug)