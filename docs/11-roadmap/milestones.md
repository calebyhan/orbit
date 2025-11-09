# ORBIT — Milestones

*Last edited: 2025-11-08*

## Purpose

Define the **phased development roadmap** from M0 (data I/O skeleton) through production and beyond. Each milestone has clear deliverables and acceptance criteria. The sequence below intentionally separates a small, safe "data I/O" first milestone (what to do before any data retrieval) from the heavier work of integrating data gathering and LLM scoring.

---

## Milestone 0: Data I/O skeleton (1 week)

**Goal:** Create a minimal, well-specified input/output surface for the project so downstream code and tests can be built without retrieving live data yet. This lets developers and CI validate end-to-end I/O, schemas, and local workflows before connecting external sources.

### Deliverables

* [ ] `src/` layout and lightweight I/O utilities: `io.read_parquet(path)`, `io.write_parquet(df, path)` and a small fixture loader for test data
* [ ] Canonical `data/` and `/srv/orbit/data/` layout documented and example directories (`data/sample/news/`, `data/sample/social/`, `data/sample/prices/`) with small sample Parquet files (sanitized)
* [ ] Clear schemas for raw → curated → features (Parquet schema docs under `docs/12-schemas/` updated if needed)
* [ ] Minimal CLI entrypoints for local runs: `orbit ingest --local-sample`, `orbit features --from-sample`
* [ ] Unit tests that exercise read/write and join logic with sample data

### Acceptance Criteria

* IO utilities can read/write Parquet without losing schema metadata
* Sample data enables a full features:build run in CI (fast, <2 minutes)
* `ORBIT_DATA_DIR` can point to `/srv/orbit/data` (documented) and the code reads from that path when set
* No external API keys required to run the tests

### Exit Criteria

* `pytest` passes for I/O tests
* Documentation updated (`docs/02-architecture/workspace_layout.md`, `03-config`) to reference I/O contract

**Status:** 🟢 Not started / In planning

---

## Milestone 1: Data gathering + Gemini integration (4 weeks)

**Goal:** Implement ingestion connectors for the primary data sources and wire in Gemini LLM scoring (batch pipeline). After this milestone the pipeline will be able to produce curated Parquet outputs for prices, news, and social from live sources.

### Deliverables

* [ ] `ingest:prices` — Stooq CSV downloader → `data/raw/prices/` and `data/curated/prices/` pipeline (EOD)
* [ ] `ingest:news` — Alpaca news WS client (or REST backfill) that writes raw and curated news Parquet (cutoff discipline enforced)
* [ ] `ingest:social` — Reddit API puller with rate‑limit handling that writes raw social Parquet
* [ ] `llm_batching_gemini` — Batch scoring pipeline using `gemini-2.5-flash-lite` with multi-key rotation and raw req/resp persistence
* [ ] Preprocess hooks: dedupe, novelty (7d), and cutoff enforcement (15:30 ET)
* [ ] Merge LLM fields into curated tables (`sent_llm, stance, sarcasm, certainty`)

### Acceptance Criteria

* Each ingestion produces daily Parquet files with the documented schema
* Batch Gemini scoring runs successfully on sample and small live batches; raw request/response saved under `data/raw/gemini/`
* Backpressure/rate-limit handling and key rotation demonstrated in tests or small runs
* Logs and rejects written to `data/rejects/` on failures

### Exit Criteria

* 7 consecutive days of stable ingest runs in staging (or smoke tests passing for each connector)
* Gemini quota handling audited (no silent failures)

**Status:** 🟡 In progress

---

## Milestone 2: Calibration & Risk Controls (2 weeks)

**Goal:** Improve probability calibration, add confidence-based position sizing, and implement risk controls. (This milestone was previously numbered M3.)

### Deliverables

* [ ] **Calibration:** Platt scaling or Isotonic regression on validation set
* [ ] **Confidence sizing:** Position = f(fused_score) with thresholds (0 / 0.5 / 1.0)
* [ ] **Risk controls:**
  - Flatten on missing data (any source >1 day stale)
  - Flatten on high vol (realized vol > 95th percentile)
  - Dynamic threshold adjustment by regime
