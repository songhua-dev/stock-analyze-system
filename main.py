# src/main.py
"""
Flask 主程式（路由層）
包含市場參數 (market) 的分流預留接口：
- market=us (預設美股處理流程)
- market=tw (預留台股處理流程)
"""

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


@app.route("/", methods=["GET"])
def index():
    """渲染前端主頁面 (templates/index.html)"""
    return render_template("index.html")


@app.route("/api/analyze", methods=["GET"])
def analyze_route():
    """
    範例請求：/api/analyze?market=us&symbol=PLTR&factors=rr,news
    """
    market = request.args.get("market", "us").lower().strip()
    symbol = request.args.get("symbol", "").upper().strip()

    if not symbol:
        return jsonify({"error": "請提供股票代號 (symbol)"}), 400

    # -----------------------------------------------------------------
    # 市場分流預留接口
    # -----------------------------------------------------------------
    if market == "tw":
        # 未來台股專屬分析入口預留點
        return jsonify({"error": "台股 API 分析接口開發中"}), 501

    # 以下為美股 (market == "us") 的既有邏輯
    factors_param = request.args.get("factors", "")
    selected_factors = [f.strip() for f in factors_param.split(",") if f.strip()]

    data_source = request.args.get("source", "yfinance")
    stock_info = fetch_stock_name(symbol)
    stock_name = stock_info.get("stock_name", symbol)

    # 第1步：抓取美股基礎資料
    try:
        df = fetch_stock_data(symbol, days=120, source=data_source)
    except Exception as e:
        return jsonify({"error": f"❌ {data_source} 無法取得 {symbol} 的數據，請輸入正確股票代碼或其他股票。"}), 500

    try:
        target_price_data = fetch_analyst_target_price(symbol)
    except Exception as e:
        return jsonify({"error": f"分析師目標價抓取失敗: {e}"}), 500

    # 第2步：計算因子
    factor_results = {}
    factor_results["candlestick"] = calculate_candlestick_score(df)

    if "rr" in selected_factors:
        current_price = float(df['close'].iloc[-1])
        support_price = float(df['close'].min())
        target_price = target_price_data.get("target_mean")
        if target_price is not None:
            factor_results["rr"] = calculate_rr_score(current_price, support_price, target_price)

    if "news" in selected_factors:
        factor_results["news"] = analyze_news_sentiment(symbol, limit=5, source=data_source)

    if "put_call" in selected_factors:
        options_data = fetch_options_ratio(symbol, min_days_out=3)
        factor_results["put_call"] = calculate_put_call_ratio_score(
            options_data.get("put_call_ratio"), 
            options_data.get("data_type")
        )

    # 第3步：成交量乘數
    volume_result = calculate_volume_multiplier(df)

    # 第4步：算式整合與分析
    analysis_result = analyze_stock(
        df=df,
        target_price_data=target_price_data,
        factor_results=factor_results,
        volume_result=volume_result,
        insider_net_sell_ratio=None
    )

    # 第5步：格式化輸出
    formatted_output = format_analysis_output(analysis_result)
    formatted_output["stock_name"] = stock_name
    return jsonify(formatted_output)


if __name__ == "__main__":
    app.run(debug=True, port=5000)