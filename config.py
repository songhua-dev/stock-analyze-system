# config.py
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_ENDPOINT = os.getenv("ALPACA_ENDPOINT", "https://paper-api.alpaca.markets")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# 基本檢查
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError("未在 .env 中找到 Alpaca API Key 或 Secret Key，請檢查設定！")
if not GROQ_API_KEY:
    raise ValueError("未在 .env 中找到 Groq API Key，請檢查設定！")

# ===================================================================
# 各因子基礎權重設定 (Base Weights)
# 數值代表相對重要程度，系統會自動根據使用者勾選的項目進行歸一化 (Sum to 100%)
# ===================================================================
FACTOR_WEIGHTS = {
    "rr": 3.0,          # 風報比
    "put_call": 1.5,    # 籌碼面
    "news": 1.0,        # 新聞情緒
}