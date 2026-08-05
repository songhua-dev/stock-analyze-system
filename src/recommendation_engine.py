# src/recommendation_engine.py

from typing import Dict

FACTOR_LABELS = {
    "rr": "RR值",
    "candlestick": "K線型態",
    "news": "新聞情緒",
    "put_call": "Put/Call"
}


def format_analysis_output(analysis_result: Dict) -> Dict:
    if analysis_result.get("status") == "error":
        return {
            "decision": "無法分析",
            "reason": analysis_result.get("reason", "未知錯誤"),
            "score": None,
            "factor_lines": [],
            "warning": None
        }

    details = analysis_result.get("details", {})
    factor_details = details.get("factor_details", {})
    factor_scores = details.get("factor_scores", {})

    # 需求 3 & 4：組裝因子明細並補上得分標示（加上 <strong> 粗體標籤）
    factor_lines = []
    for key, detail in factor_details.items():
        label = FACTOR_LABELS.get(key, key)
        score = factor_scores.get(key)
        
        # 格式化得分顯示 (+1分, -2分, 0分)
        if score is not None:
            score_str = f"+{score}分" if score > 0 else f"{score}分"
            factor_lines.append(f"<strong>{label}：</strong>{detail}（獲得 {score_str}）")
        else:
            factor_lines.append(f"<strong>{label}：</strong>{detail}")

    volume_detail = details.get("volume_detail")
    if volume_detail:
        factor_lines.append(f"<strong>成交量：</strong>{volume_detail}")

    # 需求 1：修改頂部建議顯示格式
    final_score = analysis_result.get("final_score")
    decision_text = analysis_result["decision"]
    display_decision = f"{decision_text}（平均 {final_score}分）" if final_score is not None else decision_text

    return {
        "decision": display_decision,
        "reason": analysis_result["reason"],
        "score": final_score,
        "factor_lines": factor_lines,
        "warning": analysis_result.get("divergence_warning")
    }