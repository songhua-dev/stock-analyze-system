# src/analyzer.py
"""
量化規則引擎協調模組 (analyzer.py)
【方案1架構】本檔案不 import 任何 factors/ 模組，不主動呼叫任何因子計分函式。
所有因子模組的呼叫（是否勾選、要不要跑該因子）皆由 main.py 統一負責，
main.py 呼叫完各因子模組後，把結果彙整成 factor_results 字典傳入 analyze_stock()。

analyzer.py 專心負責三件事：
1. 否決規則檢查（僅對使用者有勾選的因子生效）
2. 常態因子採動態歸一化加權，K線採外掛加減分：(基礎分數 + K線分數) * 成交量乘數
3. 依分數對照表決定最終建議與分歧警示（若觸發否決，則覆蓋建議與總分）

統一因子回傳格式為 {"score": float, "usable": bool, "detail": str}，
usable=False 代表該因子這次無法判讀，不納入計算。
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from config import FACTOR_WEIGHTS  # 匯入動態權重設定


# ===================================================================
# 1. 否決規則清單 (Veto Rules) - 僅對使用者勾選的因子生效
# ===================================================================

def check_veto_rules(
    current_price: float,
    support_price: float,
    target_price: Optional[float],
    selected_factors: List[str],
    insider_net_sell_ratio: Optional[float] = None
) -> Optional[Dict]:

    # 1. 支撐價跌破檢查
    if "rr" in selected_factors and current_price <= support_price:
        return {
            "veto": True,
            "reason": f"現價 ({current_price:.2f}元) 已跌破或等於強力支撐價 ({support_price:.2f}元)，風險評估失準"
        }

    # 2. RR 值否決檢查
    if "rr" in selected_factors:
        if target_price is None:
            return {
                "veto": True,
                "reason": "分析師目標價資料缺失，無法計算風險報酬比"
            }

        if target_price <= current_price:
            return {
                "veto": True,
                "reason": f"分析師目標價 ({target_price:.2f}元)<br>低於或等於現價 ({current_price:.2f}元)<br>資料可能異常或看空"
            }

        upside = target_price - current_price
        risk = current_price - support_price
        rr_ratio = upside / risk if risk > 0 else 0

        if rr_ratio < 2.0:
            return {
                "veto": True,
                # 換行格式並加上「元」
                "reason": f"現價{current_price:.2f}元<br>支撐價格為{support_price:.2f}元<br>分析師平均目標價為{target_price:.2f}元<br>RR值為1:{rr_ratio:.1f}, 低於建議值1:2"
            }

    if insider_net_sell_ratio is not None and insider_net_sell_ratio > 0.005:
        return {
            "veto": True,
            "reason": f"近30天內部人淨賣出達流通股本 {insider_net_sell_ratio*100:.2f}%，高於 0.5% 警戒門檻"
        }

    return None


# ===================================================================
# 2. 因子整合輔助函式（可插拔接口的核心）
# ===================================================================

def _collect_usable_factors(factor_results: Dict[str, Optional[Dict]]) -> Tuple[Dict, Dict]:
    """
    掃過 main.py 傳入的 factor_results，只留下 usable=True 的因子，
    整理成 factor_scores 與 factor_details。
    """
    factor_scores = {}
    factor_details = {}

    for key, result in factor_results.items():
        if result is None:
            continue
        if not result.get("usable", False):
            continue
        factor_scores[key] = result["score"]
        factor_details[key] = result["detail"]

    return factor_scores, factor_details


# ===================================================================
# 3. 量化規則引擎主函式 (Main Entry Point)
# ===================================================================

def analyze_stock(
    df: pd.DataFrame,
    target_price_data: Dict,
    factor_results: Dict[str, Optional[Dict]],
    volume_result: Dict,
    insider_net_sell_ratio: Optional[float] = None
) -> Dict:
    """
    量化規則引擎主要進入點
    """
    if df.empty or len(df) < 20:
        return {"status": "error", "reason": "K線數據不足，無法進行分析"}

    current_price = float(df['close'].iloc[-1])
    support_price = float(df['close'].min())  # 近120交易日最低收盤價（強力支撐）
    target_price = target_price_data.get("target_mean")

    # 找出使用者實際有勾選的因子
    selected_factors = [key for key, val in factor_results.items() if val is not None]

    # 1. 獨立分離 K 線因子，不讓它佔據常態加權分母
    candlestick_res = factor_results.get("candlestick")
    k_score = 0.0
    if candlestick_res and candlestick_res.get("usable", False):
        k_score = candlestick_res.get("score", 0.0)

    # 2. 收集其餘常態因子分數 (RR、Put/Call、News 等)[cite: 5]
    normal_factor_results = {k: v for k, v in factor_results.items() if k != "candlestick"}
    factor_scores, factor_details = _collect_usable_factors(normal_factor_results)

    # 3. 計算常態因子的動態歸一化加權平均[cite: 5]
    if factor_scores:
        weighted_score_sum = 0.0
        total_weight = 0.0

        for key, score in factor_scores.items():
            weight = FACTOR_WEIGHTS.get(key, 1.0)
            weighted_score_sum += score * weight
            total_weight += weight

        avg_base_score = weighted_score_sum / total_weight if total_weight > 0 else 0.0
    else:
        avg_base_score = 0.0

    # 4. 取得背景成交量乘數並計算最終總分：(基礎分數 + K線分數) * 成交量乘數[cite: 5]
    vol_multiplier = volume_result.get("multiplier", 1.0)
    final_score = round((avg_base_score + k_score) * vol_multiplier, 2)

    # 5. 將 K 線明細與分數補回總明細字典，供前端 UI 呈現與分歧檢查[cite: 5]
    all_factor_scores = dict(factor_scores)
    if candlestick_res and candlestick_res.get("usable", False):
        factor_details["candlestick"] = candlestick_res["detail"]
        all_factor_scores["candlestick"] = k_score

    # 6. 檢查訊號分歧 (涵蓋所有已判讀因子)
    scores_list = list(all_factor_scores.values())
    divergence_warning = None
    if len(scores_list) >= 2 and (max(scores_list) - min(scores_list)) > 2:
        divergence_warning = "⚠️ 訊號分歧：各項分析結果差異較大，建議謹慎評估"

    # 7. 進行否決規則檢查
    veto_result = check_veto_rules(
        current_price=current_price,
        support_price=support_price,
        target_price=target_price,
        selected_factors=selected_factors,
        insider_net_sell_ratio=insider_net_sell_ratio
    )

    # 8. 決定最終建議結論 (若觸發否決，優先標註否決狀態，但保留所有 details 與分數)[cite: 5]
    if veto_result is not None:
        status = "veto"
        decision = "不建議入場"
        decision_reason = veto_result["reason"]
    else:
        status = "success"
        if final_score >= 4.0:
            decision = "強烈建議入場"
            decision_reason = f"各項量化因子表現優異（總分 {final_score}分），技術面與風報比皆具備強勁買進訊號。"
        elif final_score >= 2.0:
            decision = "建議入場，可觀察"
            decision_reason = f"量化評分為 {final_score}分 達到入場門檻，整體風險可控，可考慮分批佈局。"
        elif final_score >= -1.0:
            decision = "訊號中性，建議觀望"
            decision_reason = f"量化評分為 {final_score}分，多空訊號相抵，建議觀望。"
        else:
            decision = "不建議入場"
            decision_reason = f"量化評分為 {final_score}分，整體技術面與風報比偏弱。"

    rr_calc = round((target_price - current_price) / (current_price - support_price), 2) if target_price and (current_price - support_price) > 0 else 0

    return {
        "status": status,
        "decision": decision,
        "reason": decision_reason,
        "final_score": final_score,
        "divergence_warning": divergence_warning,
        "details": {
            "factor_scores": all_factor_scores,
            "factor_details": factor_details,
            "volume_multiplier": vol_multiplier,
            "volume_detail": volume_result.get("detail", ""),
            "current_price": current_price,
            "support_price": support_price,
            "target_price": target_price,
            "rr_ratio": rr_calc
        }
    }