* [ ] **Monitoring:** Drift dashboard (IC, Sharpe, feature PSI)
* [ ] **Reports:** Calibration curve, reliability diagram, ECE tracking

### Acceptance Criteria

* **Calibration:** ECE < 0.05 (well-calibrated probabilities)
* **Brier score:** Improves by ≥0.01 vs uncalibrated
* **Risk controls:** Flatten triggers <5% of days (avoid overreaction)

### Exit Criteria

* All Level 2-6 gates pass (including promotion criteria)
* Model ready for "production" (daily scoring on new data)

**Status:** 🔴 Blocked (waiting for M1 completion)

---

## Milestone 3: Production Deployment (2 weeks)

**Goal:** Deploy ORBIT to run daily on live data (scoring only; no actual trading yet).

### Deliverables

* [ ] **Daily automation:** Cron job or scheduler (ingest → score → log)
* [ ] **Monitoring:** Health checks, data quality alerts, drift tracking
* [ ] **Logging:** Full audit trail (see `10-operations/logging_audit.md`)
* [ ] **Dashboards:** Live equity curve, rolling IC, feature distributions
* [ ] **Runbook:** On-call playbook for common failures (see `10-operations/failure_modes_playbook.md`)
* [ ] **Backup & recovery:** Cloud backups (data, models, logs)

### Acceptance Criteria

* **Uptime:** 98% successful daily runs over 30 days
* **Latency:** Full pipeline completes in <15 minutes

### Exit Criteria

* 30 consecutive days of successful daily scoring

**Status:** 🔴 Not Started

---

## Milestone 4: Paper Trading (4 weeks)

**Goal:** Simulate live trading (track performance as if executing trades, but no real money).

*(unchanged from previous plan — content omitted for brevity in this excerpt)*

---

## Milestone 5: Web Dashboard (2 weeks)

*(unchanged; same high-level goals as before)*

---

## Milestone 6: Live Trading (TBD)

*(unchanged; out-of-scope for v1 docs)*

---

## Milestone Tracking

**Dashboard:** `reports/milestones/status.md` (updated weekly)

**Template:**

```markdown
# ORBIT Milestone Status — 2025-11-08

| Milestone | Status | Progress | Blockers | ETA |
|-----------|--------|----------|----------|-----|
| M0: Data I/O skeleton | ⬜ Not Started | 0% | None | 2025-11-15 |
| M1: Data gathering + Gemini | 🟡 In Progress | 40% | Gemini quota testing | 2025-12-05 |
| M2: Calibration & Risk | 🔴 Blocked | 0% | Waiting for M1 | 2026-01-05 |
| M3: Deployment | 🔴 Not Started | 0% | None | 2026-01-20 |
| M4: Paper Trading | 🔴 Not Started | 0% | None | 2026-02-20 |
| M5: Web Dashboard | 🔴 Not Started | 0% | Waiting for M3 | 2026-02-25 |
| M6: Live Trading | 🔴 Not Started | 0% | Risk approval | TBD |

**Last Updated:** 2025-11-08
```

---

## Acceptance Checklist (Overall v1)

Before declaring **v1 complete** (M2 done):

* [ ] All 3 modalities (price, news, social) integrated and tested
* [ ] Ablations prove incremental value for each modality
* [ ] Regime analysis shows robustness across vol/trend/text regimes
* [ ] Calibration improves Brier score and ECE
* [ ] Risk controls tested (flatten on missing data, high vol)
* [ ] Drift monitoring deployed and alerting correctly
* [ ] Full documentation in `docs/` (orientation, specs, playbooks)
* [ ] Code coverage ≥80%
* [ ] Reproducibility verified (independent run replicates results)

---

## Related Files

* `extend_to_single_stocks.md` — Post-v1 single-name extension
* `future_data_sources.md` — Additional data sources roadmap
* `09-evaluation/acceptance_gates.md` — Quantitative promotion criteria

