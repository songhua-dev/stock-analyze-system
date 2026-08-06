# src/factors/news_factor.py

import os
import re
import json
from typing import Dict
from dotenv import load_dotenv
from groq import Groq
from src.us_Api_client import fetch_stock_news
from src.i18n import t

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


def analyze_news_sentiment(symbol: str, limit: int = 5, source: str = 'alpaca', lang: str = "zh") -> Dict:
    lang = "en" if str(lang).startswith("en") else "zh"

    try:
        raw_news = fetch_stock_news(symbol, limit=limit, source=source, lang=lang)
    except Exception as e:
        err_msg = t("NEWS_ERR_FETCH_FAILED", lang, error=e)
        return {"score": 0, "usable": False, "detail": err_msg}

    if not raw_news:
        no_news_msg = t("NEWS_NO_RECENT_NEWS", lang)
        return {"score": 0, "usable": False, "detail": no_news_msg}

    formatted_articles = []
    for idx, item in enumerate(raw_news, 1):
        title = item.get("headline", "No Title")
        content = item.get("summary") or item.get("content") or ""
        summary_text = _extract_summary(content, max_sentences=3)
        article_str = f"News {idx}:\nTitle: {title}" + (f"\nSummary: {summary_text}" if summary_text else "")
        formatted_articles.append(article_str)

    combined_news_input = "\n\n".join(formatted_articles)

    if not groq_client:
        key_msg = t("NEWS_ERR_NO_API_KEY", lang)
        return {"score": 0, "usable": False, "detail": key_msg}

    # 全權由 i18n 控制 Prompt 的目標語言指令
    target_language_instruction = t("NEWS_PROMPT_LANG_INSTRUCTION", lang)

    prompt = f"""
You are a professional US stock financial analyst. Analyze the following news regarding {symbol} and evaluate short-term price impact.

[News Content]
{combined_news_input}

[Scoring Rules]
1. Assign an integer score from -5 to +5 to each article:
   - +4~+5: Major bullish breakthroughs (new tech, major deals/orders, regulatory approval)
   - -4~-5: Severe fundamental risks (debt > revenue, core tech blocked, litigation loss, product recall)
   - -3~+3: General bullish/bearish news (ratings adjustments, market sentiment)
   - 0: Neutral / irrelevant / insufficient info.
2. Calculate the arithmetic average score and round to the nearest integer (-5 to +5).
3. {target_language_instruction}

[Response Format]
Return JSON ONLY, no markdown wrapping:
{{
  "score": integer_score,
  "detail": "concise_summary"
}}
"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a precise financial JSON response bot. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        final_score = max(-5, min(5, int(result.get("score", 0))))
        
        default_detail = t("NEWS_DEFAULT_DETAIL_SUCCESS", lang)
        detail_msg = result.get("detail", default_detail)

        return {"score": final_score, "usable": True, "detail": detail_msg}

    except Exception as e:
        err_msg = t("NEWS_ERR_LLM_EXCEPTION", lang, error=e)
        return {"score": 0, "usable": False, "detail": err_msg}