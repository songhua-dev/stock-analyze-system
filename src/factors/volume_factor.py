# src/factors/volume_factor.py
"""
成交量倍數計分因子
"""

import pandas as pd
from typing import Dict
from src.i18n import t


def calculate_volume_multiplier(df: pd.DataFrame, lang: str = "zh") -> Dict:
    """
    計算成交量乘數（放量判斷）
    """
    lang = "en" if str(lang).startswith("en") else "zh"

    if len(df) < 21:
        err_msg = t("VOL_ERR_INSUFFICIENT_DATA", lang)
        return {"multiplier": 1.0, "detail": err_msg}

    latest_vol = df["volume"].iloc[-1]
    ma20_vol = df["volume"].iloc[-21:-1].mean()

    if ma20_vol > 0 and latest_vol > ma20_vol * 1.5:
        ratio = latest_vol / ma20_vol
        detail = t("VOL_DETAIL_SPIKE", lang, ratio=ratio)
        return {"multiplier": 1.2, "detail": detail}

    no_spike_msg = t("VOL_DETAIL_NO_SPIKE", lang)
    return {"multiplier": 1.0, "detail": no_spike_msg}