# src/factors/volume_factor.py
"""
成交量輔助乘數因子
- 純函式，邏輯與拆分前的 analyzer.py 完全相同，只是搬移位置
- 注意：這是「乘數」，不是獨立計分因子，不納入 factor_scores 平均計算，
  而是在 analyzer.py 算完平均分之後，額外乘上這個係數
"""

import pandas as pd
from typing import Dict


def calculate_volume_multiplier(df: pd.DataFrame) -> Dict:
    """
    成交量輔助乘數：
    - 若 當日成交量 > 近 20 日平均成交量 * 1.5 -> 1.2
    - 否則 -> 1.0

    :return: {"multiplier": float, "detail": str}
    """
    if len(df) < 21:
        return {"multiplier": 1.0, "detail": "資料不足20日，無法計算均量"}

    latest_vol = df['volume'].iloc[-1]
    ma20_vol = df['volume'].iloc[-21:-1].mean()  # 排除當日，取前 20 日均量

    if ma20_vol > 0 and latest_vol > ma20_vol * 1.5:
        ratio = latest_vol / ma20_vol
        return {"multiplier": 1.2, "detail": f"當日量達20日均量{ratio:.1f}倍（放量），分數×1.2"}

    return {"multiplier": 1.0, "detail": "成交量未出現放大訊號（未越過1.5倍均量）"}