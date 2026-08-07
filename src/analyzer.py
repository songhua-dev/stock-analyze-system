"""
量化規則引擎協調模組 (analyzer.py)
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from config import FACTOR_WEIGHTS
from src.i18n import t


def check_veto_rules(
    current_price: float,
    support_price: float,
    target_price: Optional[float],
    selected_factors: List[str],
    insider_net_sell_ratio: Optional[float] = None,
    lang: str = "zh"
) -> Optional[Dict]:

    # 1. 價格跌破/等於強力支撐
    if "rr" in selected_factors and current_price <= support_price:
        reason = t("VETO_PRICE_BELOW_SUPPORT", lang, current_price=current_price, support_price=support_price)
        return {"veto": True, "reason": reason}

    # 2. RR 相關 Veto：僅在取得目標價時才做判斷（未取得資料則跳過 veto，不直接觸發 veto）
    if "rr" in selected_factors and target_price is not None:
        if target_price <= current_price:
            reason = t("VETO_TARGET_BELOW_CURRENT", lang, target_price=target_price, current_price=current_price)
            return {"veto": True, "reason": reason}

        upside = target_price - current_price
        risk = current_price - support_price
        rr_ratio = upside / risk if risk > 0 else 0

        if rr_ratio < 2.0:
            reason = t("VETO_RR_TOO_LOW", lang, current_price=current_price, support_price=support_price, target_price=target_price, rr_ratio=rr_ratio)
            return {"veto": True, "reason": reason}

    # 3. 內部人賣出比例過高
    if insider_net_sell_ratio is not None and insider_net_sell_ratio > 0.005:
        reason = t("VETO_INSIDER_NET_SELL", lang, ratio=insider_net_sell_ratio * 100)
        return {"veto": True, "reason": reason}

    return None


def _collect_usable_factors(factor_results: Dict[str, Optional[Dict]]) -> Tuple[Dict, Dict]:
    factor_scores = {}
    factor_details = {}

    for key, result in factor_results.items():
        if result is None or not result.get("usable", False):
            continue
        factor_scores[key] = result.get("score")
        factor_details[key] = result.get("detail")

    return factor_scores, factor_details


def analyze_stock(
    df: pd.DataFrame,
    target_price_data: Dict,
    factor_results: Dict[str, Optional[Dict]],
    volume_result: Dict,
    insider_net_sell_ratio: Optional[float] = None,
    lang: str = "zh"
) -> Dict:
    lang = "en" if str(lang).startswith("en") else "zh"

    if df.empty or len(df) < 20:
        err_msg = t("ERR_INSUFFICIENT_DATA", lang)
        return {"status": "error", "reason": err_msg}

    current_price = float(df['close'].iloc[-1])
    support_price = float(df['close'].min())
    target_price = target_price_data.get("target_mean") if target_price_data else None

    selected_factors = [key for key, val in factor_results.items() if val is not None]

    candlestick_res = factor_results.get("candlestick")
    k_score = 0.0
    if candlestick_res and candlestick_res.get("usable", False):
        k_score = candlestick_res.get("score") or 0.0

    normal_factor_results = {k: v for k, v in factor_results.items() if k != "candlestick"}
    factor_scores, factor_details = _collect_usable_factors(normal_factor_results)

    # 計算可用因子的加權平均分數
    usable_scores = {k: v for k, v in factor_scores.items() if v is not None}
    if usable_scores:
        weighted_score_sum = 0.0
        total_weight = 0.0

        for key, score in usable_scores.items():
            weight = FACTOR_WEIGHTS.get(key, 1.0)
            weighted_score_sum += score * weight
            total_weight += weight

        avg_base_score = weighted_score_sum / total_weight if total_weight > 0 else 0.0
    else:
        avg_base_score = 0.0

    vol_multiplier = volume_result.get("multiplier", 1.0)
    final_score = round((avg_base_score + k_score) * vol_multiplier, 2)

    all_factor_scores = dict(factor_scores)
    if candlestick_res and candlestick_res.get("usable", False):
        factor_details["candlestick"] = candlestick_res.get("detail")
        all_factor_scores["candlestick"] = k_score

    scores_list = [s for s in all_factor_scores.values() if s is not None]
    divergence_warning = None
    if len(scores_list) >= 2 and (max(scores_list) - min(scores_list)) > 2:
        divergence_warning = t("WARNING_DIVERGENCE", lang)

    # 執行 Veto 檢查
    veto_result = check_veto_rules(
        current_price=current_price,
        support_price=support_price,
        target_price=target_price,
        selected_factors=selected_factors,
        insider_net_sell_ratio=insider_net_sell_ratio,
        lang=lang
    )

    if veto_result is not None:
        status = "veto"
        decision = t("DECISION_NOT_RECOMMENDED", lang)
        decision_reason = veto_result["reason"]
    else:
        status = "success"
        if final_score >= 4.0:
            decision = t("DECISION_STRONG_BUY", lang)
            decision_reason = t("REASON_STRONG_BUY", lang, score=final_score)
        elif final_score >= 2.0:
            decision = t("DECISION_BUY_ACCUMULATE", lang)
            decision_reason = t("REASON_BUY_ACCUMULATE", lang, score=final_score)
        elif final_score >= -1.0:
            decision = t("DECISION_NEUTRAL", lang)
            decision_reason = t("REASON_NEUTRAL", lang, score=final_score)
        else:
            decision = t("DECISION_NOT_RECOMMENDED", lang)
            decision_reason = t("REASON_NOT_RECOMMENDED", lang, score=final_score)

    rr_calc = round((target_price - current_price) / (current_price - support_price), 2) if target_price and (current_price - support_price) > 0 else 0

    return {
        "status": status,
        "decision": decision,
        "reason": decision_reason,
        "final_score": final_score,
        "divergence_warning": divergence_warning,
        "raw_factor_results": factor_results,  # 傳遞完整的原始因子結果
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