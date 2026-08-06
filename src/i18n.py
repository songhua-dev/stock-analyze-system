# src/i18n.py
"""
統一多語系（i18n）字典與翻譯工具模組
"""

# 多語系字典檔
TRANSLATIONS = {
    # (recommendation_engine.py 中使用)
    "LABEL_RR": {"zh": "RR值", "en": "RR Ratio"},
    "LABEL_CANDLESTICK": {"zh": "K線型態", "en": "Candlestick"},
    "LABEL_NEWS": {"zh": "新聞情緒", "en": "News Sentiment"},
    "LABEL_PUT_CALL": {"zh": "Put/Call", "en": "Put/Call Ratio"},
    "LABEL_VOLUME": {"zh": "成交量：", "en": "Volume: "},

    # 系統訊息與格式
    "ANALYSIS_FAILED": {"zh": "無法分析", "en": "Analysis Failed"},
    "UNKNOWN_ERROR": {"zh": "未知錯誤", "en": "Unknown Error"},
    "SCORE_PTS": {"zh": "{score:+}分", "en": "{score:+} pts"},
    "FACTOR_LINE_WITH_SCORE": {
        "zh": "<strong>{label}：</strong>{detail}（獲得 {score_str}）",
        "en": "<strong>{label}: </strong>{detail} ({score_str})"
    },
    "FACTOR_LINE_NO_SCORE": {
        "zh": "<strong>{label}：</strong>{detail}",
        "en": "<strong>{label}: </strong>{detail}"
    },
    "VOLUME_LINE": {
        "zh": "<strong>{vol_label}</strong>{volume_detail}",
        "en": "<strong>{vol_label}</strong>{volume_detail}"
    },
    "DECISION_WITH_SCORE": {
        "zh": "{decision_text}（平均 {final_score}分）",
        "en": "{decision_text} (Avg. {final_score} pts)"
    },
    # (analysis.py 中使用)

    # 否決條件 (Veto Rules)
    "VETO_PRICE_BELOW_SUPPORT": {
        "zh": "現價 ({current_price:.2f}元) 已跌破或等於強力支撐價 ({support_price:.2f}元)，風險評估失準",
        "en": "Current price (${current_price:.2f}) broke/hit strong support (${support_price:.2f}). Risk assessment invalidated."
    },
    "VETO_MISSING_TARGET_PRICE": {
        "zh": "分析師目標價資料缺失，無法計算風險報酬比",
        "en": "Analyst target price data missing. R/R ratio unavailable."
    },
    "VETO_TARGET_BELOW_CURRENT": {
        "zh": "分析師目標價 ({target_price:.2f}元)<br>低於或等於現價 ({current_price:.2f}元)<br>資料可能異常或看空",
        "en": "Analyst target (${target_price:.2f}) is below/equal to current price (${current_price:.2f}). Bearish or invalid data."
    },
    "VETO_RR_TOO_LOW": {
        "zh": "現價{current_price:.2f}元<br>支撐價格為{support_price:.2f}元<br>分析師平均目標價為{target_price:.2f}元<br>RR值為1:{rr_ratio:.1f}, 低於建議值1:2",
        "en": "Price: ${current_price:.2f}<br>Support: ${support_price:.2f}<br>Target: ${target_price:.2f}<br>R/R Ratio is 1:{rr_ratio:.1f}, below threshold 1:2"
    },
    "VETO_INSIDER_NET_SELL": {
        "zh": "近30天內部人淨賣出達流通股本 {ratio:.2f}%，高於 0.5% 警戒門檻",
        "en": "Insider net selling reached {ratio:.2f}% over 30 days, exceeding 0.5% threshold."
    },
    "ERR_INSUFFICIENT_DATA": {
        "zh": "K線數據不足，無法進行分析",
        "en": "Insufficient price data for analysis."
    },

    # 訊號分歧警告
    "WARNING_DIVERGENCE": {
        "zh": "⚠️ 訊號分歧：各項分析結果差異較大，建議謹慎評估",
        "en": "⚠️ Signal Divergence: Factor results differ significantly. Proceed with caution."
    },

    # 決策文字 (Decisions)
    "DECISION_NOT_RECOMMENDED": {
        "zh": "不建議入場",
        "en": "Not Recommended"
    },
    "DECISION_STRONG_BUY": {
        "zh": "強烈建議入場",
        "en": "Strong Buy"
    },
    "DECISION_BUY_ACCUMULATE": {
        "zh": "建議入場，可觀察",
        "en": "Buy / Accumulate"
    },
    "DECISION_NEUTRAL": {
        "zh": "訊號中性，建議觀望",
        "en": "Neutral / Hold"
    },

    # 決策原因 (Reasons)
    "REASON_STRONG_BUY": {
        "zh": "各項量化因子表現優異（總分 {score}分），技術面與風報比皆具備強勁買進訊號。",
        "en": "Excellent factor ratings ({score} pts). Technicals and R/R show strong buy signals."
    },
    "REASON_BUY_ACCUMULATE": {
        "zh": "量化評分為 {score}分 達到入場門檻，整體風險可控，可考慮分批佈局。",
        "en": "Score reached entry threshold ({score} pts). Controlled risk; partial positions recommended."
    },
    "REASON_NEUTRAL": {
        "zh": "量化評分為 {score}分，多空訊號相抵，建議觀望。",
        "en": "Neutral rating ({score} pts). Bullish and bearish signals balance out."
    },
    "REASON_NOT_RECOMMENDED": {
        "zh": "量化評分為 {score}分，整體技術面與風報比偏弱。",
        "en": "Weak rating ({score} pts). Technicals and R/R ratio are weak."
    },

    # (us_API_client.py 中使用)
    "ERR_NO_ALPACA_KEY": {
        "zh": "❌ 未找到有效的 Alpaca API Key，無法使用 Alpaca 資料源。",
        "en": "❌ Valid Alpaca API Key not found. Cannot use Alpaca data source."
    },
    "ERR_YFINANCE_NO_DATA": {
        "zh": "❌ yfinance 無法取得 {symbol} 的數據。",
        "en": "❌ yfinance failed to retrieve data for {symbol}."
    },
    "ERR_CLEANED_DATA_EMPTY": {
        "zh": "❌ {symbol} 清除NaN列後無有效資料",
        "en": "❌ No valid data for {symbol} after dropping NaN rows."
    },
    "ERR_UNSUPPORTED_SOURCE": {
        "zh": "❌ 不支援的資料來源: {source}。請使用 'alpaca' 或 'yfinance'。",
        "en": "❌ Unsupported data source: {source}. Please use 'alpaca' or 'yfinance'."
    },
    "NO_NEWS_TITLE": {
        "zh": "無新聞標題",
        "en": "No News Title"
    },
    "WARN_TARGET_PRICE_FALLBACK": {
        "zh": "⚠️ 提示：Alpaca API 不支援目標價數據，自動切換至 yfinance 進行抓取。",
        "en": "⚠️ Note: Alpaca API does not support target price data; falling back to yfinance."
    },
    "WARN_OPTIONS_FALLBACK": {
        "zh": "⚠️ 提示：Put/Call Ratio 目前僅支援 yfinance，自動切換。",
        "en": "⚠️ Note: Put/Call Ratio currently only supports yfinance; switching automatically."
    },

    # Options Ratio Details
    "OPTIONS_ERR_EXPIRATION_LIST": {
        "zh": "無法取得選擇權到期日清單 ({error})",
        "en": "Failed to retrieve options expiration list ({error})"
    },
    "OPTIONS_NO_MARKET_DATA": {
        "zh": "該股票無選擇權市場資料",
        "en": "No options market data available for this stock"
    },
    "OPTIONS_ERR_CHAIN_FETCH": {
        "zh": "選擇權鏈資料抓取失敗 ({error})",
        "en": "Failed to fetch option chain data ({error})"
    },
    "OPTIONS_CALL_VOL_ZERO": {
        "zh": "Call當日成交量為0（可能非交易時段），無法計算比率",
        "en": "Call volume is 0 (possibly non-trading hours); unable to calculate ratio"
    },
    "OPTIONS_DETAIL_SUCCESS": {
        "zh": "依據 {target_date} 到期選擇權鏈計算（當日成交量）",
        "en": "Calculated based on option chain expiring {target_date} (daily volume)"
    },
    "WARN_TARGET_PRICE_FETCH_FAILED": {
        "zh": "⚠️ 分析師目標價抓取失敗或遭受請求限制 ({error})",
        "en": "⚠️ Failed to fetch analyst target price or rate limited ({error})"
    },
    "OPTIONS_DATA_TYPE_DAILY_VOL": {
        "zh": "當日成交量",
        "en": "Daily Volume"
    },
    #(candlestick_factor.py 中使用)
    "CANDLESTICK_INSUFFICIENT_DATA": {
        "zh": "K線資料不足，無法進行型態辨識",
        "en": "Insufficient K-line data for pattern recognition"
    },
    "CANDLESTICK_NO_PATTERN": {
        "zh": "無特殊 K 線型態（不額外加減分）",
        "en": "No special candlestick pattern detected"
    },
    "CANDLESTICK_MATCHED_DETAIL": {
        "zh": "符合 {name}（統計可信度 {winrate}），獲得 {score:+.1f}分",
        "en": "Matched {name} (Win rate: {winrate}), Score: {score:+.1f} pts"
    },
    # (news_factor.py 中使用)
    "NEWS_ERR_FETCH_FAILED": {
        "zh": "新聞資料抓取失敗 ({error})",
        "en": "Failed to fetch news data ({error})"
    },
    "NEWS_NO_RECENT_NEWS": {
        "zh": "近3日無相關新聞",
        "en": "No relevant news in the past 3 days"
    },
    "NEWS_ERR_NO_API_KEY": {
        "zh": "缺少 GROQ_API_KEY，無法進行新聞情緒分析",
        "en": "GROQ_API_KEY missing. Sentiment analysis disabled."
    },
    "NEWS_DEFAULT_DETAIL_SUCCESS": {
        "zh": "已完成新聞情緒評估",
        "en": "Completed news sentiment assessment"
    },
    "NEWS_ERR_LLM_EXCEPTION": {
        "zh": "LLM 新聞情緒分析過程發生例外 ({error})",
        "en": "LLM sentiment analysis exception ({error})"
    },
    "NEWS_PROMPT_LANG_INSTRUCTION": {
        "zh": "請用『繁體中文』撰寫一句簡短摘要（30字以內）。",
        "en": "Please write a concise summary (within 20 words) in ENGLISH."
    },
    # (put_call_ratio_factor.py 中使用)
    "PCR_ERR_DATA_MISSING": {
        "zh": "Put/Call 比率資料缺失，無法進行分析",
        "en": "Put/Call ratio data missing"
    },
    "PCR_SENTIMENT_BULLISH": {
        "zh": "偏多",
        "en": "Bullish"
    },
    "PCR_SENTIMENT_BEARISH": {
        "zh": "偏空",
        "en": "Bearish"
    },
    "PCR_SENTIMENT_NEUTRAL": {
        "zh": "中性",
        "en": "Neutral"
    },
    "PCR_DETAIL_FORMAT": {
        "zh": "比率 {ratio:.3f}({data_type}): {sentiment}",
        "en": "Ratio {ratio:.3f} ({data_type}): {sentiment}"
    },
    #(rr_factor.py 中使用)
    "RR_ERR_INVALID_SUPPORT": {
        "zh": "支撐價計算異常，無法計算RR值",
        "en": "Invalid support price; R/R calculation failed"
    },
    "RR_DETAIL_WITH_SCORE": {
        "zh": "RR值 1:{ratio:.2f}，獲得{score:+.0f}分",
        "en": "R/R Ratio 1:{ratio:.2f}, Score: {score:+.0f} pts"
    },
    "RR_DETAIL_WITHOUT_SCORE": {
        "zh": "RR值 1:{ratio:.2f}",
        "en": "R/R Ratio 1:{ratio:.2f}"
    },
    # (volume_factor.py 中使用)
    "VOL_ERR_INSUFFICIENT_DATA": {
        "zh": "資料不足20日，無法計算均量",
        "en": "Insufficient data (<20 days) for volume MA"
    },
    "VOL_DETAIL_SPIKE": {
        "zh": "當日量達20日均量{ratio:.1f}倍（放量），分數×1.2",
        "en": "Volume reached {ratio:.1f}x 20-day MA (Volume Spike), score x1.2"
    },
    "VOL_DETAIL_NO_SPIKE": {
        "zh": "成交量未出現放大訊號（未越過1.5倍均量）",
        "en": "No volume surge detected (<1.5x 20-day MA)"
    },
    #(main.py 中使用)
    "MAIN_ERR_RATE_LIMIT": {
        "zh": "目前為免費demo版, 為限制流量因此每10秒可以查詢一次",
        "en": "This is a free demo version. To manage server traffic, queries are limited to once every 10 seconds."
    },
    "MAIN_ERR_SYMBOL_REQUIRED": {
        "zh": "請提供股票代號 (symbol)",
        "en": "Stock symbol required"
    },
    "MAIN_ERR_TW_API_IN_DEV": {
        "zh": "台股 API 分析接口開發中",
        "en": "Taiwan Stock API is under development"
    },
    "MAIN_ERR_DEMO_ALPACA_BLOCKED": {
        "zh": "🔒 雲端 Demo 版暫不開放 Alpaca API 資料來源，請下載 GitHub 專案於本機執行。",
        "en": "🔒 Alpaca API source is restricted in Demo mode. Please clone the GitHub repo to run locally."
    },
    "MAIN_ERR_DEMO_NEWS_BLOCKED": {
        "zh": "🔒 雲端 Demo 版暫不開放 LLM 新聞情緒分析，避免 API 額度耗盡。請下載 GitHub 專案於本機執行。",
        "en": "🔒 LLM News Sentiment is restricted in Demo mode. Please clone the GitHub repo to run locally."
    },
    "MAIN_ERR_FETCH_DATA_FAILED": {
        "zh": "❌ {source} 無法取得 {symbol} 的數據，請輸入正確股票代碼或其他股票。",
        "en": "❌ {source} failed to fetch data for {symbol}. Please check the symbol and try again."
    },
    "MAIN_ERR_ANALYSIS_FAILED": {
        "zh": "量化分析計算發生錯誤: {error}",
        "en": "Quant analysis error: {error}"
    },
    #(entry_price_factor.py 中使用)
    "ENTRY_PRICE_ERR_INSUFFICIENT_DATA": {
        "zh": "資料不足，無法計算建議進場價",
        "en": "Insufficient data to calculate entry price."
    },
    "ENTRY_PRICE_DETAIL": {
        "zh": "建議進場價：{low}~{high}元（現價至短期支撐間）；買到賺到價：約{best_value}元（強力支撐附近）",
        "en": "Suggested Entry: ${low}~${high} (between current price and short-term support); Bargain Price: approx. ${best_value} (near strong support)"
    },
    # (前端 UI: 我的最愛與歷史紀錄)
    "FAVORITES_TITLE": {
        "zh": "我的最愛",
        "en": "Favorites"
    },
    "ADD_TO_FAVORITES": {
        "zh": "⭐ 加入最愛",
        "en": "⭐ Add to Favorites"
    },
    "REMOVE_FROM_FAVORITES": {
        "zh": "★ 已在最愛 (點擊移除)",
        "en": "★ Favorited (Click to remove)"
    },
    "NO_FAVORITES_YET": {
        "zh": "尚未建立最愛清單",
        "en": "No favorites added yet."
    },
    "HISTORY_TITLE": {
        "zh": "歷史查詢紀錄",
        "en": "Analysis History"
    },
    "MAIN_ERR_RATE_LIMITED": {
        "zh": "由於免費版流量達到限制，需等待 15 分鐘後才能再次使用",
        "en": "Due to free tier rate limits, please wait 15 minutes before trying again."
    }
}


def t(key: str, lang: str = "zh", **kwargs) -> str:
    """
    通用翻譯與格式化函式
    :param key: 字典鍵值
    :param lang: 語言代碼 ('zh', 'en'...)
    :param kwargs: 動態帶入的格式化參數 (如 score, detail 等)
    """
    lang_code = "en" if str(lang).lower().startswith("en") else "zh"
    
    # 1. 確保 TRANSLATIONS 字典中有這個 Key
    msg_dict = TRANSLATIONS.get(key)
    if not msg_dict:
        # 若連字典都找不到這個 key，印出警告方便除錯，並回傳 key
        print(f"⚠️ [i18n Warning] Key '{key}' not found in TRANSLATIONS dictionary.")
        return key

    # 2. 取得翻譯範本（找不到對應語言則 fallback 到 'zh'，再找不到才退回 key）
    template = msg_dict.get(lang_code) or msg_dict.get("zh") or key

    # 3. 處理 kwargs 格式化替換
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception as e:
            print(f"⚠️ [i18n Format Error] Key: '{key}', Template: '{template}', Error: {e}")
            return template

    return template