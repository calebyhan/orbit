# ORBIT

*Last edited: 2025-11-05*

**What is ORBIT?**
ORBIT (Observational Reasoning & Behavior-Integrated Trading) is a free‑first, daily **tri‑modal** alpha engine for the S&P 500 ETF (SPY/VOO).

* **Prices:** Stooq OHLCV for `SPY.US`, `VOO.US`, and `^SPX`
* **News:** Alpaca Market Data **news WebSocket** (≤30 symbols on free tier)
* **Social:** Reddit API (r/stocks, r/investing, r/wallstreetbets) with Gemini AI sentiment scoring.

**Why index‑first?**
One symbol, fewer mapping errors, fast iteration. Text impact is **gated** so it weighs more only on news/social burst days.

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

- Export API keys (see `docs/03-config/env_keys.md`) or create a `.env` from `.env.example`:

```bash
cp .env.example .env
# Fill in keys in .env, then:
export $(cat .env | xargs)
```

5. Run the daily pipeline (example order)

Run each pipeline step once when setting up — order matters:

```bash
# ingest prices
python -m orbit.cli ingest:prices

# ingest news (Alpaca WS)
python -m orbit.cli ingest:news

# ingest social (Reddit)
python -m orbit.cli ingest:social

# build features
python -m orbit.cli features:build

# train models (heads + fusion)
python -m orbit.cli train:fit

# run a backtest
python -m orbit.cli backtest:run
```

### M0 Quickstart (No External APIs)

For rapid testing without any external API keys:

```bash
# Generate synthetic sample data
python src/orbit/utils/generate_samples.py

# Run M0 CLI commands
orbit ingest --local-sample
orbit features --from-sample

# Run unit tests
pytest tests/ -v
```

**Notes:**

- M0 sample data in `data/sample/` is version controlled and runs entirely offline
- For production use, see `docs/02-architecture/workspace_layout.md` to configure `ORBIT_DATA_DIR=/srv/orbit/data`
- The legacy pipeline commands above are placeholders for M1+


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
