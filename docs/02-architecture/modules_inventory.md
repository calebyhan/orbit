# ORBIT — Modules Inventory

*Last edited: 2025-11-16*

A reference table for every runnable module: purpose, inputs, outputs, dependencies, and acceptance checks.

## M1 Modules (Implemented ✅)

| Module (CLI) | Purpose | Inputs | Outputs | Depends on | Acceptance checks |
| ------------ | ------- | ------ | ------- | ---------- | ----------------- |
| `orbit ingest prices` | Fetch Stooq CSV → Parquet | Stooq endpoints | `data/raw/prices/<symbol>.parquet` | internet | Full history per symbol; schema valid; prices > 0 |
| `orbit ingest news` | Stream Alpaca News WebSocket | Alpaca WS API key/secret | `data/raw/news/date=YYYY-MM-DD/news.parquet` | Alpaca connection | WS connects; dedup by `msg_id`; timestamps valid |
| `orbit ingest news-backfill` | Fetch historical news (Alpaca REST) | Alpaca REST API keys (1-5) | `data/raw/news/date=YYYY-MM-DD/news_backfill.parquet` | Multi-key rotation | Date range filled; dedup by `msg_id`; rate limits respected |
| `orbit ingest social-backfill` | Fetch historical Reddit (Arctic API) | Arctic Shift API (no auth) | `data/raw/social/date=YYYY-MM-DD/social.parquet` | Rate limiter (3.5 req/s) | 10-year backfill ~2.6 hrs; subreddit filtering; SHA-256 hashing |
| `orbit preprocess` | Time align, dedupe, novelty | `data/raw/{news,social}/` | `data/curated/{news,social}/date=YYYY-MM-DD/` | Preprocessing pipeline | 15:30 ET cutoff enforced; dedup Hamming ≤3; novelty [0,1] |

## M2+ Modules (Planned 🔲)

| Module (CLI) | Purpose | Status | Notes |
| ------------ | ------- | ------ | ----- |
| `orbit llm score` | Batch Gemini sentiment | Library-only (M1) | `llm_gemini.py` exists but no CLI integration yet |
| `orbit features build` | Assemble daily features | Not started | Depends on curated data + price features |
| `orbit train heads` | Fit price/news/social heads | Not started | Depends on features |
| `orbit train fusion` | Fit gated ensemble | Not started | Depends on trained heads |
| `orbit score daily` | Generate Score_t predictions | Not started | Depends on trained models |
| `orbit backtest run` | Evaluate long/flat strategy | Not started | Depends on scores + labels |
| `orbit eval ablations` | Price vs +News vs +Social | Not started | Depends on backtest |
| `orbit eval regimes` | Slice by vol/news/social | Not started | Depends on backtest |
| `orbit ops checks` | Data quality & freshness | Not started | Validation utilities exist but no CLI |

---

## M1 Implementation Details

### Ingestion

**Prices** (`orbit ingest prices`):
- **Source**: Stooq CSV API (free, no auth)
- **Symbols**: SPY.US, VOO.US, ^SPX (configurable via `--symbols`)
- **Partitioning**: Symbol-level (one file per symbol, full history)
- **Update strategy**: Overwrite entire file on each run
- **Runtime**: ~10-30 seconds for 3 symbols (10-year history)

**News** (`orbit ingest news` + `news-backfill`):
- **Source**: Alpaca News API (WebSocket + REST)
- **Authentication**: Requires `ALPACA_API_KEY` and `ALPACA_API_SECRET` in `.env`
- **Multi-key support**: Backfill uses 1-5 keys for parallel ingestion
- **Partitioning**: Date-level (`date=YYYY-MM-DD`)
- **Deduplication**: By `msg_id` within partition
- **Runtime**:
  - WebSocket: Continuous streaming during market hours
  - Backfill: ~1-2 hours (1 key), ~15-20 minutes (5 keys) for 10 years

**Social** (`orbit ingest social-backfill`):
- **Source**: Arctic Shift API (unofficial Reddit archive, no auth)
- **Rate limit**: 3.5 req/s (80% of observed max)
- **Subreddits**: wallstreetbets, stocks, investing, stockmarket
- **Privacy**: SHA-256 hashing for author IDs and content IDs
- **Partitioning**: Date-level (`date=YYYY-MM-DD`)
- **Runtime**: ~2.6 hours for 10-year backfill

### Preprocessing

**Preprocessing Pipeline** (`orbit preprocess`):
- **Cutoff enforcement**: (T-1 15:30, T 15:30] ET window with timezone awareness
- **Safety lag**: 30-minute buffer for training (configurable)
- **Deduplication**: Simhash (3-gram) with Hamming distance ≤3
- **Clustering**: Connected components with earliest item as leader
- **Novelty scoring**: 7-day reference window (default), 1 - max_similarity
- **Output fields**: `is_dupe`, `cluster_id`, `novelty`, `window_start_et`, `window_end_et`
- **Runtime**: ~5-30 seconds per day (depends on volume)

### LLM Scoring (Library-only)

**Gemini Sentiment** (`llm_gemini.py`):
- **Model**: Gemini 2.5 Flash-Lite
- **API**: Google Generative AI (requires `GEMINI_API_KEY_1` in `.env`)
- **Multi-key rotation**: Up to 5 keys for higher throughput
- **Batch size**: 200 items/batch (configurable)
- **Output fields**: `sent_llm` [-1,1], `stance` (bull/bear/neutral), `sarcasm`, `certainty`, `toxicity`
- **Usage**: Python API only (no CLI command in M1)
- **Runtime**: ~1-2 API calls/day for typical news/social volume

---

## Configuration

**M1 uses `.env` files only** (no `orbit.yaml` yet):
- API keys and secrets in `.env` (loaded automatically via python-dotenv)
- Data directory: `ORBIT_DATA_DIR` (defaults to `./data`)
- All configuration via environment variables
- See [docs/03-config/env_keys.md](../03-config/env_keys.md) for setup

**M2+ will add `orbit.yaml`** for:
- Feature engineering parameters
- Model hyperparameters
- Training configuration
- Evaluation thresholds
- See [docs/03-config/sample_config.yaml](../03-config/sample_config.yaml) (planned)

---

## Acceptance Checklist

**M1 Completion Criteria** (✅ All met):
- [x] Prices ingestion (Stooq) with symbol-level partitioning
- [x] News ingestion (Alpaca WS + REST backfill) with multi-key rotation
- [x] Social ingestion (Arctic API) with rate limiting and privacy hashing
- [x] Preprocessing pipeline (cutoff, dedupe, novelty) with timezone discipline
- [x] LLM sentiment library (Gemini) with batch scoring
- [x] Comprehensive tests (104 passing: prices, news, social, preprocessing)
- [x] CLI commands for all M1 operations
- [x] Documentation aligned with implementation

**M2 Planned Deliverables**:
- [ ] Feature engineering module with rolling windows
- [ ] Model training (price/news/social heads)
- [ ] Fusion ensemble with gating
- [ ] Daily scoring pipeline
- [ ] Backtest evaluation framework
- [ ] Ablation and regime analysis
- [ ] Data quality monitoring

---

## Related Files

* [docs/INSTRUCTIONS/02_cli_commands.md](../INSTRUCTIONS/02_cli_commands.md) — CLI usage guide
* [docs/11-roadmap/milestones.md](../11-roadmap/milestones.md) — Milestone tracking
* [docs/02-architecture/system_diagram.md](system_diagram.md) — Architecture overview
