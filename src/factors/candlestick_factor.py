# src/factors/candlestick_factor.py
"""
K線型態計分因子（TA-Lib + Bulkowski 統計分級）

【資料來源與可信度聲明】
分級依據為 Thomas Bulkowski 的型態統計研究，數字來自一份 TradingView 開源腳本
的間接引用，未直接核對 Bulkowski 原始出版品（Encyclopedia of Candlestick Charts），
存在轉錄誤差的可能性，應視為「參考性分級」而非絕對精確值。

TA-Lib 總共約 60 餘種型態函式，本分級表僅涵蓋其中已知有具體統計勝率數據的 6 種
（依 Bulkowski 排名前 6 名）。未涵蓋的其餘型態，一律視為「無統計依據」，不計分。

【設計原則：只取當天信度最高的型態，不加總】
若同一天同時偵測到多個已分級型態，僅採用信度最高（分數絕對值最大）的一個代表
當天的K線判斷，避免多個不同可信度的型態混在一起加總造成失真。
"""

import talib
import pandas as pd
from typing import Dict

# ---------------------------------------------------------------------------
# Bulkowski 六級分表
# key: (TA-Lib函式名稱, 訊號方向 1=看漲/-1=看跌)
# ---------------------------------------------------------------------------
BULKOWSKI_TIERS = {
    ("CDL3LINESTRIKE", -1): {"score": -5.0, "name": "Bearish Three Line Strike", "winrate": "67.38%"},
    ("CDL3LINESTRIKE", 1):  {"score": 5.0,  "name": "Bullish Three Line Strike", "winrate": "65.23%"},
    ("CDL3BLACKCROWS", -1): {"score": -4.0, "name": "Bearish Three Black Crows", "winrate": "59.83%"},
    ("CDLEVENINGSTAR", -1): {"score": -4.0, "name": "Bearish Evening Star", "winrate": "55.85%"},
    ("CDLTASUKIGAP", 1):    {"score": 3.0,  "name": "Bullish Upside Tasuki Gap", "winrate": "54.44%"},
    ("CDLINVERTEDHAMMER", 1): {"score": 2.0, "name": "Bullish Inverted Hammer", "winrate": "51.73%"},
}


def calculate_candlestick_score(df: pd.DataFrame) -> Dict:
    """
    掃描當天K線，比對 Bulkowski 分級表，取信度最高者代表。

    :param df: 含 open, high, low, close 欄位的 DataFrame（至少需要足夠天數供TA-Lib判斷多根K棒型態）
    :return: {"score": float, "usable": bool, "detail": str}
    """
    if len(df) < 10:
        return {"score": 0.0, "usable": False, "detail": "K線資料不足，無法進行型態辨識"}

    op = df['open'].values
    hi = df['high'].values
    lo = df['low'].values
    cl = df['close'].values

    matched_patterns = []  # 收集當天所有「命中分級表」的型態

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

    # 關鍵修改 1：改為 usable=True，分數為 0.0，讓 analyzer 能收集到它並呈現在明細中
    if not matched_patterns:
        return {
            "score": 0.0, 
            "usable": True, 
            "detail": "無特殊 K 線型態（不額外加減分）"
        }

    # 取信度最高者（分數絕對值最大）代表當天
    best_match = max(matched_patterns, key=lambda p: abs(p["score"]))

    # 關鍵修改 2：統整 detail 格式
    detail = (f"符合 {best_match['name']}"
              f"（統計可信度 {best_match['winrate']}），"
              f"獲得 {best_match['score']:+.1f}分")

    return {"score": best_match["score"], "usable": True, "detail": detail}