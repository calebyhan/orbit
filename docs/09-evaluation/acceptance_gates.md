# ORBIT — Acceptance Gates

*Last edited: 2025-11-05*

## Purpose

Define the **quantitative thresholds** ("gates") that a trained model must meet before being promoted from development to production, or from index (SPY/VOO) to single-stock universe. These gates prevent overfitting and ensure statistical rigor.

---

## Philosophy

* **Conservative by default:** Better to reject a marginally good model than deploy a lucky outlier
* **Multi-metric:** No single metric; require improvement across IC, risk-adjusted return, and stability
* **Regime-aware:** Must work across multiple market conditions
* **Ablation-driven:** Text modalities must add value over price-only baseline

---

## Gate Hierarchy

### Level 0: Data Quality (Pre-Training)

Must pass **before** training begins:

* [ ] **Ingestion completeness:** ≥95% of expected trading days have price/news/social data
* [ ] **Schema validity:** All Parquet files match `12-schemas/*.md` specs
* [ ] **Freshness:** Most recent data ≤2 trading days old (for live deploy)
* [ ] **Outlier check:** No single-day price moves >20% (data error flag)
* [ ] **Feature coverage:** ≤5% NaN in engineered features (after imputation)

**Verdict:** BLOCK training if any check fails. Fix data issues first.

---

### Level 1: Model Convergence (Training)

Must pass **during** training:

* [ ] **Loss convergence:** Training loss decreases for ≥10 epochs before early stop
* [ ] **Validation stability:** Val loss does not oscillate >20% across final 5 epochs
* [ ] **No extreme weights:** All head weights have L2 norm <10
* [ ] **Gradient health:** No NaN or Inf gradients during backprop
* [ ] **Reproducibility:** Re-running with same seed produces same validation AUC (±0.001)

**Verdict:** BLOCK promotion if convergence is unstable. Re-train with stronger regularization.

---

### Level 2: Out-of-Sample Performance (Backtest)

Must pass on **held-out test set** (or walk-forward OOS concatenated):

#### A) Information Coefficient (IC)

* **Minimum:** IC ≥ 0.010 (Spearman, daily)
* **Target:** IC ≥ 0.020
* **Excellent:** IC ≥ 0.030

**Rationale:** IC < 0.01 is too small for index prediction; likely noise.

---

#### B) AUC (Classification)

* **Minimum:** AUC ≥ 0.525
* **Target:** AUC ≥ 0.545
* **Excellent:** AUC ≥ 0.570

**Rationale:** AUC < 0.525 is barely better than random.

---

#### C) Sharpe Ratio (After Costs)

* **Minimum:** Sharpe ≥ 0.30 (annualized, with realistic costs)
* **Target:** Sharpe ≥ 0.50
* **Excellent:** Sharpe ≥ 0.70

**Rationale:** Sharpe < 0.3 is too low for deployment; opportunity cost vs buy-and-hold.

---

#### D) Max Drawdown

* **Acceptable:** Max DD ≤ -25%
* **Preferred:** Max DD ≤ -15%
* **Excellent:** Max DD ≤ -10%

**Rationale:** Deeper drawdowns are psychologically and financially costly.

---

#### E) Hit Rate (In-Trade)

* **Minimum:** Hit rate ≥ 52% (when position = 1)
* **Target:** Hit rate ≥ 54%
* **Excellent:** Hit rate ≥ 56%

**Rationale:** <52% suggests model is not better than a coin flip after costs.

---

#### F) Coverage

* **Minimum:** Coverage ≥ 30% (trade ≥30% of days)
* **Acceptable:** Coverage 40-70%
* **Too high:** Coverage >80% suggests overfitting (trading on noise)

**Rationale:** Too low coverage = underutilized model; too high = likely overfit.

---

### Level 3: Stability Across Time

Must pass on **rolling windows** or **monthly slices**:

#### A) Monthly IC Consistency

* **Requirement:** IC > 0 in ≥60% of OOS months
* **Target:** IC > 0 in ≥70% of OOS months
* **Excellent:** IC > 0 in ≥80% of OOS months

**Rationale:** Stable predictive power is more valuable than a few lucky months.

---

#### B) Rolling Sharpe Stability

* **Requirement:** Median rolling 60d Sharpe ≥ 0.25
* **Target:** 25th percentile rolling 60d Sharpe ≥ 0.15
* **No blow-ups:** No rolling 60d Sharpe < -0.5 (catastrophic failure)

