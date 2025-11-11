# ORBIT

*Last edited: 2025-11-11*

**What is ORBIT?**
ORBIT (Observational Reasoning & Behavior-Integrated Trading) is a free‑first, daily **tri‑modal** alpha engine for the S&P 500 ETF (SPY/VOO).

* **Prices:** Stooq OHLCV for `SPY.US`, `VOO.US`, and `^SPX` ✅
* **News:** Alpaca Market Data **news WebSocket** (≤30 symbols on free tier) ✅
* **Social:** Reddit API (r/stocks, r/investing, r/wallstreetbets) 🚧
* **LLM Sentiment:** Gemini 2.0 Flash-Lite with multi-key rotation (up to 5 keys) ✅

**Why index‑first?**
One symbol, fewer mapping errors, fast iteration. Text impact is **gated** so it weighs more only on news/social burst days.

**Current Status:** M1 — Data gathering + Gemini integration (75% complete)

### Quickstart

Get up and running quickly — these steps assume a Unix-like shell (bash) and Python 3.11+.

1. Clone the repository and enter the folder

```bash
git clone https://github.com/calebyhan/orbit.git
cd orbit
```

2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure the project

- Copy the sample config and edit paths/keys as needed:

```bash
cp docs/03-config/sample_config.yaml orbit.yaml
# edit orbit.yaml with your editor
```

- Create a `.env` file from the template (automatically loaded by ORBIT):

```bash
cp .env.example .env
# Edit .env and fill in your API keys (see below)
```

**Note:** ORBIT automatically loads environment variables from `.env` when you run any command. You don't need to manually export them.

**Required API Keys (M1):**

```bash
# Alpaca (news WebSocket + REST API) - FREE tier available
# Sign up at: https://alpaca.markets
# Single key mode (WebSocket only):
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_API_SECRET=your_alpaca_api_secret

# Multi-key mode (for historical backfill 5x throughput):
# REST API: ~200 RPM per key, 5 keys = ~1,000 RPM combined
ALPACA_API_KEY_1=your_alpaca_key_1
ALPACA_API_SECRET_1=your_alpaca_secret_1
ALPACA_API_KEY_2=your_alpaca_key_2
ALPACA_API_SECRET_2=your_alpaca_secret_2
# ... up to _5 for maximum throughput

# Gemini API (sentiment analysis) - FREE tier: 1,000 RPD per key
# Get keys at: https://makersuite.google.com/app/apikey
# Model: gemini-2.5-flash-lite (15 RPM, 250K TPM, 1,000 RPD)
GEMINI_API_KEY_1=your_gemini_key_1

# Optional: Add up to 5 Gemini keys for higher throughput (5,000 RPD combined)
GEMINI_API_KEY_2=your_gemini_key_2
GEMINI_API_KEY_3=your_gemini_key_3
GEMINI_API_KEY_4=your_gemini_key_4
GEMINI_API_KEY_5=your_gemini_key_5

# Reddit API (coming soon in M1)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=ORBIT/1.0 by you@example.com

# Runtime configuration
ORBIT_DATA_DIR=/srv/orbit/data  # or leave blank to use ./data
ORBIT_USER_AGENT=ORBIT/1.0
ORBIT_LOG_LEVEL=INFO
```

5. Run the daily pipeline (M1 commands)

Run each pipeline step once when setting up — order matters:

```bash
# M1: Ingest prices from Stooq (one-time historical + daily updates)
orbit ingest prices

# M1: Ingest news from Alpaca WebSocket (long-running, press Ctrl+C to stop)
# This streams real-time news - run in background or separate terminal
orbit ingest news --symbols SPY VOO

# M1: Backfill historical news (for backtesting)
# Uses REST API with optional multi-key rotation for 5x throughput
orbit ingest news-backfill --start 2024-01-01 --end 2024-12-31 --symbols SPY VOO

# M1: Score sentiment with Gemini (batch processing)
# Run this after collecting news to add sentiment scores
python -m orbit.ingest.llm_gemini  # Programmatic API

# Coming in M1: Social media ingestion
# orbit ingest social

# Coming in M2+: Features, training, and backtesting
# orbit features build
# orbit train fit
# orbit backtest run
```

