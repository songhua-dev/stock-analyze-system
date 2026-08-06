# src/factors/rr_factor.py
"""
RR值（風險報酬比）計分因子
"""

from typing import Dict
from src.i18n import t


def calculate_rr_score(
    current_price: float, 
    support_price: float, 
    target_price: float, 
    lang: str = "zh"
) -> Dict:
    lang = "en" if str(lang).startswith("en") else "zh"

    upside = target_price - current_price
    risk = current_price - support_price

    if risk <= 0:
        err_msg = t("RR_ERR_INVALID_SUPPORT", lang)
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

    if score > 0:
        detail = t("RR_DETAIL_WITH_SCORE", lang, ratio=rr_ratio, score=score)
    else:
        detail = t("RR_DETAIL_WITHOUT_SCORE", lang, ratio=rr_ratio)

    return {"score": score, "usable": True, "detail": detail}