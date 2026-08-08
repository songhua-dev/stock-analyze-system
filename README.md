# 📈 US Stock Quantitative Analysis System

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask-green)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Render-Live%20Demo-brightgreen)](https://stock-analyze-uodo.onrender.com)

A modular, pluggable quantitative analysis tool for US (and now Taiwan) stocks. Instead of drowning in raw indicators, it combines a few independent signals — candlestick patterns, risk/reward ratio, options Put/Call sentiment, and LLM-based news sentiment — into a single plain-language recommendation.

> 中文摘要：一個模組化、可插拔的美股（現已支援台股）量化分析工具，把K線型態、風報比、選擇權籌碼面、新聞情緒這幾個獨立訊號，綜合成一句白話文的進場建議。

**Live demo:** https://stock-analyze-uodo.onrender.com
*(Cloud demo runs a deliberately restricted mode — see [Cloud demo reliability](#cloud-demo-reliability) below before judging feature completeness from the live link alone.)*

---

## Why this exists

Most retail-facing chart tools show you raw indicators and expect you to interpret them. This project does the opposite: each signal is scored independently, and the user picks which ones to combine.

> 中文摘要：多數工具丟出一堆原始指標讓使用者自己解讀，這個專案反過來——每個訊號各自算分，使用者自己選要參考哪些。

---

## Core design

- **Pluggable factor engine** — each analysis method lives in its own file under `factors/`, all returning the same `{score, usable, detail}` shape. Adding a new scoring factor means writing one file and registering a weight in `config.py`, not touching the scoring engine itself.
- **Tri-source data fallback, in priority order.** Each fetch attempts Alpaca → Finnhub → yfinance, falling through automatically on failure, rather than a hard single-source dependency. In practice, coverage differs per data type — see [Cloud demo reliability](#cloud-demo-reliability).
- **Anti-throttling measures on the yfinance leg.** Requests use a browser-impersonated session (`curl_cffi`, Chrome110 fingerprint) plus randomized jitter (0.5–1.2s) between calls, to reduce the chance of being flagged as bot traffic.
- **Shared in-memory cache across all users**, with per-data-type TTLs (real-time bars: 2 min, news: 5 min, after-market data like stock names/options: 4 hr), plus a dedicated 1-hour cache specifically for analyst target price. This cuts down redundant upstream calls under concurrent traffic — but it's pure in-process memory, not a database: it resets on every Render restart or redeploy, and wouldn't stay consistent if the app were ever scaled across multiple server instances.
- **Candlestick scoring always runs**, independent of what the user has selected — it's treated as baseline context rather than an opt-in factor.
- **Candlestick scoring is tiered by statistical reliability, not treated as one-size-fits-all.** TA-Lib detects 60+ patterns; only the ones with a documented historical win rate (Bulkowski's ranking) get scored, tiered by how reliable that pattern actually is. Everything else scores 0 rather than pretending to have equal confidence.
- **News sentiment is LLM-scored under explicit constraints, not free-form.** The prompt restricts high-magnitude scores (±4~5) to concrete categories (verified technical breakthroughs, major contract wins vs. debt exceeding revenue, product recalls); everything else is capped to a narrower ±1~3 band. This exists specifically to reduce subjective drift in LLM scoring.
- **Dynamic weighted average, not a flat mean.** Each factor's contribution is weighted per `config.py`, normalized across whichever factors the user actually selected — so checking one factor vs. three doesn't skew the scale.
- **"My Favorites" list, stored client-side.** Saved tickers live in the browser's `localStorage` — no account, no server-side database. Trade-off: favorites don't sync across devices or survive a browser data wipe, but there's nothing to authenticate and nothing for the server to store.
- **Rate limiting is demo-mode only.** A 10-second per-IP request throttle only activates when `DEMO_MODE=true` (the public Render deployment); local/full-featured deployments are unthrottled.

> 中文摘要：因子引擎完全解耦；資料抓取採三層容錯（Alpaca→Finnhub→yfinance），實際各資料類型的覆蓋率不同（詳見下方雲端穩定性段落）；yfinance那一層加了瀏覽器偽裝與隨機延遲降低被判定為機器人流量的機率；新增多使用者共享的記憶體快取（依資料類型設不同TTL），純記憶體、Render重啟或重新部署就會清空，多實例部署下也不會同步；K線型態永遠會跑，不受使用者勾選影響，視為基礎背景資訊而非可選因子；K線依統計可信度分級計分，不是所有型態一視同仁；新聞情緒交給LLM評分，但用明確條件限制高分級距，減少主觀漂移；採動態加權平均，勾選一個或三個因子門檻感受一致；「我的最愛」存在瀏覽器localStorage；10秒限流只在Demo模式啟用。

### A note on the veto layer

Earlier versions ran risk-control veto checks (RR ratio floor, support breakdown, target-price sanity) unconditionally, regardless of what the user selected — the reasoning was that these are safety floors, not opt-in analysis. **This has since changed**: RR-dependent veto checks now only execute when the user has selected the RR factor. This was a deliberate trade-off to avoid firing an analyst-target-price API call (and the rate-limit failures that came with it) when the user never asked for RR analysis in the first place. The cost is real: if a user only checks candlestick or Put/Call, the system will no longer warn them if the stock has, say, broken through support — that check is now effectively bundled into "did you ask for RR," not "is this always checked." An insider-selling veto check still exists unconditionally, but currently has no data source wired to it, so it's presently inert.

> 中文摘要：早期版本的否決規則（風報比、跌破支撐、目標價異常）不受使用者勾選影響、永遠強制執行。目前已改為：這幾條否決規則現在綁定在「使用者是否勾選RR值」這個開關上，沒勾RR就不會執行——這是為了避免在使用者根本沒要求RR分析時，還被迫呼叫一次容易觸發限流的目標價API。代價是：如果使用者只勾K線或Put/Call，系統不會再提醒「這支股票已經跌破支撐」這類風險。內部人賣股否決規則本身仍是無條件執行的設計，但目前沒有接上任何實際資料源，處於閒置狀態。

---

## Cloud demo reliability

The public Render deployment is not a fully-representative demo of what this system can do — it's bottlenecked by two free-tier constraints that don't exist when run locally:

- **Yahoo Finance appears to blanket-block Render's shared IP ranges**, independent of actual request volume from this app. Extended cache TTLs, request jitter, and cache pre-warming were all tried and made no measurable difference — even after hours of zero traffic, the very next request still comes back rate-limited. This points to an IP-reputation block at Yahoo's end, not a request-pattern issue this app can tune its way out of.
- **Finnhub's free tier doesn't include the analyst-target-price or options-chain endpoints** (confirmed via a direct API call returning `403`) — both are gated behind a paid plan. So for both of those data types, the "tri-source fallback" collapses to yfinance-only in practice, which then hits the IP block above.

**Net effect in the cloud demo:** candlestick scoring (Alpaca-backed) is reliably available; RR analysis, Put/Call ratio, and news sentiment are frequently unavailable due to the constraints above (news is additionally disabled outright in demo mode to conserve LLM quota). The app surfaces this honestly — when the target price fetch fails in demo mode, the UI tells the user directly rather than silently degrading. **None of this applies to a local run with your own API keys.**

> 中文摘要：雲端Demo版不能代表完整功能——Yahoo Finance似乎對Render的共用IP做了整段封鎖，跟實際請求量無關（延長快取、加入延遲、預熱快取都試過，沒有實質改善，即使幾小時沒人使用，下一次請求還是被擋）；Finnhub免費版不包含分析師目標價與選擇權鏈端點（直接測試回傳403確認），代表這兩項資料實際上還是只能靠yfinance，一樣撞上IP封鎖。實際結果：雲端Demo版裡K線分析（走Alpaca）穩定可用，RR值、Put/Call比率、新聞情緒經常無法使用（新聞另外在Demo模式被直接關閉以節省LLM額度）。系統會誠實告知使用者這個限制，不會悄悄降級不說。本機使用自己的API金鑰完全不受此限制影響。

---

## Project structure

```
.
├── main.py                       # Flask entry point, factor toggles, shared cache, demo-mode guard
├── config.py                     # API keys, demo-mode flag, per-factor weight config
├── requirements.txt
├── templates/
│   └── index.html                # Frontend UI (factor checkboxes, source switch, favorites)
└── src/
    ├── i18n.py                    # Centralized bilingual (EN/ZH) string dictionary
    ├── us_Api_client.py            # US market: Alpaca / Finnhub / yfinance tri-source client
    ├── tw_Api_client.py             # Taiwan market client (same interface as us_Api_client)
    ├── analyzer.py                  # Veto rules + weighted scoring engine
    ├── recommendation_engine.py      # Formats analyzer output into readable lines
    └── factors/                      # Independent, pluggable scoring modules
        ├── rr_factor.py
        ├── candlestick_factor.py
        ├── volume_factor.py
        ├── news_factor.py
        ├── put_call_ratio_factor.py
        └── entry_price_factor.py      # Suggested entry / best-value price (non-scoring, price-only output)
```

> 中文摘要：`market=tw` 已正式串接 `tw_Api_client.py`，不再只是預留接口；`i18n.py`集中管理雙語字串；`entry_price_factor.py`是非計分因子，只輸出建議進場價/買到賺到價這兩個價格數字。

---

## Tech stack

- **Language:** Python 3.11+
- **Web framework:** Flask / Gunicorn
- **Data sources:** yfinance, Alpaca Market Data API, Finnhub
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

FINNHUB_API_KEY=your_finnhub_api_key

GROQ_API_KEY=your_groq_api_key

DEMO_MODE=false
```

Without keys, the app falls back progressively — missing Alpaca/Finnhub keys just mean those fallback tiers are skipped in favor of the next one; missing Groq disables news sentiment. `DEMO_MODE=false` (the default) runs the full, unthrottled feature set.

Run locally:

```bash
python main.py
```

Then open `http://localhost:5000`.

> 中文摘要：本機執行沒有金鑰時，會依序略過對應的備援層，不會整個崩潰；缺Groq金鑰只會停用新聞情緒功能；`DEMO_MODE=false`（預設）跑完整、不受限流的功能集。

---

## API

**Endpoint:** `GET /api/analyze`

| Parameter | Required | Description |
|---|---|---|
| `symbol` | Yes | Ticker symbol, e.g. `PLTR` (US) or `2330` (TW) |
| `market` | No | `us` (default) or `tw` |
| `source` | No | Preferred data source: `alpaca`, `finnhub`, or `yfinance` — actual source used may fall through per the tri-source chain |
| `factors` | No | Comma-separated factor list, e.g. `rr,news,put_call` (candlestick always runs regardless) |
| `lang` | No | `en` (default) or `zh` — controls all returned text |

```bash
curl "http://localhost:5000/api/analyze?symbol=PLTR&market=us&factors=rr,news,put_call&source=alpaca&lang=en"
```

---

## Adding a new factor

Every scoring factor module returns the same shape:

```python
{"score": float, "usable": bool, "detail": str}
```

`usable=False` means the factor couldn't be evaluated this time (missing data, API failure) — it's excluded from the weighted average rather than counted as a neutral zero. To add a new **weighted scoring factor**:

1. Write a new file under `src/factors/` following this return shape.
2. Add a weight for it in `config.py`'s `FACTOR_WEIGHTS`.
3. Wire the toggle into `main.py` alongside the existing factors.

`analyzer.py`'s score-collection logic needs no changes for this case. However, if the new factor also needs its own **veto condition**, that still requires adding a branch inside `analyzer.py`'s `check_veto_rules()` — veto logic is not abstracted into the same pluggable shape as scoring factors. Non-scoring, informational outputs (like `entry_price_factor.py`) don't follow the `{score, usable, detail}` shape at all — they're threaded through `main.py` and `recommendation_engine.py` as a separate, explicit parameter rather than folded into `factor_results`.

> 中文摘要：一般加減分因子只要三步：寫檔案、在config設權重、main.py接開關，analyzer.py分數收集邏輯不用改。但若新因子也需要否決規則，仍要進check_veto_rules()裡加。像entry_price_factor.py這種非計分、純資訊性質的輸出，不套用score/usable格式，是用獨立參數穿過main.py傳給recommendation_engine.py，不會混進factor_results裡。

---

## Deployment

Deployable to Render or similar PaaS:

1. Push to GitHub.
2. Create a new Web Service on Render, connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn main:app`
5. Set `DEMO_MODE=true` in Render's environment variables to enable the cloud demo guard (10s per-IP throttle, news disabled). See [Cloud demo reliability](#cloud-demo-reliability) for what to expect from a shared-IP cloud host regardless of this setting.

---

## Known limitations

- Candlestick reliability tiers are indirectly sourced from a TradingView script citing Bulkowski's published win rates — not independently verified against the original publication. Treat as a reference-level approximation, not an exact figure.
- Put/Call ratio is computed from options **volume**, not open interest — both yfinance and Alpaca's free tier returned unreliable/unavailable open interest data during testing, so volume was used as a more consistently populated fallback.
- News sentiment scoring depends on an LLM call per analysis; scores are the model's constrained-category judgment, not a deterministic calculation like the other factors.
- Analyst target price and options-chain data are effectively yfinance-only despite the tri-source client design — Alpaca doesn't offer target price at any tier, and Finnhub's free tier excludes both endpoints (confirmed via direct testing).
- The veto layer's RR-dependent checks (support breakdown, RR floor, target sanity) only run when RR is a selected factor — see [A note on the veto layer](#a-note-on-the-veto-layer).
- The shared in-memory cache is ephemeral (cleared on restart/redeploy) and single-instance only.
- See [Cloud demo reliability](#cloud-demo-reliability) for the public deployment's specific data-availability constraints, which don't apply to local runs.

> 中文摘要：K線可信度分級數據為間接引用，未逐一核對原始出版品；Put/Call比率改用成交量而非未平倉量計算；新聞情緒分數是LLM在限定類別下的判斷，不是可重現的定量計算；分析師目標價與選擇權鏈實質上仍只能靠yfinance（Alpaca不提供目標價，Finnhub免費版不含這兩項端點，皆已直接測試確認）；否決規則中跟RR相關的檢查現在綁定使用者是否勾選RR；共享記憶體快取是暫時性的，重啟/重新部署會清空，且只在單一實例下有效；雲端Demo版的資料可用性限制詳見上方段落，本機執行不受影響。

---

## License

MIT License — fork it, modify it, use it for whatever you want. If you build something interesting on top of it, I'd genuinely like to hear about it, but that's not a requirement.

> 中文摘要：MIT授權，歡迎自由引用、修改、拿去用在任何用途，沒有強制要求告知，但如果你做出有趣的東西很樂意聽聽看。