```
# ORBIT — Milestones

*Last edited: 2025-11-06*

## Purpose

Define the **phased development roadmap** from M0 (price-only baseline) to M3 (production-ready tri-modal system) and beyond. Each milestone has clear deliverables and acceptance criteria.

---

## Milestone 0: Price-Only Baseline (2 weeks)

**Goal:** Establish a working pipeline with **price features only** to validate infrastructure and set performance floor.

### Deliverables

* [ ] **Ingestion:** Stooq price fetcher (SPY, VOO, ^SPX)
* [ ] **Features:** Momentum (5/20/50d), reversal (1d), vol (10d), drawdown, ETF-index basis
* [ ] **Model:** Single MLP head (price features → score)
* [ ] **Training:** Rolling walk-forward on 2020-2024 data
* [ ] **Backtest:** Long/flat overnight strategy with costs
* [ ] **Reports:** IC, Sharpe, equity curve, monthly breakdown

### Acceptance Criteria

* **IC:** ≥0.005 (proves price features have signal)
* **Sharpe:** ≥0.10 (after 2 bps/side costs)
* **Coverage:** 40-70% (trading frequency)
* **Reproducibility:** Same seed → same results (±0.001 AUC)
* **Runtime:** Full backtest (5 years) completes in <30 minutes

### Exit Criteria

* All Level 0-2 acceptance gates pass (see `09-evaluation/acceptance_gates.md`)
* Equity curve does not crash (no >30% drawdown)
* Code reviewed and merged to `main`

**Status:** 🟢 **Complete** (or 🟡 **In Progress** / 🔴 **Blocked**)

---

## Milestone 1: Add News Modality (3 weeks)

**Goal:** Integrate Alpaca news WebSocket and prove that news features add incremental value over price-only.

### Deliverables

* [ ] **Ingestion:** Alpaca news WS client (persistent daemon)
* [ ] **Preprocessing:** Dedupe, time alignment (15:30 ET cutoff), source weighting
* [ ] **Features:** news_count_z, sentiment (Gemini), novelty, source_weighted_sentiment
* [ ] **Model:** News head + gated fusion (news gate based on news_count_z, novelty)
* [ ] **Ablations:** Price-only vs Price+News comparison
* [ ] **Backtest:** Long/flat with full ablations

### Acceptance Criteria

* **IC lift:** Price+News IC ≥ Price-only IC + 0.005 (overall)
* **Busy day lift:** On days with news_count_z > 1.5, IC lift ≥ +0.010
* **No harm on quiet days:** On news_count_z ≤ 0.5, IC degradation ≤ 0.002
* **Sharpe lift:** ≥ +0.10 vs price-only
* **Max DD constraint:** ≤ Price-only Max DD + 5 ppt

### Exit Criteria

* Ablation report shows clear value on busy news days
* Gate activation rate 20-30% (as designed)
* All Level 2-5 gates pass
* News WS runs stably for 7 consecutive days (no manual restarts)

**Status:** 🟡 **In Progress**

---

## Milestone 2: Add Social Modality (4 weeks)

**Goal:** Integrate Reddit API + Gemini sentiment and prove social features add incremental value.

### Deliverables

* [ ] **Ingestion:** Reddit API puller (OAuth, rate-limited)
* [ ] **Preprocessing:** Bot filtering, quality checks, dedupe
* [ ] **Sentiment:** Gemini-only pipeline (fast/light scoring pre-filter + Flash-Lite batch escalation for highest-impact posts, top ~20%)
* [ ] **Features:** post_count_z, comment_velocity, cred_weighted_sentiment, social_novelty, sarcasm_rate
* [ ] **Model:** Social head + gated fusion (social gate based on post_count_z, novelty)
* [ ] **Ablations:** Price-only vs Price+Social vs Price+News+Social (4-way)
* [ ] **Backtest:** Long/flat with regime analysis

### Acceptance Criteria

* **IC lift:** All-modalities IC ≥ Price-only IC + 0.010
* **Busy social lift:** On post_count_z > 1.5, IC lift ≥ +0.015
* **Sharpe lift:** ≥ +0.15 vs price-only (target: +0.20)
* **Regime validation:** Works in ≥2 of 3 vol regimes (low/med/high)
* **Gemini quota:** Stays within free tier limits (<1000 posts/day escalated)

### Exit Criteria

* 4-way ablation shows All > any 2-modality combo
* Social gate activates 15-25% of days (as designed)
* Reddit API rate limits handled gracefully (zero 429 crashes in 7 days)
* All Level 2-5 gates pass

**Status:** 🔴 **Blocked** (waiting for M1 completion)

---

## Milestone 3: Calibration & Risk Controls (2 weeks)

**Goal:** Improve probability calibration, add confidence-based position sizing, and implement risk controls.

### Deliverables

* [ ] **Calibration:** Platt scaling or Isotonic regression on validation set
* [ ] **Confidence sizing:** Position = f(fused_score) with thresholds (0 / 0.5 / 1.0)
* [ ] **Risk controls:**
  - Flatten on missing data (any source >1 day stale)
  - Flatten on high vol (realized vol > 95th percentile)
  - Dynamic threshold adjustment by regime
* [ ] **Monitoring:** Drift dashboard (IC, Sharpe, feature PSI)
* [ ] **Reports:** Calibration curve, reliability diagram, ECE tracking

### Acceptance Criteria

* **Calibration:** ECE < 0.05 (well-calibrated probabilities)
* **Brier score:** Improves by ≥0.01 vs uncalibrated
* **Risk controls:** Flatten triggers <5% of days (avoid overreaction)
* **Confidence sizing:** Higher-confidence trades have higher hit rate
* **Monitoring:** Drift alerts tested (simulated drift scenario)

### Exit Criteria

* All Level 2-6 gates pass (including promotion criteria)
* Model ready for "production" (daily scoring on new data)
* Full documentation complete (`docs/` tree fully populated)
* Code coverage ≥80% (unit + integration tests)

**Status:** 🔴 **Blocked** (waiting for M2 completion)

---

## Milestone 4: Production Deployment (2 weeks)

**Goal:** Deploy ORBIT to run daily on live data (scoring only; no actual trading yet).

### Deliverables

* [ ] **Daily automation:** Cron job or scheduler (ingest → score → log)
* [ ] **Monitoring:** Health checks, data quality alerts, drift tracking
* [ ] **Logging:** Full audit trail (see `10-operations/logging_audit.md`)
* [ ] **Dashboards:** Live equity curve, rolling IC, feature distributions
* [ ] **Runbook:** On-call playbook for common failures (see `10-operations/failure_modes_playbook.md`)
* [ ] **Backup & recovery:** Cloud backups (data, models, logs)

### Acceptance Criteria

* **Uptime:** 98% successful daily runs over 30 days
* **Latency:** Full pipeline completes in <15 minutes
* **Drift detection:** Alerts trigger correctly (tested with synthetic drift)
* **Recovery:** All P0/P1 failures recovered within SLA (see playbook)
* **Audit:** Can reconstruct any signal from logs + artifacts

### Exit Criteria

* 30 consecutive days of successful daily scoring
* Zero unplanned outages (>1 hour)
* On-call engineer trained and confident with playbook
* Stakeholder sign-off for paper trading

**Status:** 🔴 **Not Started**

---

## Milestone 5: Paper Trading (4 weeks)

**Goal:** Simulate live trading (track performance as if executing trades, but no real money).

### Deliverables

* [ ] **Trade simulator:** Generate signals → log "trades" → track P&L
* [ ] **Execution realism:** Model slippage, partial fills, market impact
* [ ] **Live vs backtest comparison:** Compare realized IC/Sharpe to backtest predictions
* [ ] **Drift monitoring:** Track live IC daily; alert if <0.005 for 10 days
* [ ] **Monthly review:** Performance report vs backtest expectations

### Acceptance Criteria

* **Live IC:** Within ±0.01 of backtest IC over 90 days
* **Live Sharpe:** Within ±0.15 of backtest Sharpe
* **No surprises:** No failure modes not covered in playbook
* **Stable operations:** Zero manual interventions needed in final 30 days

### Exit Criteria

* 90 days of paper trading complete
* Live performance matches backtest (no data leakage or overfitting)
* Risk committee approves real money deployment
* Legal/compliance sign-off (if applicable)

**Status:** 🔴 **Not Started**

---

## Milestone 6: Web Dashboard (2 weeks)

**Goal:** Build interactive web dashboard for real-time monitoring and historical analysis of ORBIT signals and performance.

### Deliverables

* [ ] **Frontend Framework:** React/Next.js or Streamlit dashboard
* [ ] **Live Metrics View:**
  - Current day signal strength (fused score + modality breakdown)
  - Real-time ingestion status (news/social/prices completeness)
  - Current market regime (VIX, volatility, regime classification)
  - Gate activation status (news burst, social burst indicators)
* [ ] **Performance Charts:**
  - Equity curve (cumulative returns vs SPY benchmark)
  - Rolling IC/Sharpe (30d, 90d, 1y windows)
  - Win rate and avg profit per trade
  - Drawdown visualization
* [ ] **Feature Monitoring:**
  - Feature distributions over time (PSI heatmap)
  - Z-score anomaly detection (outlier days)
  - Text data quality scores (news/social completeness)
  - Modality weight evolution (fusion gate history)
* [ ] **Ablation Comparison:**
  - Price-only vs Price+News vs All-modalities IC
  - Regime-stratified performance (Low/Normal/Elevated/Crisis)
  - Monthly breakdown table
* [ ] **Alert Dashboard:**
  - Active drift warnings
  - Data quality issues (missing/partial days)
  - Model performance degradation alerts
  - Regime transition notifications
* [ ] **Historical Drill-Down:**
  - Single-day view: features → head scores → fusion → final signal
  - Trade log with execution details
  - News/social content viewer for specific dates
* [ ] **API Endpoints:**
  - RESTful API for dashboard data (`/api/metrics`, `/api/signals`, `/api/trades`)
  - WebSocket feed for real-time updates (optional)

### Technical Stack Options

**Selected Stack: Next.js + Supabase (Serverless-First)**

**Architecture:**
- **Frontend:** Next.js 14+ (React) with App Router
  - Deployed on Vercel (serverless, automatic scaling)
  - Server Components for data fetching
  - Client Components for interactive charts
- **Backend API:** Next.js API Routes (serverless functions)
  - `/api/metrics` → Read from Parquet/S3
  - `/api/signals` → Latest model scores
  - `/api/trades` → Historical trade log
- **Authentication:** Supabase Auth
  - Email/password or magic link
  - Row-level security policies
  - JWT-based session management
- **Database (optional):** Supabase Postgres
  - Use only if Parquet reads become bottleneck
  - Cache aggregated metrics (daily IC, equity curve points)
  - Keep raw data in Parquet, use DB for dashboard queries
- **Storage:** 
  - Primary: Read Parquet files from S3/local filesystem
  - Cache: Supabase Storage or Vercel Blob for processed artifacts
- **Charting:** Recharts or Tremor (React-native, lightweight)
- **Styling:** Tailwind CSS + shadcn/ui components

**Serverless Benefits:**
- Zero DevOps: No servers to manage
- Auto-scaling: Handles traffic spikes during market hours
- Cost-effective: Pay only for compute time used
- Fast deployment: Push to GitHub → Vercel auto-deploys

**Data Flow:**
```
Parquet files (S3/local)
    ↓
