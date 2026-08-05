# config.py
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 讀取環境變數，若找不到則預設為 "DEMO"
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "DEMO_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "DEMO_SECRET")
ALPACA_ENDPOINT = os.getenv("ALPACA_ENDPOINT", "https://paper-api.alpaca.markets")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "DEMO_GROQ_KEY")

# 標示目前是否為 Demo 模式
IS_DEMO_MODE = (ALPACA_API_KEY == "DEMO_KEY" or GROQ_API_KEY == "DEMO_GROQ_KEY")

if IS_DEMO_MODE:
    print("⚠️ 注意：目前處於 Demo 模式（未設定 Alpaca 或 Groq API Key）")

# ===================================================================
# 各因子基礎權重設定 (Base Weights)
# 數值代表相對重要程度，系統會自動根據使用者勾選的項目進行歸一化 (Sum to 100%)
# ===================================================================
FACTOR_WEIGHTS = {
    "rr": 3.0,          # 風報比
    "put_call": 1.5,    # 籌碼面
    "news": 1.0,        # 新聞情緒
}