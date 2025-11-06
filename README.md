# ORBIT

*Last edited: 2025-11-05*

**What is ORBIT?**
ORBIT (Observational Reasoning & Behavior-Integrated Trading) is a free‑first, daily **tri‑modal** alpha engine for the S&P 500 ETF (SPY/VOO).

* **Prices:** Stooq OHLCV for `SPY.US`, `VOO.US`, and `^SPX`
* **News:** Alpaca Market Data **news WebSocket** (≤30 symbols on free tier)
* **Social:** Reddit API (r/stocks, r/investing, r/wallstreetbets) with VADER/FinBERT pre‑scores and optional Gemini batch escalation

**Why index‑first?**
One symbol, fewer mapping errors, fast iteration. Text impact is **gated** so it weighs more only on news/social burst days.

### Quickstart

1. **Install**: Python 3.11+, `pip install -r requirements.txt`.
2. **Config**: copy `docs/03-config/sample_config.yaml` → `orbit.yaml` and edit keys/paths.
3. **Environment**: export API keys per `docs/03-config/env_keys.md`.
4. **Run daily pipeline** (order matters):

   * `ingest:prices` → Stooq CSV → Parquet
   * `ingest:news` → Alpaca WS capture
   * `ingest:social` → Reddit pulls (+ optional Gemini batch)
   * `features:build` → daily feature row
   * `train:fit` → price/news/social heads + gated fusion (rolling walk‑forward)
   * `backtest:run` → long/flat evaluation with costs

### Design contracts (must‑follow)

* **Cutoff:** only use text published **≤ 15:30 ET** to predict the next session.
* **Point‑in‑time:** no revised data; store raw ingests.
* **Gating:** up‑weight text when `news_count_z` or `post_count_z` is high.
* **Ablations required:** Price‑only vs +News vs +Social vs All.

### Outputs

* Parquet tables in `data/` (prices/news/social/features)
* Backtest report in `reports/` per `docs/09-evaluation/dashboard_spec.md`

### Acceptance checklist (LLM/human)

* Can you list the 6 daily jobs in order?
* Did you respect the 15:30 ET cutoff and lags?
* Do ablations show text adds value on burst days?