**Rationale:** Consistent risk-adjusted returns > occasional spikes.

---

#### C) Drawdown Recovery

* **Requirement:** Largest drawdown recovers to new high within 120 trading days
* **Target:** Recovers within 60 trading days
* **Red flag:** No recovery after 180 days (model may be broken)

**Rationale:** Prolonged drawdowns signal regime shift or model failure.

---

### Level 4: Regime Robustness

Must pass on **regime slices** (see `regime_analysis.md`):

#### A) Volatility Regimes

* **Requirement:** IC ≥ 0.005 in **all three** vol terciles (Low, Med, High)
* **Target:** IC > 0.010 in Low and Med vol; IC > 0.005 in High vol
* **Red flag:** Negative IC in any regime (suggests overfitting)

**Rationale:** Model should work (or at least not fail) across vol regimes.

---

#### B) Text Intensity Regimes

* **Requirement:** On **busy text days** (news_count_z > 1.5 OR post_count_z > 1.5):
  - All-modalities IC ≥ Price-only IC + 0.01
* **Target:** IC lift ≥ +0.02 on busy days
* **Red flag:** Text hurts IC on busy days (gates broken)

**Rationale:** Text should add value when news/social is active.

---

#### C) Trend Regimes

* **Requirement:** Sharpe ≥ 0.15 in **both** bull and bear markets
* **Target:** Sharpe > 0 in all three (bull, neutral, bear)
* **Excellent:** Works equally well in all regimes

**Rationale:** Regime-agnostic models are more robust.

---

### Level 5: Ablation Validation

Must pass **ablation experiments** (see `ablations_checklist.md`):

#### A) Price-Only Baseline

* **Requirement:** Price-only IC ≥ 0.005 (proves price features work)
* **Target:** Price-only Sharpe ≥ 0.15

**Rationale:** Weak baseline suggests feature engineering is broken.

---

#### B) Text Modality Lift

* **Requirement:** All-modalities IC ≥ Price-only IC + 0.005
* **Target:** All-modalities IC ≥ Price-only IC + 0.010
* **Excellent:** IC lift ≥ +0.020

**Rationale:** Text must add incremental value to justify complexity.

---

#### C) Max Drawdown Constraint

* **Requirement:** All-modalities Max DD ≤ Price-only Max DD + 5 ppt
* **Target:** All-modalities Max DD ≤ Price-only Max DD (no worse)

**Rationale:** Text should not increase risk.

---

### Level 6: Promotion to Single Stocks

**Additional gates** before extending from SPY/VOO to cross-sectional universe:

* [ ] **Index v1 results:** All Level 2-5 gates passed on SPY/VOO
* [ ] **1+ year OOS:** ≥252 days of held-out test data
* [ ] **Publication ready:** Results documented in `reports/` with full transparency
* [ ] **Reproducibility:** Independent run by second person replicates results (±5% on Sharpe)
* [ ] **Code review:** All ingestion, preprocessing, feature, and modeling code peer-reviewed
* [ ] **No red flags:** No unresolved data quality issues, no suspected leakage

**Rationale:** Single-stock models are more complex and costly; index v1 is the proving ground.

---

## Summary Table: Minimum Gates for Promotion

| Gate | Minimum Threshold | Notes |
|------|-------------------|-------|
| **OOS IC** | ≥ 0.010 | Spearman, daily |
| **OOS AUC** | ≥ 0.525 | Classification only |
| **OOS Sharpe** | ≥ 0.30 | After costs |
| **Max Drawdown** | ≤ -25% | Absolute worst case |
| **Hit Rate** | ≥ 52% | When in trade |
| **Coverage** | 30-80% | Not too low, not too high |
| **Monthly IC > 0** | ≥ 60% of months | Stability check |
| **IC in all vol regimes** | ≥ 0.005 | No negative regimes |
| **Text IC lift (busy days)** | ≥ +0.010 | vs price-only |
| **Ablation: Text doesn't hurt** | Max DD lift ≤ +5 ppt | Risk control |

**Verdict:**  
- **PASS:** Promote to production (or next phase)  
- **CONDITIONAL PASS:** Deploy with monitoring; flag for review in 30 days  
- **FAIL:** Do not deploy; diagnose and re-train

---

## Gate Evaluation Process

### Step 1: Run Full Backtest + Ablations

```bash
python -m orbit.train --config orbit.yaml --mode full
python -m orbit.evaluate.backtest --run_id <run_id>
python -m orbit.evaluate.ablations --run_id <run_id>
python -m orbit.evaluate.regimes --run_id <run_id>
```