Next.js API Routes (read on-demand)
    ↓
Server Components (pre-render metrics)
    ↓
Client Components (interactive charts)
```

**Authentication Flow:**
```
User → Supabase Auth → JWT token → Next.js middleware → Protected routes
```

**Future Expansion (Post-v1):**
- If performance becomes issue: Add Redis cache (Upstash serverless)
- If real-time needed: Add Supabase Realtime subscriptions
- If complex queries needed: Migrate aggregated data to Supabase Postgres

### Acceptance Criteria

* **Latency:** Dashboard loads in <3 seconds (Next.js SSR + edge caching)
* **Real-time updates:** Signal/status updates within 30 seconds of pipeline completion
* **Historical range:** Can view data back to start of backtest (2020+)
* **Mobile responsive:** Usable on tablet/phone for on-the-go monitoring
* **Uptime:** Dashboard available 99.9% (Vercel SLA)
* **Security:** 
  - Supabase Auth required (email/password or magic link)
  - Row-level security policies for multi-user (if needed)
  - API routes validate JWT tokens
  - No public access to raw data endpoints

### Implementation Notes

**Phase 1: MVP (Week 1)**
- Next.js app scaffolding with Supabase Auth
- Read Parquet files from local filesystem
- Display: Equity curve, current signal, last 30 days IC
- Deploy to Vercel

**Phase 2: Full Features (Week 2)**
- Add all metric views (ablations, regimes, feature monitoring)
- Integrate Recharts for interactive charts
- Add drill-down views (single day analysis)
- Alert dashboard integration
- Polish UI with Tailwind + shadcn/ui

**Serverless Considerations:**
- API routes have 10s timeout on Vercel Hobby (60s on Pro)
- For large Parquet reads: Pre-compute aggregations, cache results
- Consider edge functions for frequently accessed metrics
- Use Incremental Static Regeneration (ISR) for semi-static pages

### Exit Criteria

* Dashboard deployed and accessible via web browser
* All key metrics from `monitoring_dashboards.md` integrated
* Stakeholders can monitor ORBIT without reading logs
* Documented in `10-operations/web_dashboard_guide.md`

**Status:** 🔴 **Not Started** (requires M4 deployment infrastructure)

---

## Milestone 7: Live Trading (TBD)

**Goal:** Execute real trades based on ORBIT signals (if desired).

**Note:** This is **out-of-scope for v1 documentation**. If you reach this point, ORBIT has proven itself and you'll need broker integration, compliance, and likely institutional capital.

**Prerequisites:**
- M5 (paper trading) successful
- Broker API integration (Alpaca, IBKR, etc.)
- Risk management framework
- Regulatory compliance (depends on jurisdiction)

---

## Future Milestones (Post-v1)

See `11-roadmap/extend_to_single_stocks.md` and `future_data_sources.md` for:

* **M7:** Extend to single-stock universe (cross-sectional long/short)
* **M8:** Add macro features (Fed, VIX, yield curve)
* **M9:** Add filings/10-K/10-Q text analysis
* **M10:** Add options flow / short interest

---

## Milestone Tracking

**Dashboard:** `reports/milestones/status.md` (updated weekly)

**Template:**

```markdown
# ORBIT Milestone Status — 2024-11-05

