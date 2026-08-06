# src/recommendation_engine.py

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

    # -----------------------------------------------------------------
    # 【新增】建議進場價 / 買到賺到價
    # 這不是計分因子（不在 factor_details 裡），獨立成一個欄位輸出，
    # 不管 analysis_result 的 status 是 success 還是 veto 都照樣顯示——
    # 即使系統判定「不建議入場」，使用者可能還是想知道「如果要進，大概在哪個價位」，
    # 這兩個數字本身不代表「建議你進場」，純粹是價格參考資訊。
    # -----------------------------------------------------------------
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