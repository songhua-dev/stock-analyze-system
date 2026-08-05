# src/factors/news_factor.py
"""
新聞情緒分析模組（原 news_sentiment.py，搬移至 factors/ 並改名，內容不變）
- 唯一呼叫 LLM API 的因子模組，與其他純函式因子明確切割
- 使用 Groq API (llama-3.1-8b-instant)
- 輸出格式統一為 {"score": int, "usable": bool, "detail": str}
  usable=False 代表「查無資料/無法判讀」，不應被 analyzer.py 納入平均分計算
  usable=True 代表「LLM 已完成有效判讀」，即使結果剛好是 0 分（真中性）也要納入計算
"""

import os
import re
import json
from typing import Dict
from dotenv import load_dotenv
from groq import Groq
from src.us_Api_client import fetch_stock_news

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _extract_summary(text: str, max_sentences: int = 3) -> str:
    if not text:
        return ""
    sentences = re.split(r'([。！？!?\n]+)', text)
    summary = ""
    sentence_count = 0
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i].strip()
        punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
        if sentence:
            summary += sentence + punctuation
            sentence_count += 1
            if sentence_count >= max_sentences:
                break
    return summary if summary else text[:150]


def analyze_news_sentiment(symbol: str, limit: int = 5, source: str = 'alpaca') -> Dict:
    """
    :return: {"score": int (-5~5), "usable": bool, "detail": str}
    """
    try:
        raw_news = fetch_stock_news(symbol, limit=limit, source=source)
    except Exception as e:
        return {"score": 0, "usable": False, "detail": f"新聞資料抓取失敗 ({e})"}

    if not raw_news:
        return {"score": 0, "usable": False, "detail": "近3日無相關新聞"}

    formatted_articles = []
    for idx, item in enumerate(raw_news, 1):
        title = item.get("headline", "無標題")
        content = item.get("summary") or item.get("content") or ""
        summary_text = _extract_summary(content, max_sentences=3)
        article_str = f"新聞 {idx}：\n標題：{title}" + (f"\n摘要：{summary_text}" if summary_text else "")
        formatted_articles.append(article_str)

    combined_news_input = "\n\n".join(formatted_articles)

    if not groq_client:
        return {"score": 0, "usable": False, "detail": "缺少 GROQ_API_KEY，無法進行新聞情緒分析"}

    prompt = f"""
你是一位專業的美股金融新聞分析師。請分析以下關於個股 {symbol} 的新聞內容，評估其對股價的短期影響。

【新聞資料】
{combined_news_input}

【評分規則】
1. 針對每一則新聞獨立給予一個 -5 到 +5 的整數分數：
   - +4~+5：技術實質突破（例如：新產品/新技術獲驗證、重大合作/訂單簽署、監管批准）
   - -4~-5：重大基本面惡化（例如：負債超過營收、核心技術受阻/專利訴訟敗訴、產品重大瑕疵/召回）
   - -3~+3：其餘所有一般性利多/利空消息（分析師評等調整、市場氛圍等）
   - 0：中性、與該股票走勢無直接關聯、或內容不足以判斷利多利空（必須給 0 分，不可硬生出非零分數）
2. 計算所有新聞分數的「算術平均值」，並四捨五入取至整數，作為最終綜合分數（必須介於 -5 到 +5 之間）。
3. 提供一句簡短的摘要（30字以內），說明主要的判斷依據。

【回傳格式】
請嚴格僅回傳 JSON 格式，不要包含任何額外 Markdown 標記或解析文字：
{{
  "score": 綜合分數(整數),
  "detail": "一句簡短說明主要判斷依據"
}}
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "你是一個精準的金融 JSON 回傳機器人，只輸出標準 JSON。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        final_score = max(-5, min(5, int(result.get("score", 0))))
        detail_msg = result.get("detail", "已完成新聞情緒評估")

        return {"score": final_score, "usable": True, "detail": detail_msg}

    except Exception as e:
        return {"score": 0, "usable": False, "detail": f"LLM 新聞情緒分析過程發生例外 ({e})"}


if __name__ == "__main__":
    print("🚀 開始測試 src/factors/news_factor.py 新聞情緒模組...\n" + "=" * 50)
    test_symbol = "PLTR"
    res = analyze_news_sentiment(test_symbol, limit=5, source='alpaca')
    print(f"\n【分析結果】\n得分: {res.get('score')} | 可用: {res.get('usable')} | 說明: {res.get('detail')}")
    print("\n" + "=" * 50 + "\n🎉 測試完成！")