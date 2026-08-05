# src/factors/volume_factor.py
"""
成交量倍數計分因子
"""

import pandas as pd
from typing import Dict


def calculate_volume_multiplier(df: pd.DataFrame, lang: str = "zh") -> Dict:
    """
    計算成交量乘數（放量判斷）
    """
    lang = "en" if lang.startswith("en") else "zh"

    if len(df) < 21:
        err_msg = (
            "資料不足20日，無法計算均量"
            if lang == "zh"
            else "Insufficient data (<20 days) for volume MA"
        )
        return {"multiplier": 1.0, "detail": err_msg}

    latest_vol = df["volume"].iloc[-1]
    ma20_vol = df["volume"].iloc[-21:-1].mean()

    if ma20_vol > 0 and latest_vol > ma20_vol * 1.5:
        ratio = latest_vol / ma20_vol
        detail = (
            f"當日量達20日均量{ratio:.1f}倍（放量），分數×1.2"
            if lang == "zh"
            else f"Volume reached {ratio:.1f}x 20-day MA (Volume Spike), score x1.2"
        )
        return {"multiplier": 1.2, "detail": detail}

    no_spike_msg = (
        "成交量未出現放大訊號（未越過1.5倍均量）"
        if lang == "zh"
        else "No volume surge detected (<1.5x 20-day MA)"
    )
    return {"multiplier": 1.0, "detail": no_spike_msg}