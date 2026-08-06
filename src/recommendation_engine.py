# src/recommendation_engine.py

from typing import Dict
from src.i18n import t

# 因子 Key 對照表
FACTOR_KEY_MAP = {
    "rr": "LABEL_RR",
    "candlestick": "LABEL_CANDLESTICK",
    "news": "LABEL_NEWS",
    "put_call": "LABEL_PUT_CALL"
}


def format_analysis_output(analysis_result: Dict, lang: str = "zh") -> Dict:
    lang = "en" if str(lang).startswith("en") else "zh"
    
    if analysis_result.get("status") == "error":
        return {
            "decision": t("ANALYSIS_FAILED", lang),
            "reason": analysis_result.get("reason", t("UNKNOWN_ERROR", lang)),
            "score": None,
            "factor_lines": [],
            "warning": None
        }

    details = analysis_result.get("details", {})
    factor_details = details.get("factor_details", {})
    factor_scores = details.get("factor_scores", {})

    factor_lines = []
    for key, detail in factor_details.items():
        # 取得多語系因子標籤
        i18n_key = FACTOR_KEY_MAP.get(key)
        label = t(i18n_key, lang) if i18n_key else key
        
        score = factor_scores.get(key)
        
        if score is not None:
            score_str = t("SCORE_PTS", lang, score=score)
            line = t("FACTOR_LINE_WITH_SCORE", lang, label=label, detail=detail, score_str=score_str)
            factor_lines.append(line)
        else:
            line = t("FACTOR_LINE_NO_SCORE", lang, label=label, detail=detail)
            factor_lines.append(line)

    volume_detail = details.get("volume_detail")
    if volume_detail:
        vol_label = t("LABEL_VOLUME", lang)
        vol_line = t("VOLUME_LINE", lang, vol_label=vol_label, volume_detail=volume_detail)
        factor_lines.append(vol_line)

    final_score = analysis_result.get("final_score")
    decision_text = analysis_result["decision"]
    
    if final_score is not None:
        display_decision = t("DECISION_WITH_SCORE", lang, decision_text=decision_text, final_score=final_score)
    else:
        display_decision = decision_text

    return {
        "decision": display_decision,
        "reason": analysis_result["reason"],
        "score": final_score,
        "factor_lines": factor_lines,
        "warning": analysis_result.get("divergence_warning")
    }