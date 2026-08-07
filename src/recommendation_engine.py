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

    # 如果分析過程直接報錯，回傳錯誤狀態
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
    
    # 定義流量限制的提示文字（安全地透過 try-catch 嘗試取得 i18n，若失敗則使用預設備用字串）
    try:
        rate_limit_msg = t("DEMO_RATE_LIMIT_WARNING", lang)
    except Exception:
        rate_limit_msg = (
            "Demo版目前被yfinance限制流量，建議至Github下載完整程式碼操作可以避免"
            if lang == "zh"
            else "Demo version is rate-limited by yfinance. Download full code from Github to avoid this."
        )

    # 針對使用者選擇並執行的所有因子進行逐一格式化
    for key, result in raw_factor_results.items():
        if result is None:
            continue

        i18n_key = FACTOR_KEY_MAP.get(key)
        label = t(i18n_key, lang) if i18n_key else key

        # 檢查該因子是否成功取得有效資料
        is_usable = result.get("usable", False) if isinstance(result, dict) else False
        score = factor_scores.get(key) if is_usable else None

        # --- 修改重點：偵測 RR 因子的流量限制狀態 ---
        if key == "rr" and not is_usable and result.get("detail") == "rate_limited":
            # 直接顯示流量限制警告，不顯示分數
            factor_lines.append(f"{label}: {rate_limit_msg}")
        
        elif not is_usable or score is None:
            # 原本的無資料處理
            no_data_str = t("NO_DATA_AVAILABLE", lang)
            line = t("FACTOR_LINE_NO_SCORE", lang, label=label, detail=no_data_str)
            factor_lines.append(line)
        else:
            # 正常有分數的處理
            detail = factor_details.get(key, result.get("detail", ""))
            score_str = t("SCORE_PTS", lang, score=score)
            line = t("FACTOR_LINE_WITH_SCORE", lang, label=label, detail=detail, score_str=score_str)
            factor_lines.append(line)

    # 成交量處理
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

    # 建議進場價處理
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