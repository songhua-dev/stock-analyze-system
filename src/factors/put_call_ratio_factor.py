# src/factors/put_call_ratio_factor.py
"""
Put/Call 比率分析因子模組 (put_call_ratio_factor.py)
回傳標準格式: {"score": float, "usable": bool, "detail": str}
"""

from typing import Dict, Optional


def calculate_put_call_ratio_score(
    pc_ratio: Optional[float],
    data_type: str = "當日成交量"
) -> Dict:
    """
    根據 Put/Call 比率計算得分與產生說明文字
    
    :param pc_ratio: Put/Call 比率數值 (例如 0.524)
    :param data_type: 資料來源類型 (預設: "當日成交量")
    """
    if pc_ratio is None:
        return {
            "score": 0.0,
            "usable": False,
            "detail": " Put/Call 比率資料缺失，無法進行分析"
        }

    # 1. 判斷多空方向與得分
    if pc_ratio < 0.7:
        sentiment_text = "偏多"
        score = 1.0
    elif pc_ratio > 1.0:
        sentiment_text = "偏空"
        score = -1.0
    else:
        sentiment_text = "中性"
        score = 0.0

    # 2. 需求 4 精簡格式：比率 0.524(當日成交量): 偏多
    # （分數部分會由 recommendation_engine.py 統一在尾端補上）
    detail = f"比率 {pc_ratio:.3f}({data_type}): {sentiment_text}"

    return {
        "score": score,
        "usable": True,
        "detail": detail
    }


if __name__ == "__main__":
    # 單元測試
    test_result = calculate_put_call_ratio_score(0.524)
    print("測試結果：", test_result)