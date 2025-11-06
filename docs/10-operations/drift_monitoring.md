
*Last edited: 2025-11-06*

## Purpose

Detect **model performance degradation** and **feature distribution shifts** over time. Drift monitoring alerts us when the model's assumptions break down, triggering retraining or gating adjustments.

---

## Types of Drift

### 1. Concept Drift

**Definition:** Relationship between features and labels changes over time  
**Example:** News sentiment → returns correlation weakens after market regime shift

**Detection:** Track IC and AUC over rolling windows

---

### 2. Data Drift (Covariate Shift)

**Definition:** Feature distributions change over time  
**Example:** Average `news_count` increases 2× after a new data source is added

**Detection:** Track feature distributions (mean, std, quantiles) and compare to training

---

### 3. Label Drift

**Definition:** Distribution of labels (returns) changes over time  
**Example:** Market volatility regime shifts from low to high

**Detection:** Track return distribution (mean, vol, skewness) over rolling windows

---

## Monitoring Frequency

Frequency adapts based on **market regime** (see `regime_transition_protocol.md`):

| Regime       | IC Check Frequency | Feature Drift Check | Alert Threshold (10d MA IC) |
| ------------ | ------------------ | ------------------- | --------------------------- |
| **Low Vol**  | Weekly (Mon AM)    | Weekly              | < 0.005                     |
| **Normal**   | 2×/week (Mon/Thu)  | Every 3 days        | < 0.005                     |
| **Elevated** | Daily (9:35 AM)    | Daily               | < 0.000 (neutral)           |
| **Crisis**   | Hourly             | Continuous          | < −0.05 (negative)          |

**Additional Metrics:**

| Metric                  | Check Frequency | Alert Threshold        |
| ----------------------- | --------------- | ---------------------- |
| Rolling Sharpe          | Weekly          | 60-day Sharpe < 0.15   |
| Feature PSI             | Per regime      | Any feature PSI > 0.25 |
| Prediction calibration  | Monthly         | Brier score ↑ >10%     |
| Label distribution      | Monthly         | Vol ↑ >50% vs training |

---

## 1. Performance Drift Monitoring

### Daily IC Tracking

**Metric:** Spearman IC between `fused_score_t` and `label_{t+1}`

**Compute:**
```python
# After each day's realized return is known
ic_daily = spearmanr(score[t], label[t+1])
# Append to logs/drift/ic_daily.parquet
```

**Alert rules:**
- **WARN:** 10-day moving average IC < 0.005 (near zero)
- **CRITICAL:** 10-day MA IC < -0.01 (negative predictive power)

**Action:**
- WARN: Review recent market regime; check if text gates are activating appropriately
- CRITICAL: **Flatten positions**; investigate data quality; consider emergency retrain

---

### Rolling Sharpe Tracking

**Metric:** 60-day rolling Sharpe of strategy returns

**Compute:**
```python
sharpe_60d = (ret_net[-60:].mean() / ret_net[-60:].std()) * sqrt(252)
```

**Alert rules:**
- **WARN:** Sharpe < 0.20 (degraded but not broken)
- **CRITICAL:** Sharpe < 0.0 (losing money risk-adjusted)

**Action:**
- WARN: Schedule retrain in next window
- CRITICAL: **Flatten positions**; rollback to previous model if available

---

### Hit Rate Tracking

**Metric:** % winning trades (when position = 1)

**Compute:**
```python
hit_rate_30d = (ret_net[-30:][position[-30:] == 1] > 0).mean()
```

**Alert rules:**
- **WARN:** Hit rate < 51% over 30 days
- **CRITICAL:** Hit rate < 48% over 30 days

**Action:**
- WARN: Review threshold settings
- CRITICAL: Raise threshold or flatten

---

## 2. Feature Drift Monitoring (PSI)

### Population Stability Index (PSI)

**Purpose:** Measure how much a feature's distribution has shifted vs training baseline

**Formula:**
$$
\text{PSI} = \sum_{i=1}^{10} (P_i - Q_i) \times \ln\left(\frac{P_i}{Q_i}\right)
$$

where:
- $P_i$ = % of live data in bin $i$
- $Q_i$ = % of training data in bin $i$
- Bins = deciles of training distribution

