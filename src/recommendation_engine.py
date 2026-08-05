# src/recommendation_engine.py

from typing import Dict

FACTOR_LABELS = {
    "zh": {
        "rr": "RR值",
        "candlestick": "K線型態",
        "news": "新聞情緒",
        "put_call": "Put/Call"
    },
    "en": {
        "rr": "RR Ratio",
        "candlestick": "Candlestick",
        "news": "News Sentiment",
        "put_call": "Put/Call Ratio"
    }
}


def format_analysis_output(analysis_result: Dict, lang: str = "zh") -> Dict:
    lang = "en" if lang.startswith("en") else "zh"
    
    if analysis_result.get("status") == "error":
        return {
            "decision": "無法分析" if lang == "zh" else "Analysis Failed",
            "reason": analysis_result.get("reason", "未知錯誤" if lang == "zh" else "Unknown Error"),
            "score": None,
            "factor_lines": [],
            "warning": None
        }

    details = analysis_result.get("details", {})
    factor_details = details.get("factor_details", {})
    factor_scores = details.get("factor_scores", {})

    labels = FACTOR_LABELS.get(lang, FACTOR_LABELS["zh"])

    factor_lines = []
    for key, detail in factor_details.items():
        label = labels.get(key, key)
        score = factor_scores.get(key)
        
        if score is not None:
            if lang == "zh":
                score_str = f"+{score}分" if score > 0 else f"{score}分"
                factor_lines.append(f"<strong>{label}：</strong>{detail}（獲得 {score_str}）")
            else:
                score_str = f"+{score} pts" if score > 0 else f"{score} pts"
                factor_lines.append(f"<strong>{label}: </strong>{detail} ({score_str})")
        else:
            factor_lines.append(f"<strong>{label}：</strong>{detail}" if lang == "zh" else f"<strong>{label}: </strong>{detail}")

    volume_detail = details.get("volume_detail")
    if volume_detail:
        vol_label = "成交量：" if lang == "zh" else "Volume: "
        factor_lines.append(f"<strong>{vol_label}</strong>{volume_detail}")

    final_score = analysis_result.get("final_score")
    decision_text = analysis_result["decision"]
    
    if final_score is not None:
        display_decision = f"{decision_text}（平均 {final_score}分）" if lang == "zh" else f"{decision_text} (Avg. {final_score} pts)"
    else:
        display_decision = decision_text

    return {
        "decision": display_decision,
        "reason": analysis_result["reason"],
        "score": final_score,
        "factor_lines": factor_lines,
        "warning": analysis_result.get("divergence_warning")
    }