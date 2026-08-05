# src/analyzer.py
"""
量化規則引擎協調模組 (analyzer.py)
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from config import FACTOR_WEIGHTS


def check_veto_rules(
    current_price: float,
    support_price: float,
    target_price: Optional[float],
    selected_factors: List[str],
    insider_net_sell_ratio: Optional[float] = None,
    lang: str = "zh"
) -> Optional[Dict]:

    if "rr" in selected_factors and current_price <= support_price:
        reason = (
            f"現價 ({current_price:.2f}元) 已跌破或等於強力支撐價 ({support_price:.2f}元)，風險評估失準"
            if lang == "zh"
            else f"Current price (${current_price:.2f}) broke/hit strong support (${support_price:.2f}). Risk assessment invalidated."
        )
        return {"veto": True, "reason": reason}

    if "rr" in selected_factors:
        if target_price is None:
            reason = "分析師目標價資料缺失，無法計算風險報酬比" if lang == "zh" else "Analyst target price data missing. R/R ratio unavailable."
            return {"veto": True, "reason": reason}

        if target_price <= current_price:
            reason = (
                f"分析師目標價 ({target_price:.2f}元)<br>低於或等於現價 ({current_price:.2f}元)<br>資料可能異常或看空"
                if lang == "zh"
                else f"Analyst target (${target_price:.2f}) is below/equal to current price (${current_price:.2f}). Bearish or invalid data."
            )
            return {"veto": True, "reason": reason}

        upside = target_price - current_price
        risk = current_price - support_price
        rr_ratio = upside / risk if risk > 0 else 0

        if rr_ratio < 2.0:
            reason = (
                f"現價{current_price:.2f}元<br>支撐價格為{support_price:.2f}元<br>分析師平均目標價為{target_price:.2f}元<br>RR值為1:{rr_ratio:.1f}, 低於建議值1:2"
                if lang == "zh"
                else f"Price: ${current_price:.2f}<br>Support: ${support_price:.2f}<br>Target: ${target_price:.2f}<br>R/R Ratio is 1:{rr_ratio:.1f}, below threshold 1:2"
            )
            return {"veto": True, "reason": reason}

    if insider_net_sell_ratio is not None and insider_net_sell_ratio > 0.005:
        reason = (
            f"近30天內部人淨賣出達流通股本 {insider_net_sell_ratio*100:.2f}%，高於 0.5% 警戒門檻"
            if lang == "zh"
            else f"Insider net selling reached {insider_net_sell_ratio*100:.2f}% over 30 days, exceeding 0.5% threshold."
        )
        return {"veto": True, "reason": reason}

    return None


def _collect_usable_factors(factor_results: Dict[str, Optional[Dict]]) -> Tuple[Dict, Dict]:
    factor_scores = {}
    factor_details = {}

    for key, result in factor_results.items():
        if result is None or not result.get("usable", False):
            continue
        factor_scores[key] = result["score"]
        factor_details[key] = result["detail"]

    return factor_scores, factor_details


def analyze_stock(
    df: pd.DataFrame,
    target_price_data: Dict,
    factor_results: Dict[str, Optional[Dict]],
    volume_result: Dict,
    insider_net_sell_ratio: Optional[float] = None,
    lang: str = "zh"
) -> Dict:
    lang = "en" if lang.startswith("en") else "zh"

    if df.empty or len(df) < 20:
        err_msg = "K線數據不足，無法進行分析" if lang == "zh" else "Insufficient price data for analysis."
        return {"status": "error", "reason": err_msg}

    current_price = float(df['close'].iloc[-1])
    support_price = float(df['close'].min())
    target_price = target_price_data.get("target_mean")

    selected_factors = [key for key, val in factor_results.items() if val is not None]

    candlestick_res = factor_results.get("candlestick")
    k_score = 0.0
    if candlestick_res and candlestick_res.get("usable", False):
        k_score = candlestick_res.get("score", 0.0)

    normal_factor_results = {k: v for k, v in factor_results.items() if k != "candlestick"}
    factor_scores, factor_details = _collect_usable_factors(normal_factor_results)

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

    vol_multiplier = volume_result.get("multiplier", 1.0)
    final_score = round((avg_base_score + k_score) * vol_multiplier, 2)

    all_factor_scores = dict(factor_scores)
    if candlestick_res and candlestick_res.get("usable", False):
        factor_details["candlestick"] = candlestick_res["detail"]
        all_factor_scores["candlestick"] = k_score

    scores_list = list(all_factor_scores.values())
    divergence_warning = None
    if len(scores_list) >= 2 and (max(scores_list) - min(scores_list)) > 2:
        divergence_warning = (
            "⚠️ 訊號分歧：各項分析結果差異較大，建議謹慎評估"
            if lang == "zh"
            else "⚠️ Signal Divergence: Factor results differ significantly. Proceed with caution."
        )

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
        decision = "不建議入場" if lang == "zh" else "Not Recommended"
        decision_reason = veto_result["reason"]
    else:
        status = "success"
        if final_score >= 4.0:
            decision = "強烈建議入場" if lang == "zh" else "Strong Buy"
            decision_reason = (
                f"各項量化因子表現優異（總分 {final_score}分），技術面與風報比皆具備強勁買進訊號。"
                if lang == "zh"
                else f"Excellent factor ratings ({final_score} pts). Technicals and R/R show strong buy signals."
            )
        elif final_score >= 2.0:
            decision = "建議入場，可觀察" if lang == "zh" else "Buy / Accumulate"
            decision_reason = (
                f"量化評分為 {final_score}分 達到入場門檻，整體風險可控，可考慮分批佈局。"
                if lang == "zh"
                else f"Score reached entry threshold ({final_score} pts). Controlled risk; partial positions recommended."
            )
        elif final_score >= -1.0:
            decision = "訊號中性，建議觀望" if lang == "zh" else "Neutral / Hold"
            decision_reason = (
                f"量化評分為 {final_score}分，多空訊號相抵，建議觀望。"
                if lang == "zh"
                else f"Neutral rating ({final_score} pts). Bullish and bearish signals balance out."
            )
        else:
            decision = "不建議入場" if lang == "zh" else "Not Recommended"
            decision_reason = (
                f"量化評分為 {final_score}分，整體技術面與風報比偏弱。"
                if lang == "zh"
                else f"Weak rating ({final_score} pts). Technicals and R/R ratio are weak."
            )

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