**Multi-key rotation example:**

```bash
# Alpaca REST API (historical backfill) automatically uses all configured keys
# ALPACA_API_KEY_1/SECRET_1 through _5
# Default: round-robin strategy, ~200 RPM per key
# With 5 keys: ~1,000 RPM combined throughput (5x faster backfill)

# Gemini automatically uses all configured keys (GEMINI_API_KEY_1 through _5)
# Model: gemini-2.5-flash-lite
# Default: round-robin strategy, 1,000 RPD per key
# With 5 keys: 5,000 requests per day combined throughput
```

### M0 Quickstart (No External APIs)

For rapid testing without any external API keys:

```bash
# Generate synthetic sample data
python src/orbit/utils/generate_samples.py

# Run M0 CLI commands (offline mode)
orbit ingest --local-sample
orbit features --from-sample

# Run unit tests
pytest tests/ -v
```

**Notes:**

- M0 sample data in `data/sample/` is version controlled and runs entirely offline
- For production use, set `ORBIT_DATA_DIR=/srv/orbit/data` in `.env`
- See `docs/02-architecture/workspace_layout.md` for data directory structure


### Design contracts (must‑follow)

* **Cutoff:** only use text published **≤ 15:30 ET** to predict the next session.
* **Point‑in‑time:** no revised data; store raw ingests.
* **Gating:** up‑weight text when `news_count_z` or `post_count_z` is high.
* **Ablations required:** Price‑only vs +News vs +Social vs All.

### Data Outputs (M1)

* **Prices:** `data/raw/prices/{symbol}.parquet` and `data/curated/prices/{symbol}.parquet`
* **News:** `data/raw/news/date=YYYY-MM-DD/news.parquet` (real-time WebSocket stream)
* **Gemini sentiment:** `data/raw/gemini/date=YYYY-MM-DD/batch_{run_id}.jsonl` (raw req/resp audit trail)
* **Features:** `data/features/features_daily.parquet` (coming in M1)
* **Backtest reports:** `reports/` per `docs/09-evaluation/dashboard_spec.md` (coming in M2+)

### Key Features (M1)

✅ **Multi-API-Key Rotation**
- **Gemini:** Supports up to 5 API keys for 5x throughput (5,000 RPD combined)
- **Alpaca REST:** Supports up to 5 API keys for 5x throughput (~1,000 RPM combined)
- Automatic failover and load balancing (round-robin or least-used strategies)
- Per-key quota tracking with Pacific timezone reset (matches Gemini's API reset schedule)
- Model: gemini-2.5-flash-lite (15 RPM, 250K TPM, 1,000 RPD per key)

✅ **Real-time News Ingestion**
- WebSocket streaming from Alpaca with automatic reconnection
- In-memory buffering with deduplication
- Graceful shutdown and audit trail

✅ **Historical News Backfill**
- REST API pagination for historical data collection
- Multi-key rotation for 5x faster backfill (~1,000 RPM with 5 keys)
- Same normalized schema as real-time ingestion
- Date range iteration with rate limiting

✅ **Sentiment Analysis Pipeline**
- Batch processing with Gemini 2.5 Flash-Lite (15 RPM, 250K TPM, 1,000 RPD)
- Structured output: sentiment [-1,1], stance (bull/bear/neutral), certainty [0,1]
- Neutral fallback on quota exhaustion or errors
- Cost-effective: FREE tier handles ~50-80 news items/day easily with single key

### Acceptance Checklist (M1)

* ✅ Can you ingest prices from Stooq without errors?
* ✅ Can you stream news from Alpaca WebSocket with deduplication?
* ✅ Can you batch score sentiment with Gemini using multi-key rotation?
* [ ] Did you respect the 15:30 ET cutoff and lags? (preprocessing in progress)
* [ ] Do ablations show text adds value on burst days? (coming in M2)