### Step 2: Generate Gate Report

```bash
python -m orbit.evaluate.gates --run_id <run_id>
```

**Output:** `reports/gates/<run_id>/gate_report.md`

**Template:**

```markdown
# Gate Evaluation Report

**Run ID:** <run_id>  
**Date:** <timestamp>  
**Evaluator:** <name/LLM>

## Level 0: Data Quality
- [x] Ingestion completeness: 98.2% ✓
- [x] Schema validity: All pass ✓
- [x] Freshness: Data current to T-1 ✓
- [x] Outlier check: No errors ✓
- [x] Feature coverage: 1.8% NaN (acceptable) ✓

**Verdict:** PASS

## Level 2: OOS Performance
- [x] IC: 0.023 (≥ 0.010) ✓
- [x] AUC: 0.558 (≥ 0.525) ✓
- [x] Sharpe: 0.42 (≥ 0.30) ✓
- [x] Max DD: -15.1% (≤ -25%) ✓
- [x] Hit Rate: 54.2% (≥ 52%) ✓
- [x] Coverage: 64.0% (30-80%) ✓

**Verdict:** PASS (Target level met)

## Level 3: Stability
- [x] Monthly IC > 0: 68% of months (≥ 60%) ✓
- [x] Median rolling Sharpe: 0.38 (≥ 0.25) ✓
- [x] Drawdown recovery: 45 days (≤ 120) ✓

**Verdict:** PASS

## Level 4: Regime Robustness
- [x] IC in Low Vol: 0.028 ✓
- [x] IC in Med Vol: 0.019 ✓
- [x] IC in High Vol: 0.011 ✓
- [x] Text IC lift (busy days): +0.026 (≥ +0.010) ✓

**Verdict:** PASS

## Level 5: Ablations
- [x] Price-only IC: 0.012 (≥ 0.005) ✓
- [x] Text IC lift: +0.011 (≥ +0.005) ✓
- [x] Max DD delta: -3.0 ppt (≤ +5 ppt) ✓

**Verdict:** PASS

## Overall Verdict

**✓ PASS** — All gates met. Model approved for production deployment.

**Confidence:** High  
**Recommendation:** Deploy to live scoring for SPY/VOO; monitor for 30 days before single-stock extension.

**Signed:** Claude (LLM Operator)  
**Date:** 2025-11-05T20:35:00-05:00
```

### Step 3: Human Review (Required)

* Review gate report
* Spot-check 5-10 random days (features → score → trade → return)
* Verify no data leakage (timestamps, publish lags)
* Sign off or request changes

---

## Failure Examples

### Example 1: Low IC (FAIL)

```
OOS IC: 0.007 (< 0.010)
Verdict: FAIL — IC too low; likely noise.
Action: Re-engineer features; check for leakage; extend training data.
```

---

### Example 2: Unstable Across Regimes (FAIL)

```
IC in Low Vol: 0.035 ✓
IC in Med Vol: 0.008 ✓
IC in High Vol: -0.012 ✗ (negative!)

Verdict: FAIL — Model breaks in high vol.
Action: Add vol-dependent gates; flatten when vol > 90th percentile.
```

---

### Example 3: Text Doesn't Help (CONDITIONAL PASS)

```
Price-only IC: 0.015
All-modalities IC: 0.016 (+0.001, < +0.005 target)

Verdict: CONDITIONAL PASS — Text barely helps.
Action: Deploy price-only for now; revisit text after improving sentiment scorer.
```

---

### Example 4: Max DD Too Deep (FAIL)

```
Max Drawdown: -28% (> -25% limit)
Verdict: FAIL — Unacceptable risk.
Action: Add risk controls (see risk_controls.md); re-test with tighter stops.
```

---

## Logging & Audit Trail

Every gate evaluation must be:

* **Logged** to `reports/gates/<run_id>/gate_log.json` (machine-readable)
* **Stored** in version control (Git commit with gate report)
* **Signed** by human reviewer (name + date in report)

**Audit trail ensures:**
- No cherry-picking of runs
- Transparency for future reviews
- Compliance with internal policies

---

## Related Files

* `metrics_definitions.md` — Metric calculation details
* `backtest_long_flat_spec.md` — Backtest execution
* `ablations_checklist.md` — Ablation experiments
* `regime_analysis.md` — Regime-specific checks
* `risk_controls.md` — Risk management rules

---

