# ORBIT Milestone Weekly Tracking

*Last updated: 2025-11-10*

| Week Ending | M0: Setup | M1: Data + Gemini | M2: Calibration | M3: Multimodal | M4: Production | M5: Complete | Notes |
|-------------|-----------|-------------------|-----------------|----------------|----------------|--------------|-------|
| 2025-11-10  | 100% ✅   | 55% 🟡            | 0% 🔴          | 0% 🔴         | 0% 🔴         | 0% 🔴       | M1: prices ingestion complete (Stooq CSV → Parquet with validation) |

## M1 Deliverable Progress (as of 2025-11-10)

✅ Complete:
- `ingest:prices` (src/orbit/ingest/prices.py, tests/test_ingest_prices.py, CLI command)
  - Fetches SPY.US, VOO.US, ^SPX from Stooq
  - Writes to data/raw/prices/ and data/curated/prices/
  - 22 tests, 92% coverage
  - Handles retry/backoff, polite delays, volume normalization

⏳ In Progress:
- None currently

🔴 Remaining:
- `ingest:news` — Alpaca news ingestion
- `ingest:social` — Reddit social ingestion
- `llm_batching_gemini` — Gemini batch scoring
- Preprocess hooks (dedupe, novelty, cutoff enforcement)
- Merge LLM fields into curated tables
- `train:walkforward` and `backtest:run` CLI

## Recent Velocity

- **Week of 2025-11-03**: +15% (M1 prices ingestion completed)
- **Average velocity**: 15%/week

## Projected Completion

- **M1 (Data + Gemini)**: ~4 more weeks (assuming 15%/week)
- **M2 (Calibration)**: TBD (blocked on M1)
- **M3 (Multimodal)**: TBD (blocked on M1)