| Milestone | Status | Progress | Blockers | ETA |
|-----------|--------|----------|----------|-----|
| M0: Price-Only | ✅ Complete | 100% | None | Done |
| M1: +News | 🟡 In Progress | 75% | Alpaca WS reconnect logic | 2024-11-15 |
| M2: +Social | 🔴 Blocked | 0% | Waiting for M1 | 2024-12-15 |
| M3: Calibration | 🔴 Blocked | 0% | Waiting for M2 | 2025-01-05 |
| M4: Deployment | 🔴 Not Started | 0% | None | 2025-01-20 |
| M5: Paper Trading | 🔴 Not Started | 0% | None | 2025-02-20 |
| M6: Web Dashboard | 🔴 Not Started | 0% | Waiting for M4 | 2025-02-25 |
| M7: Live Trading | 🔴 Not Started | 0% | Risk approval | TBD |

**Last Updated:** 2024-11-05T21:05:00-05:00  
**Next Review:** 2024-11-12
```

---

## Acceptance Checklist (Overall v1)

Before declaring **v1 complete** (M3 done):

* [ ] All 3 modalities (price, news, social) integrated and tested
* [ ] Ablations prove incremental value for each modality
* [ ] Regime analysis shows robustness across vol/trend/text regimes
* [ ] Calibration improves Brier score and ECE
* [ ] Risk controls tested (flatten on missing data, high vol)
* [ ] Drift monitoring deployed and alerting correctly
* [ ] Full documentation in `docs/` (orientation, specs, playbooks)
* [ ] Code coverage ≥80%
* [ ] Reproducibility verified (independent run replicates results)
* [ ] Acceptance gates (Level 0-6) all pass

---

## Related Files

* `extend_to_single_stocks.md` — Post-v1 single-name extension
* `future_data_sources.md` — Additional data sources roadmap
* `09-evaluation/acceptance_gates.md` — Quantitative promotion criteria

---
