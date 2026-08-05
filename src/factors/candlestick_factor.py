# src/factors/candlestick_factor.py

import talib
import pandas as pd
from typing import Dict

BULKOWSKI_TIERS = {
    ("CDL3LINESTRIKE", -1): {"score": -5.0, "name": "Bearish Three Line Strike", "winrate": "67.38%"},
    ("CDL3LINESTRIKE", 1):  {"score": 5.0,  "name": "Bullish Three Line Strike", "winrate": "65.23%"},
    ("CDL3BLACKCROWS", -1): {"score": -4.0, "name": "Bearish Three Black Crows", "winrate": "59.83%"},
    ("CDLEVENINGSTAR", -1): {"score": -4.0, "name": "Bearish Evening Star", "winrate": "55.85%"},
    ("CDLTASUKIGAP", 1):    {"score": 3.0,  "name": "Bullish Upside Tasuki Gap", "winrate": "54.44%"},
    ("CDLINVERTEDHAMMER", 1): {"score": 2.0, "name": "Bullish Inverted Hammer", "winrate": "51.73%"},
}


def calculate_candlestick_score(df: pd.DataFrame, lang: str = "zh") -> Dict:
    lang = "en" if lang.startswith("en") else "zh"

    if len(df) < 10:
        err_msg = "K線資料不足，無法進行型態辨識" if lang == "zh" else "Insufficient K-line data for pattern recognition"
        return {"score": 0.0, "usable": False, "detail": err_msg}

    op = df['open'].values
    hi = df['high'].values
    lo = df['low'].values
    cl = df['close'].values

    matched_patterns = []

    for (func_name, direction), tier_info in BULKOWSKI_TIERS.items():
        try:
            func = getattr(talib, func_name)
            res = func(op, hi, lo, cl)
            latest_val = res[-1]
        except Exception:
            continue

        latest_direction = 1 if latest_val > 0 else (-1 if latest_val < 0 else 0)

        if latest_direction == direction:
            matched_patterns.append(tier_info)

    if not matched_patterns:
        no_pattern_msg = "無特殊 K 線型態（不額外加減分）" if lang == "zh" else "No special candlestick pattern detected"
        return {
            "score": 0.0, 
            "usable": True, 
            "detail": no_pattern_msg
        }

    best_match = max(matched_patterns, key=lambda p: abs(p["score"]))

    if lang == "zh":
        detail = (f"符合 {best_match['name']}"
                  f"（統計可信度 {best_match['winrate']}），"
                  f"獲得 {best_match['score']:+.1f}分")
    else:
        detail = (f"Matched {best_match['name']} "
                  f"(Win rate: {best_match['winrate']}), "
                  f"Score: {best_match['score']:+.1f} pts")

    return {"score": best_match["score"], "usable": True, "detail": detail}