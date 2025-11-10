 # ORBIT — Milestones

*Last edited: 2025-11-09*

## Purpose

Define a concise, actionable phased roadmap from M0 (data I/O skeleton) through production and beyond. Each milestone should have a clear owner, measurable acceptance and exit criteria, dependencies, and an ETA so the team can track progress and gate promotions.

## How to update this file

- Update `*Last edited:` at the top when making any change.
- Milestone fields should follow the template below. Keep edits minimal and focused.

## Status legend (use consistently)

- ⬜ Not started
- 🟡 In progress
- 🔴 Blocked
- ✅ Complete

## Milestone template (use for new milestones)

### Mx — Short title
Status: ⬜ Not started | Progress: 0% | Dependencies: [Mx-1]

Relevant docs / reading
- Short list of relevant docs or design specs

Deliverables
- [ ] Short, testable list of deliverables

Acceptance criteria (measurable)
- Metric or test to validate (e.g., unit tests pass; ECE < 0.05; daily Parquet files produced for 7 consecutive days)

Exit criteria (gating conditions)
- Concrete conditions to promote milestone (e.g., CI green for N days; runbook created and smoke tests pass)

Risks / Blockers
- Short list of blockers and mitigation steps

Notes / Links
- Links to related docs, issues, or design specs

---

## Milestones

### M0 — Data I/O skeleton
Status: ✅ Complete | Progress: 100% | Dependencies: none

Relevant docs / reading
- `docs/02-architecture/workspace_layout.md` — workspace layout and data paths
- `docs/03-config/sample_config.yaml` — config keys and examples (`ORBIT_DATA_DIR`)
- `docs/12-schemas/features_daily.parquet.schema.md`, `docs/12-schemas/news.parquet.schema.md`, `docs/12-schemas/prices.parquet.schema.md`, `docs/12-schemas/social.parquet.schema.md` — canonical Parquet schemas
- `docs/05-ingestion/storage_layout_parquet.md` — storage layout and conventions

Deliverables
- [x] `src/` layout and lightweight I/O utilities: `io.read_parquet(path)`, `io.write_parquet(df, path)` and a small fixture loader for tests ✅ `src/orbit/io.py` implemented
- [x] Canonical `data/` layout with: `data/sample/` (test fixtures), `data/models/production/` (latest model), `data/curated/`, `data/features/`, `data/rejects/` (small samples for tests) ✅ All directories created
- [x] Parquet schemas documented under `docs/12-schemas/` ✅ 4 schemas: prices, news, social, features_daily
- [x] Minimal CLI entrypoints for local runs: `orbit ingest --local-sample`, `orbit features --from-sample` ✅ `src/orbit/cli.py` with both commands (predict coming in M2)
- [x] Unit tests exercising read/write and join logic (fast, deterministic) ✅ `tests/test_io.py` with 28 tests covering I/O, validation, fixtures, integration
- [x] CI job: run `pytest` + `coverage` and publish report ✅ `.github/workflows/ci.yml` with test/lint/integration jobs + coverage reporting

Acceptance criteria (measurable)
- ✅ Unit tests covering I/O utilities pass in CI (CI job exits 0) — 28 tests in test_io.py
- ✅ Sample data enables `features:build` run in CI within <2 minutes — Integration test verifies with `time` command
- ✅ `ORBIT_DATA_DIR` configurable and respected by code (tested by env-var driven CI job) — Verified in integration job with ORBIT_DATA_DIR=/tmp/orbit-test-data
- ✅ No external API keys required to run CI tests — Sample data generated via generate_samples.py (no APIs)

Exit criteria
- ✅ I/O unit tests pass in CI — All tests passing
- ✅ Docs updated (`docs/02-architecture/workspace_layout.md`, `docs/03-config/sample_config.yaml`) to reference the I/O contract — Updated 2025-11-10

Risks
- ✅ Missing sanitized sample data — RESOLVED: `src/orbit/utils/generate_samples.py` creates synthetic samples

---

### M1 — Data gathering + Gemini integration
Status: 🟡 In progress | Progress: 55% | Dependencies: M0

Relevant docs / reading
- `docs/04-data-sources/alpaca_news_ws.md` — news source design and cutoffs
- `docs/04-data-sources/stooq_prices.md` — prices source specification
- `docs/04-data-sources/reddit_api.md` — social source spec and rate limits
- `docs/04-data-sources/gemini_sentiment_api.md` — LLM scoring design (Gemini)
- `docs/04-data-sources/rate_limits.md` and `docs/04-data-sources/tos_compliance.md` — quota and compliance
- `docs/05-ingestion/news_alpaca_ws_ingest.md`, `docs/05-ingestion/prices_stooq_ingest.md`, `docs/05-ingestion/social_reddit_ingest.md`, `docs/05-ingestion/llm_batching_gemini.md` — ingestion and LLM batching implementation notes
- `docs/06-preprocessing/deduplication_novelty.md`, `docs/06-preprocessing/time_alignment_cutoffs.md` — preprocess hooks and cutoff discipline

