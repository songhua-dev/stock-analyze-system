"""
建議進場價 / 買到賺到價 計算模組

【重要：這不是計分因子】
本模組回傳的不是 {"score", "usable", "detail"} 這種計分格式，
不會被 analyzer.py 收進 factor_results 去參與加權平均計算。
它單純計算「兩個價格數字」，供 recommendation_engine.py 另外組裝進輸出，
性質類似 analyzer.py 否決規則裡已經在算的 current_price/support_price 這類
「核心價格資訊」，不是使用者可以勾選要不要看的「分析角度」。

【定義】
- 建議進場價：現價 到 短期支撐（近20日最低收盤）之間的區間，
  代表價格回踩短期支撐時的合理試探進場範圍。
- 買到賺到價：強力支撐（近120日最低收盤）附近，
  代表左側安全邊際較高、最具吸引力的加碼價位。

兩者都只需要價格資料，不需要分析師目標價，因此不受「有沒有勾RR值」影響，
main.py 應該永遠呼叫這個函式（不受 selected_factors 開關限制）。
"""

from typing import Dict, Optional
from src.i18n import t


def calculate_entry_price(
    current_price: Optional[float],
    short_support: Optional[float],
    strong_support: Optional[float],
    lang: str = "zh"
) -> Dict:
    """
    :param current_price: 現價
    :param short_support: 短期支撐（近20日最低收盤）
    :param strong_support: 強力支撐（近120日最低收盤，與RR值否決規則使用同一個數字）
    :param lang: 語言標籤 ('zh' 或 'en')
    :return: {
        "available": bool,
        "entry_price_low": float,   # 建議進場價區間下緣（=短期支撐）
        "entry_price_high": float,  # 建議進場價區間上緣（=現價）
        "best_value_price": float,  # 買到賺到價（=強力支撐）
        "detail": str
    }
    """
    lang = "en" if str(lang).startswith("en") else "zh"

    if current_price is None or short_support is None or strong_support is None:
        return {
            "available": False,
            "entry_price_low": None,
            "entry_price_high": None,
            "best_value_price": None,
            "detail": t("ENTRY_PRICE_ERR_INSUFFICIENT_DATA", lang)
        }

    entry_price_low = round(short_support, 2)
    entry_price_high = round(current_price, 2)
    best_value_price = round(strong_support, 2)

    detail = t(
        "ENTRY_PRICE_DETAIL",
        lang,
        low=entry_price_low,
        high=entry_price_high,
        best_value=best_value_price
    )

    return {
        "available": True,
        "entry_price_low": entry_price_low,
        "entry_price_high": entry_price_high,
        "best_value_price": best_value_price,
        "detail": detail
    }


if __name__ == "__main__":
    # 簡易測試（純數學運算，不依賴外部API）
    print("🚀 測試 entry_price_factor.py (ZH)...")
    result_zh = calculate_entry_price(current_price=125.89, short_support=118.50, strong_support=95.20, lang="zh")
    print(result_zh)

    print("\n🚀 測試 entry_price_factor.py (EN)...")
    result_en = calculate_entry_price(current_price=125.89, short_support=118.50, strong_support=95.20, lang="en")
    print(result_en)