**Interpretation:**
- PSI < 0.10: **No significant shift**
- $0.10 \leq \text{PSI} < 0.25$: **Moderate shift** (monitor)
- $\text{PSI} \geq 0.25$: **Large shift** (investigate + consider retrain)

---

### Weekly Feature PSI Check

**Compute:**
```bash
python -m orbit.ops.drift_check --type feature_psi --window last_7d
# Compares last 7 days vs training baseline
# Outputs: reports/drift/YYYY-WW/feature_psi.parquet
```

**Alert rules:**
- **WARN:** Any feature PSI > 0.25
- **CRITICAL:** ≥3 features with PSI > 0.25

**Action:**
- WARN: Log for monthly review
- CRITICAL: Investigate root cause; consider feature recalibration or retrain

---

### Feature Distribution Plots

**Weekly report:**

Generate histograms comparing:
- Training baseline (blue)
- Last 7 days (red overlay)

**Features to monitor:**
- `news_count_z` (text intensity)
- `post_count_z` (social buzz)
- `momentum_20d` (price trend)
- `rv_10d` (volatility)

**Save to:** `reports/drift/YYYY-WW/feature_distributions.pdf`

---

## 3. Label Drift Monitoring

### Return Distribution Tracking

**Metrics:**
- Mean daily return
- Volatility (std)
- Skewness
- 5th / 95th percentiles

**Compute monthly:**
```python
ret_stats = {
    'mean': label.mean(),
    'std': label.std(),
    'skew': label.skew(),
    'p05': label.quantile(0.05),
    'p95': label.quantile(0.95)
}
```

**Alert rules:**
- **WARN:** Vol ↑ >50% vs training baseline
- **WARN:** Mean return changes sign (bull → bear or vice versa)

**Action:**
- Regime shift detected; review regime-specific gates
- Consider training separate models per regime

---

## 4. Prediction Calibration Drift

### Calibration Error (Classification)

**Metric:** Expected Calibration Error (ECE)

**Formula:**
$$
\text{ECE} = \sum_{m=1}^{M} \frac{n_m}{N} \left| \text{acc}(m) - \text{conf}(m) \right|
$$

where:
- $M$ = number of bins (e.g., 10)
- $n_m$ = samples in bin $m$
- $\text{acc}(m)$ = accuracy in bin $m$
- $\text{conf}(m)$ = avg confidence in bin $m$

**Compute monthly:**
```bash
python -m orbit.ops.drift_check --type calibration --month last
```

**Alert rules:**
- **WARN:** ECE ↑ >10% vs training baseline
- **CRITICAL:** ECE ↑ >25%

**Action:**
- WARN: Schedule recalibration (Platt/Isotonic)
- CRITICAL: Recalibrate immediately or flatten

---

### Brier Score Tracking

**Metric:** Mean squared error of predicted probabilities

**Compute:**
```python
brier = ((prob_pred - label_binary)**2).mean()
```

**Alert rules:**
- **WARN:** Brier score ↑ >0.02 vs training baseline

**Action:**
- Recalibrate probabilities

---

## 5. Gate Drift Monitoring

### Gate Activation Rate

**Metric:** % days where `news_gate > 0.5` or `social_gate > 0.5`

**Baseline (training):** ~20-30% for news, ~15-25% for social

**Compute weekly:**
```python
news_gate_rate = (news_gate > 0.5).mean()
social_gate_rate = (social_gate > 0.5).mean()
```

**Alert rules:**
- **WARN:** Activation rate shifts >10 ppt vs training (e.g., 25% → 40%)

**Action:**
- Investigate: Is text genuinely busier, or is feature drift inflating z-scores?
- May need to re-standardize features with updated rolling windows

---

## 6. Automated Drift Report

### Weekly Drift Summary

**Command:**
```bash
python -m orbit.ops.drift_report --week last
# Generates: reports/drift/YYYY-WW/drift_summary.md
```

**Contents:**