Deliverables
- [x] `ingest:prices` — Stooq CSV downloader -> `data/raw/prices/` and `data/curated/prices/` (EOD)
- [ ] `ingest:news` — Alpaca news WS client or REST backfill producing curated Parquet (cutoff enforced)
- [ ] `ingest:social` — Reddit API puller with rate-limit handling writing raw social Parquet
- [ ] `llm_batching_gemini` — Batch scoring using `gemini-2.5-flash-lite` with multi-key rotation and raw req/resp persistence under `data/raw/gemini/`
- [ ] Preprocess hooks: dedupe, novelty window=7d, cutoff enforcement (15:30 ET)
- [ ] Merge LLM fields into curated tables (`sent_llm`, `stance`, `sarcasm`, `certainty`)
- [ ] `train:walkforward` harness and `backtest:run` CLI

Acceptance criteria (measurable)
- Each ingestion produces daily Parquet outputs that validate against the published schema (automated schema check)
- Batch Gemini scoring runs on sample and small live batches; raw req/resp stored and retrievable
- Key rotation and backpressure handling demonstrated in smoke tests (simulate quota exhaustion)
- Failures produce rejects under `data/rejects/` and are logged

Exit criteria
- 7 consecutive days of stable ingest runs in staging OR automated smoke tests covering each connector pass

Risks
- External API quotas (mitigate: multi-key rotation, test with short backoff)

---

### M2 — Calibration & Risk Controls
Status: 🔴 Blocked | Progress: 0% | Dependencies: M1

Relevant docs / reading
- `docs/09-evaluation/metrics_definitions.md` — definitions for ECE, Brier, IC, Sharpe
- `docs/09-evaluation/thresholds_position_sizing.md` — position sizing guidance
- `docs/09-evaluation/acceptance_gates.md` — promotion gates and levels
- `docs/10-operations/drift_monitoring.md` — drift monitoring and PSI

Deliverables
- [ ] Implement calibration (Platt scaling or Isotonic regression) and evaluation reporting (ECE, reliability diagrams)
- [ ] Confidence-based position sizing: Position = f(fused_score) with documented thresholds
- [ ] Risk controls: flatten on missing data (any source >1 day stale), flatten on realized vol > 95th percentile, dynamic thresholds by regime
- [ ] Drift monitoring (IC, PSI) and calibration tracking dashboards

Acceptance criteria (measurable)
- ECE < 0.05 on validation set (or documented improvement vs baseline)
- Brier score improves by ≥ 0.01 vs uncalibrated baseline on validation/backtest
- Flatten triggers empirically occur on <5% trading days in historical backtest (or documented rationale)

Exit criteria
- Calibration and risk-control tests pass; promotion gates (Level 2-6) satisfied per `09-evaluation/acceptance_gates.md`

Risks
- Delays in M1 ingestion produce insufficient validation data (mitigate: use CV folds on historical data)

---

### M3 — Production Deployment
Status: ⬜ Not started | Progress: 0% | Dependencies: M2

Relevant docs / reading
- `docs/10-operations/runbook.md` — runbook and run procedures
- `docs/10-operations/monitoring_dashboards.md` — dashboard specs and alerts
- `docs/10-operations/data_quality_checks.md` — data quality tests and alerts
- `docs/10-operations/logging_audit.md` — audit logging and retention

Deliverables
- [ ] Scheduler for daily runs (ingest → score → log) with health checks
- [ ] Data-quality alerts, drift tracking, and runbook
- [ ] Backup & recovery for data, models, and logs

Acceptance criteria
- ≥98% successful daily run SLO over 30 days in staging OR equivalent automated verification
- End-to-end runtime target met (document target; current aim < 15 minutes)

---

### M4 — Paper Trading
Status: ⬜ Not started | Progress: 0% | Dependencies: M3

Relevant docs / reading
- `docs/09-evaluation/backtest_rules.md` — backtesting rules and slippage models
- `docs/09-evaluation/backtest_long_flat_spec.md` — backtest spec and scenarios
- `docs/09-evaluation/thresholds_position_sizing.md` — sizing and risk rules used in paper runs

Deliverables
- [ ] Paper trade execution harness with simulated fills, slippage, and costs
- [ ] Performance reporting and integration tests for a short paper-run

Acceptance criteria
- Paper trading produces recorded simulated trades and metrics; tests verify reproducibility

---

### M5 — Web Dashboard
Status: ⬜ Not started | Progress: 0% | Dependencies: M3

Relevant docs / reading
- `docs/09-evaluation/dashboard_spec.md` — dashboard requirements and panels
- `docs/10-operations/monitoring_dashboards.md` — monitoring and alerting integration
- `docs/reports/milestones/status.md` — weekly milestone tracking (canonical)

Deliverables
- [ ] Next.js scaffold with basic auth and pages for equity curve, backtest summaries, IC, and current signals
- [ ] API routes or precomputed aggregations for fast reads

Acceptance criteria
- Stakeholders can view key metrics without running the pipeline locally; smoke test verifies rendering

---

## Acceptance Checklist (Overall v1)

Before declaring v1 complete (M2 done):
- All 3 modalities integrated and tested
- Ablations show incremental value per modality
- Regime analysis shows robustness
- Calibration improvements (ECE/Brier) verified
- Risk controls tested
- Drift monitoring deployed
- Documentation complete and `last_edited` updated
- Code coverage >= 80%
- Reproducibility verified

---

## Related Files

- `docs/extend_to_single_stocks.md`
- `docs/future_data_sources.md`
- `docs/09-evaluation/acceptance_gates.md`
