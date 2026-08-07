"""
格式化與建議輸出模組 (recommendation_engine.py)
"""

from typing import Dict, Optional
from src.i18n import t

# 因子 Key 對照表
FACTOR_KEY_MAP = {
    "rr": "LABEL_RR",
    "candlestick": "LABEL_CANDLESTICK",
    "news": "LABEL_NEWS",
    "put_call": "LABEL_PUT_CALL"
}


def format_analysis_output(analysis_result: Dict, entry_price_data: Optional[Dict] = None, lang: str = "zh") -> Dict:
    lang = "en" if str(lang).startswith("en") else "zh"

    if analysis_result.get("status") == "error":
        return {
            "decision": t("ANALYSIS_FAILED", lang),
            "reason": analysis_result.get("reason", t("UNKNOWN_ERROR", lang)),
            "score": None,
            "factor_lines": [],
            "warning": None,
            "entry_price": None
        }

    details = analysis_result.get("details", {})
    factor_details = details.get("factor_details", {})
    factor_scores = details.get("factor_scores", {})
    raw_factor_results = analysis_result.get("raw_factor_results", {})

    factor_lines = []
    
    # 針對使用者選擇並執行的所有因子進行逐一格式化
    for key, result in raw_factor_results.items():
        if result is None:
            continue

        i18n_key = FACTOR_KEY_MAP.get(key)
        label = t(i18n_key, lang) if i18n_key else key

        # 檢查該因子是否成功取得有效資料
        is_usable = result.get("usable", False) if isinstance(result, dict) else False
        score = factor_scores.get(key) if is_usable else None

        if not is_usable or score is None:
            # 未取得資料：僅顯示「未取得資料」，不包含分數或細節分析
            no_data_str = t("NO_DATA_AVAILABLE", lang)
            line = t("FACTOR_LINE_NO_SCORE", lang, label=label, detail=no_data_str)
            factor_lines.append(line)
        else:
            detail = factor_details.get(key, result.get("detail", ""))
            score_str = t("SCORE_PTS", lang, score=score)
            line = t("FACTOR_LINE_WITH_SCORE", lang, label=label, detail=detail, score_str=score_str)
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

    # 建議進場價參考資訊 (無論 success 或 veto 均呈現)
    entry_price_output = None
    if entry_price_data and entry_price_data.get("available"):
        entry_price_output = {
            "low": entry_price_data.get("entry_price_low"),
            "high": entry_price_data.get("entry_price_high"),
            "best_value": entry_price_data.get("best_value_price"),
            "detail": entry_price_data.get("detail")
        }

    return {
        "decision": display_decision,
        "reason": analysis_result["reason"],
        "score": final_score,
        "factor_lines": factor_lines,
        "warning": analysis_result.get("divergence_warning"),
        "entry_price": entry_price_output
    }