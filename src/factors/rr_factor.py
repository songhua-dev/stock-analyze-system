# src/factors/rr_factor.py
"""
RR值（風險報酬比）計分因子
"""

from typing import Dict


def calculate_rr_score(
    current_price: float, 
    support_price: float, 
    target_price: float, 
    lang: str = "zh"
) -> Dict:
    lang = "en" if lang.startswith("en") else "zh"

    upside = target_price - current_price
    risk = current_price - support_price

    if risk <= 0:
        err_msg = "支撐價計算異常，無法計算RR值" if lang == "zh" else "Invalid support price; R/R calculation failed"
        return {"score": 0.0, "usable": False, "detail": err_msg}

    rr_ratio = upside / risk

    if rr_ratio >= 5.0:
        score = 5.0
    elif rr_ratio >= 3.0:
        score = 3.0
    elif rr_ratio >= 2.0:
        score = 1.0
    else:
        score = 0.0

    if lang == "zh":
        detail = f"RR值 1:{rr_ratio:.2f}，獲得{score:+.0f}分" if score > 0 else f"RR值 1:{rr_ratio:.2f}"
    else:
        detail = f"R/R Ratio 1:{rr_ratio:.2f}, Score: {score:+.0f} pts" if score > 0 else f"R/R Ratio 1:{rr_ratio:.2f}"

    return {"score": score, "usable": True, "detail": detail}