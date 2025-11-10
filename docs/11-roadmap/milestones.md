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
Status: ⬜ Not started | Progress: 0% | Dependencies: none

Deliverables
- [ ] `src/` layout and lightweight I/O utilities: `io.read_parquet(path)`, `io.write_parquet(df, path)` and a small fixture loader for tests
- [ ] Canonical `data/` layout and sanitized sample Parquet files under `data/sample/{news,social,prices}/`
- [ ] Parquet schemas documented under `docs/12-schemas/`
- [ ] Minimal CLI entrypoints for local runs: `orbit ingest --local-sample`, `orbit features --from-sample`
- [ ] Unit tests exercising read/write and join logic (fast, deterministic)
- [ ] CI job: run `pytest` + `coverage` and publish report

Acceptance criteria (measurable)
- Unit tests covering I/O utilities pass in CI (CI job exits 0)
- Sample data enables `features:build` run in CI within <2 minutes
- `ORBIT_DATA_DIR` configurable and respected by code (tested by env-var driven CI job)
- No external API keys required to run CI tests

Exit criteria
- I/O unit tests pass in CI and docs updated (`docs/02-architecture/workspace_layout.md`, `docs/03-config/sample_config.yaml`) to reference the I/O contract

Risks
- Missing sanitized sample data (mitigate: create minimal synthetic samples in this milestone)

---

### M1 — Data gathering + Gemini integration
Status: 🟡 In progress | Progress: 40% | Dependencies: M0

Deliverables
- [ ] `ingest:prices` — Stooq CSV downloader -> `data/raw/prices/` and `data/curated/prices/` (EOD)
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

Deliverables
- [ ] Paper trade execution harness with simulated fills, slippage, and costs
- [ ] Performance reporting and integration tests for a short paper-run

Acceptance criteria
- Paper trading produces recorded simulated trades and metrics; tests verify reproducibility

---

### M5 — Web Dashboard
Status: ⬜ Not started | Progress: 0% | Dependencies: M3

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
