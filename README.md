# 📈 US Stock Quantitative Analysis System

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask-green)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Render-Live%20Demo-brightgreen)](https://stock-analyze-uodo.onrender.com)

A modular, pluggable quantitative analysis tool for US stocks. Instead of drowning in raw indicators, it combines a few independent signals — candlestick patterns, risk/reward ratio, options Put/Call sentiment, and LLM-based news sentiment — into a single plain-language recommendation.

> 中文摘要：一個模組化、可插拔的美股量化分析工具，把K線型態、風報比、選擇權籌碼面、新聞情緒這幾個獨立訊號，綜合成一句白話文的進場建議。

**Live demo:** https://stock-analyze-uodo.onrender.com

---

## Why this exists

Most retail-facing chart tools show you raw indicators and expect you to interpret them. This project does the opposite: each signal is scored independently, and the user picks which ones to combine. No single indicator decides the outcome — a hard veto layer (RR ratio, support breakdown, abnormal analyst target) blocks a recommendation outright regardless of how well other signals score.

> 中文摘要：多數工具丟出一堆原始指標讓使用者自己解讀，這個專案反過來——每個訊號各自算分，使用者自己選要參考哪些，並有一層否決規則（風報比、跌破支撐、目標價異常）可以直接擋下建議，不受其他因子高分影響。

---

## Core design

- **Pluggable factor engine** — each analysis method lives in its own file under `factors/`, all returning the same `{score, usable, detail}` shape. Adding a new factor means writing one file and registering a weight in `config.py`, not touching the scoring engine itself.
- **Veto rules run independently of factor selection.** If RR ratio falls under 1:2, price breaks support, or the analyst target price looks inconsistent, the system refuses to recommend an entry — this check always runs, whatever the user has selected.
- **Candlestick scoring is tiered by statistical reliability, not treated as one-size-fits-all.** TA-Lib detects 60+ patterns; only the ones with a documented historical win rate (Bulkowski's ranking) get scored, tiered by how reliable that pattern actually is. Everything else scores 0 rather than pretending to have equal confidence.
- **News sentiment is LLM-scored under explicit constraints, not free-form.** The prompt restricts high-magnitude scores (±4~5) to concrete categories (verified technical breakthroughs, major contract wins vs. debt exceeding revenue, product recalls); everything else is capped to a narrower ±1~3 band. This exists specifically to reduce subjective drift in LLM scoring.
- **Dynamic weighted average, not a flat mean.** Each factor's contribution is weighted per `config.py`, normalized across whichever factors the user actually selected — so checking one factor vs. three doesn't skew the scale.
- **Dual data source (yfinance / Alpaca), switchable.** Analyst target price is yfinance-only (Alpaca's market data API doesn't offer it, at any tier).

> 中文摘要：因子引擎完全解耦，新增分析方式只要寫一個檔案+在config設權重；否決規則不受使用者勾選影響，永遠強制執行；K線型態依統計可信度分級計分，不是所有型態一視同仁；新聞情緒交給LLM評分，但用明確條件限制高分級距，減少主觀漂移；採動態加權平均，勾選一個或三個因子門檻感受一致；支援yfinance/Alpaca雙資料源切換，分析師目標價僅yfinance提供。

---

## Project structure

```
.
├── main.py                      # Flask entry point, factor toggles, demo-mode guard
├── config.py                    # API keys, demo-mode flag, per-factor weight config
├── requirements.txt
├── templates/
│   └── index.html               # Frontend UI (factor checkboxes, source switch)
└── src/
    ├── us_Api_client.py          # yfinance / Alpaca data fetching (US market)
    ├── analyzer.py                # Veto rules + weighted scoring engine
    ├── recommendation_engine.py    # Formats analyzer output into readable lines
    └── factors/                    # Independent, pluggable scoring modules
        ├── rr_factor.py
        ├── candlestick_factor.py
        ├── volume_factor.py
        ├── news_factor.py
        └── put_call_ratio_factor.py
```

A `tw_Api_client.py` (Taiwan market) is planned as a natural extension of the same client interface; `market=tw` is already reserved as a routing parameter in the frontend, not yet wired to a backend implementation.

> 中文摘要：`market=tw` 目前只在前端預留接口，後端尚未實作；未來計畫比照 `us_Api_client.py` 的介面新增 `tw_Api_client.py`，處理台股資料源。

---

## Tech stack

- **Language:** Python 3.11+
- **Web framework:** Flask / Gunicorn
- **Data sources:** yfinance, Alpaca Market Data API
- **LLM:** Groq Cloud API (llama-3.1-8b-instant)
- **Analysis:** pandas, numpy, TA-Lib

---

## Quick start

```bash
git clone https://github.com/songhua-dev/stock-analyze-system.git
cd stock-analyze-system

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_ENDPOINT=https://paper-api.alpaca.markets

GROQ_API_KEY=your_groq_api_key

DEMO_MODE=false
```

Without keys, the app falls back to demo mode automatically — Alpaca and news-sentiment features are disabled, everything else still runs on yfinance.

Run locally:

```bash
python main.py
```

Then open `http://localhost:5000`.

> 中文摘要：本機執行不用金鑰也能跑，會自動退回demo模式（停用Alpaca與新聞情緒功能，其餘功能維持正常）；有金鑰則完整解鎖。

---

## API

**Endpoint:** `GET /api/analyze`

| Parameter | Required | Description |
|---|---|---|
| `symbol` | Yes | US ticker, e.g. `PLTR`, `TSLA` |
| `market` | No | Market identifier, default `us` (`tw` reserved, not yet implemented) |
| `source` | No | `yfinance` (default) or `alpaca` |
| `factors` | No | Comma-separated factor list, e.g. `rr,news,put_call` |

```bash
curl "http://localhost:5000/api/analyze?symbol=PLTR&factors=rr,news,put_call&source=yfinance"
```

---

## Adding a new factor

Every factor module returns the same shape:

```python
{"score": float, "usable": bool, "detail": str}
```

`usable=False` means the factor couldn't be evaluated this time (missing data, API failure) — it's excluded from the weighted average rather than counted as a neutral zero. To add a new one:

1. Write a new file under `src/factors/` following this return shape.
2. Add a weight for it in `config.py`'s `FACTOR_WEIGHTS`.
3. Wire the toggle into `main.py` alongside the existing factors.

`analyzer.py` itself needs no changes — it only consumes whatever `factor_results` dict it's handed.

> 中文摘要：每個因子模組統一回傳 `{score, usable, detail}`；`usable=False`代表這次無法判讀，不計入加權平均（不是當作0分）。新增因子只要三步：寫檔案、在config設權重、main.py接上開關，`analyzer.py`本身不用改。

---

## Deployment

Deployable to Render or similar PaaS:

1. Push to GitHub.
2. Create a new Web Service on Render, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn main:app`
5. Set `DEMO_MODE=true` in Render's environment variables to enable the cloud demo guard (blocks Alpaca/LLM calls that would consume private API quota; local deployment is unrestricted).

---

## Known limitations

- Candlestick reliability tiers are indirectly sourced from a TradingView script citing Bulkowski's published win rates — not independently verified against the original publication. Treat as a reference-level approximation, not an exact figure.
- Put/Call ratio is computed from options **volume**, not open interest — both yfinance and Alpaca's free tier returned unreliable/unavailable open interest data during testing, so volume was used as a more consistently populated fallback.
- News sentiment scoring depends on an LLM call per analysis; scores are the model's constrained-category judgment, not a deterministic calculation like the other factors.
- Analyst target price is yfinance-only; Alpaca's Market Data API does not offer this at any subscription tier.

> 中文摘要：K線可信度分級數據為間接引用，未逐一核對原始出版品；Put/Call比率改用成交量而非未平倉量計算，因為兩邊免費資料源的未平倉量欄位測試下來都不可靠；新聞情緒分數是LLM在限定類別下的判斷，不像其他因子是可重現的定量計算；分析師目標價僅yfinance提供，Alpaca任何方案都沒有這項資料。

---

## License

MIT License — fork it, modify it, use it for whatever you want. If you build something interesting on top of it, I'd genuinely like to hear about it, but that's not a requirement.

> 中文摘要：MIT授權，歡迎自由引用、修改、拿去用在任何用途，沒有強制要求告知，但如果你做出有趣的東西很樂意聽聽看。