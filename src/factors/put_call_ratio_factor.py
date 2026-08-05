# src/factors/put_call_ratio_factor.py
"""
Put/Call 比率分析因子模組 (put_call_ratio_factor.py)
回傳標準格式: {"score": float, "usable": bool, "detail": str}
"""

from typing import Dict, Optional


def calculate_put_call_ratio_score(
    pc_ratio: Optional[float],
    data_type: str = "當日成交量",
    lang: str = "zh"
) -> Dict:
    lang = "en" if lang.startswith("en") else "zh"

    if pc_ratio is None:
        err_msg = "Put/Call 比率資料缺失，無法進行分析" if lang == "zh" else "Put/Call ratio data missing"
        return {
            "score": 0.0,
            "usable": False,
            "detail": err_msg
        }

    # 1. 判斷多空方向與得分[cite: 9]
    if pc_ratio < 0.7:
        sentiment_text = "偏多" if lang == "zh" else "Bullish"
        score = 1.0
    elif pc_ratio > 1.0:
        sentiment_text = "偏空" if lang == "zh" else "Bearish"
        score = -1.0
    else:
        sentiment_text = "中性" if lang == "zh" else "Neutral"
        score = 0.0

    # 2. 資料類型文字處理[cite: 9]
    if lang == "en" and data_type == "當日成交量":
        display_data_type = "Daily Volume"
    else:
        display_data_type = data_type

    # 3. 格式化輸出[cite: 9]
    detail = (
        f"比率 {pc_ratio:.3f}({display_data_type}): {sentiment_text}"
        if lang == "zh"
        else f"Ratio {pc_ratio:.3f} ({display_data_type}): {sentiment_text}"
    )

    return {
        "score": score,
        "usable": True,
        "detail": detail
    }


if __name__ == "__main__":
    test_result = calculate_put_call_ratio_score(0.524, lang="en")
    print("測試結果：", test_result)