# src/factors/put_call_ratio_factor.py
"""
Put/Call 比率分析因子模組 (put_call_ratio_factor.py)
回傳標準格式: {"score": float, "usable": bool, "detail": str}
"""

from typing import Dict, Optional
from src.i18n import t


def calculate_put_call_ratio_score(
    pc_ratio: Optional[float],
    data_type: Optional[str] = None,
    lang: str = "zh"
) -> Dict:
    lang = "en" if str(lang).startswith("en") else "zh"

    # 若未傳入 data_type，預設使用 i18n 字典中的「當日成交量」
    if data_type is None:
        data_type = t("OPTIONS_DATA_TYPE_DAILY_VOL", lang)

    if pc_ratio is None:
        err_msg = t("PCR_ERR_DATA_MISSING", lang)
        return {
            "score": 0.0,
            "usable": False,
            "detail": err_msg
        }

    # 1. 判斷多空方向與得分
    if pc_ratio < 0.7:
        sentiment_text = t("PCR_SENTIMENT_BULLISH", lang)
        score = 1.0
    elif pc_ratio > 1.0:
        sentiment_text = t("PCR_SENTIMENT_BEARISH", lang)
        score = -1.0
    else:
        sentiment_text = t("PCR_SENTIMENT_NEUTRAL", lang)
        score = 0.0

    # 2. 格式化輸出
    detail = t(
        "PCR_DETAIL_FORMAT",
        lang,
        ratio=pc_ratio,
        data_type=data_type,
        sentiment=sentiment_text
    )

    return {
        "score": score,
        "usable": True,
        "detail": detail
    }


if __name__ == "__main__":
    test_result = calculate_put_call_ratio_score(0.524, lang="en")
    print("測試結果：", test_result)