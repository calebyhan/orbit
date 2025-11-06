
*Last edited: 2025-11-05*

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
* [ ] **Features:** news_count_z, sentiment (VADER/FinBERT), novelty, source_weighted_sentiment
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
* [ ] **Sentiment:** VADER/FinBERT pre-filter + Gemini Flash-Lite batch escalation (top ~20%)
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

## Milestone 6: Live Trading (TBD)

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