```markdown
# Drift Report — Week 44, 2024

**Period:** 2024-10-28 to 2024-11-03  
**Days:** 5 trading days

## Performance Drift

| Metric | Last 7d | Last 30d | Training Baseline | Status |
|--------|---------|----------|-------------------|--------|
| IC (mean) | 0.018 | 0.021 | 0.023 | ✓ OK |
| Sharpe (60d) | 0.41 | 0.44 | 0.42 | ✓ OK |
| Hit Rate (30d) | 53.2% | 54.1% | 54.5% | ✓ OK |

## Feature Drift (PSI)

| Feature | PSI | Status | Action |
|---------|-----|--------|--------|
| news_count_z | 0.08 | ✓ OK | None |
| post_count_z | 0.32 | ⚠ WARN | Investigate |
| momentum_20d | 0.12 | ✓ OK | Monitor |
| rv_10d | 0.18 | ✓ OK | None |

**Flagged:** `post_count_z` PSI = 0.32 (>0.25 threshold)  
**Diagnosis:** Reddit activity spiked this week (election news?); not a data error.  
**Action:** Monitor for 2 more weeks; if persists, retrain with updated baseline.

## Label Drift

| Metric | Last 30d | Training Baseline | Change |
|--------|----------|-------------------|--------|
| Mean return | 0.08% | 0.06% | +0.02% |
| Volatility | 1.2% | 1.1% | +9% |
| Skewness | -0.3 | -0.1 | More negative |

**Status:** ✓ OK (minor vol increase, within normal range)

## Calibration

| Metric | Last 30d | Training Baseline | Change |
|--------|----------|-------------------|--------|
| Brier Score | 0.244 | 0.242 | +0.002 |
| ECE | 0.032 | 0.028 | +0.004 |

**Status:** ✓ OK (slight degradation, not alarming)

## Overall Verdict

**✓ PASS** — No critical drift detected. Continue monitoring `post_count_z` PSI.

**Next Review:** 2024-11-10
```

---

## Retrain Triggers

**Automatic retrain** if any of:

1. **IC drift:** 30-day MA IC < 0.005 for 2 consecutive weeks
2. **Sharpe drift:** 60-day Sharpe < 0.15 for 2 consecutive weeks
3. **Feature drift:** ≥3 features with PSI > 0.25 for 2 consecutive weeks
4. **Calibration drift:** ECE ↑ >25% vs training

**Manual review retrain** if:
- Label distribution shifts significantly (vol doubles)
- Market regime change (e.g., VIX >35 for extended period)
- Major data source change (e.g., Alpaca API update)

---

## Retrain Procedure

**When triggered:**

```bash
# 1. Snapshot current model performance
python -m orbit.ops.snapshot_model --run-id <current_run_id>

# 2. Retrain with updated data (extended walk-forward window)
python -m orbit.train --config orbit.yaml --mode retrain --start-date <new_start>

# 3. Compare new vs old model on overlapping OOS period
python -m orbit.evaluate.compare --old-run-id <old> --new-run-id <new>

# 4. If new model passes acceptance gates, promote
python -m orbit.ops.promote_model --run-id <new> --environment production

# 5. Monitor closely for 30 days
python -m orbit.ops.enable_enhanced_monitoring --run-id <new> --duration 30d
```

---

## Dashboard

**Live drift dashboard:** `reports/drift/dashboard.html`

**Updated:** Daily after scoring

**Panels:**
1. **Rolling IC** (line chart, 10-day MA)
2. **Rolling Sharpe** (line chart, 60-day)
3. **Feature PSI heatmap** (features × weeks)
4. **Label distribution** (histogram: training vs last 30d)
5. **Calibration curve** (reliability diagram)
6. **Gate activation rate** (time series)

---

## Acceptance Checklist

* [ ] Drift monitoring runs automatically (weekly minimum)
* [ ] Alert thresholds configured in `orbit.yaml`
* [ ] Drift reports archived to `reports/drift/`
* [ ] Retrain triggers tested (dry-run)
* [ ] Dashboard updates daily
* [ ] On-call engineer receives critical alerts

---

## Related Files

* `regime_transition_protocol.md` — Regime-based monitoring frequency
* `runbook.md` — Daily operations
* `data_quality_checks.md` — Ingestion validation
* `logging_audit.md` — What gets logged
* `acceptance_gates.md` — Model promotion criteria

---

