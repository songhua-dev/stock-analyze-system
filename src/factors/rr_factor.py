# src/factors/rr_factor.py
"""
RR值（風險報酬比）計分因子
- 純函式，邏輯與拆分前的 analyzer.py 完全相同，只是搬移位置
"""


def calculate_rr_score(current_price: float, support_price: float, target_price: float) -> dict:
    """
    RR 值因子分級計分：
    - 1:2 <= RR < 1:3  -> +1
    - 1:3 <= RR < 1:5  -> +3
    - RR >= 1:5        -> +5

    :return: {"score": float, "usable": True, "detail": str}
             RR值因子在否決規則通過後必定可計算，usable 恆為 True
    """
    upside = target_price - current_price
    risk = current_price - support_price

    if risk <= 0:
        return {"score": 0.0, "usable": False, "detail": "支撐價計算異常，無法計算RR值"}

    rr_ratio = upside / risk

    if rr_ratio >= 5.0:
        score = 5.0
    elif rr_ratio >= 3.0:
        score = 3.0
    elif rr_ratio >= 2.0:
        score = 1.0
    else:
        score = 0.0

    detail = f"RR值 1:{rr_ratio:.2f}，獲得{score:+.0f}分" if score > 0 else f"RR值 1:{rr_ratio:.2f}"

    return {"score": score, "usable": True, "detail": detail}