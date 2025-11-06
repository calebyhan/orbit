
*Last edited: 2025-11-05*

## Purpose

Define the **plots, tables, and visualizations** to generate after each backtest run. A complete dashboard ensures we can quickly assess model quality, identify failure modes, and compare across runs.

---

## Output Location

**Path:** `reports/backtest/<run_id>/dashboard/`

**Files:**
- `dashboard.html` — Interactive HTML with all plots
- `dashboard.pdf` — Static PDF for archival
- `plots/*.png` — Individual plot images
- `tables/*.csv` — Exportable data tables

---

## Required Visualizations

### 1. Equity Curve (Normalized)

**Type:** Line plot  
**X-axis:** Date  
**Y-axis:** Normalized equity (start = 1.0)  
**Lines:**
- ORBIT strategy (all modalities)
- Buy-and-hold SPY
- Price-only baseline (for comparison)

**Shading:**
- Gray bands for drawdown periods (>10% from peak)
- Optional: regime bands (low/med/high vol)

**Goal:** Show cumulative performance vs benchmark.

**File:** `plots/equity_curve.png`

---

### 2. Rolling Sharpe Ratio

**Type:** Line plot  
**X-axis:** Date  
**Y-axis:** Rolling 60-day Sharpe (annualized)  
**Lines:**
- ORBIT strategy
- Buy-and-hold SPY

**Horizontal lines:**
- Sharpe = 0 (break-even)
- Sharpe = 0.5 (target threshold)

**Goal:** Show time-varying risk-adjusted performance.

**File:** `plots/rolling_sharpe.png`

---

### 3. Rolling IC (Information Coefficient)

**Type:** Line plot  
**X-axis:** Date  
**Y-axis:** Rolling 60-day Spearman IC  
**Line:** `fused_score_t` vs next-day return

**Horizontal lines:**
- IC = 0
- IC = 0.02 (target threshold)

**Goal:** Track predictive power over time.

**File:** `plots/rolling_ic.png`

---

### 4. Drawdown Chart

**Type:** Area plot  
**X-axis:** Date  
**Y-axis:** Drawdown from running peak (%)  
**Fill:** Red area showing depth of drawdowns

**Annotations:**
- Max drawdown value and date
- Drawdown duration (peak-to-recovery)

**Goal:** Visualize risk/loss periods.

**File:** `plots/drawdown.png`

---

### 5. Daily Returns Distribution

**Type:** Histogram + KDE overlay  
**X-axis:** Daily net return (%)  
**Y-axis:** Frequency  
**Lines:**
- ORBIT strategy (blue)
- Buy-and-hold SPY (gray, dashed)

**Statistics overlay:**
- Mean, Median, Std
- Skewness, Kurtosis
- 5th and 95th percentiles

**Goal:** Understand return distribution shape.

**File:** `plots/returns_distribution.png`

---

### 6. Monthly Returns Heatmap

**Type:** Heatmap  
**Rows:** Years  
**Columns:** Months (Jan-Dec)  
**Values:** Monthly return (%)  
**Color:** Green (positive) to Red (negative)

**Goal:** Identify seasonal patterns or bad months.

**File:** `plots/monthly_heatmap.png`

---

### 7. Trade Analysis

**Type:** Bar chart  
**Categories:** Long trades, Flat days  
**Metrics:**
- Count
- Avg return
- Win rate
- Avg winner / Avg loser

**Goal:** Understand trade quality.

**File:** `plots/trade_analysis.png`

---

### 8. Coverage & Threshold

**Type:** Dual-axis line plot  
**X-axis:** Date  
**Y-axis (left):** Position (0 or 1)  
**Y-axis (right):** Fused score

**Lines:**
- Position indicator (step)
- Fused score (line)
- Threshold (horizontal dashed)

**Goal:** Visualize when model takes positions.

**File:** `plots/coverage_threshold.png`

---

### 9. Ablation Comparison (Bar Chart)

**Type:** Grouped bar chart  
**X-axis:** Metrics (IC, Sharpe, Max DD, Hit Rate, Coverage)  
**Y-axis:** Metric value  
**Groups:**
- Price-Only
- Price+News
- Price+Social
- All

**Goal:** Compare ablation performance at a glance.

**File:** `plots/ablation_comparison.png`

---

### 10. Regime Performance (Heatmap)

**Type:** Heatmap  
**Rows:** Volatility regime (Low, Med, High)  
**Columns:** Text intensity (Quiet, Normal, Busy)  
**Values:** IC or Sharpe  
**Color:** Blue (low) to Green (high)

**Goal:** Identify sweet spots and failure regimes.

**File:** `plots/regime_heatmap.png`

---

### 11. Regime Performance (Box Plots)

**Type:** Box plot  
**X-axis:** Regime buckets (e.g., Low Vol, Med Vol, High Vol)  
**Y-axis:** Daily Sharpe (rolling 20d)  
**Boxes:** Show quartiles per regime

**Goal:** Compare performance distribution across regimes.

**File:** `plots/regime_boxplot.png`

---

### 12. Score Calibration (Classification)

**Type:** Reliability diagram  
**X-axis:** Predicted probability (binned)  
**Y-axis:** Observed frequency (actual up days)  
**Line:** Diagonal (perfect calibration)  
**Scatter:** Actual calibration points

**Goal:** Check if probabilities are well-calibrated.

**File:** `plots/calibration.png`

---

### 13. ROC Curve (Classification)

**Type:** ROC plot  
**X-axis:** False positive rate  
**Y-axis:** True positive rate  
**Curve:** Model ROC  
**Diagonal:** Random classifier

**Annotation:** AUC value

**Goal:** Assess classification quality.

**File:** `plots/roc_curve.png`

---

### 14. Precision-Recall Curve

**Type:** PR plot  
**X-axis:** Recall  
**Y-axis:** Precision  
**Curve:** Model PR

**Goal:** Understand precision/recall trade-off at different thresholds.

**File:** `plots/precision_recall.png`

---

### 15. Feature Importance (if available)

**Type:** Horizontal bar chart  
**X-axis:** Importance score (or Shapley value)  
**Y-axis:** Feature names  
**Bars:** Top 20 features

**Goal:** Understand which features drive predictions.

**File:** `plots/feature_importance.png`

---

### 16. Gate Activation Over Time

**Type:** Line plot  
**X-axis:** Date  
**Y-axis:** Gate value (0 to 1)  
**Lines:**
- news_gate
- social_gate

**Shading:**
- Activation threshold (e.g., 0.5)

**Goal:** Show when text modalities are up-weighted.

**File:** `plots/gate_activation.png`

---

### 17. Costs Impact

**Type:** Line plot  
**X-axis:** Date  
**Y-axis:** Cumulative equity  
**Lines:**
- Gross returns (no costs)
- Net returns (with costs)
- Cost difference (area between)

**Goal:** Quantify cost drag.

**File:** `plots/costs_impact.png`

---

### 18. Threshold Sensitivity (Sharpe)

**Type:** Line plot  
**X-axis:** Threshold (τ)  
**Y-axis:** Sharpe ratio  
**Line:** Sharpe at different thresholds

**Annotation:** Optimal threshold (max Sharpe)

**Goal:** Tune threshold parameter.

**File:** `plots/threshold_sharpe.png`

---

### 19. Threshold Sensitivity (Coverage)

**Type:** Line plot  
**X-axis:** Threshold (τ)  
**Y-axis:** Coverage (% days traded)  
**Line:** Coverage at different thresholds

**Goal:** Understand threshold vs trading frequency.

**File:** `plots/threshold_coverage.png`

---

## Required Tables

### Table 1: Summary Metrics

**File:** `tables/summary_metrics.csv`

| Metric | Value |
|--------|-------|
| Total Return | +24.3% |
| Annualized Return | +4.8% |
| Annualized Volatility | 11.2% |
| Sharpe Ratio | 0.42 |
| Max Drawdown | -15.1% |
| Daily IC | 0.023 |
| AUC | 0.558 |
| Hit Rate | 54.2% |
| Coverage | 64.0% |
| Avg Winner | +0.81% |
| Avg Loser | -0.69% |
| Win/Loss Ratio | 1.17 |
| Total Trades | 403 |
| Turnover (annual) | 160% |

---

### Table 2: Monthly Performance

**File:** `tables/monthly_performance.csv`

| Month | Return | Sharpe | IC | Coverage | Trades |
|-------|--------|--------|-----|----------|--------|
| 2024-01 | +2.1% | 0.52 | 0.018 | 68% | 14 |
| 2024-02 | -0.8% | -0.12 | 0.005 | 55% | 11 |
| ... | ... | ... | ... | ... | ... |

---

### Table 3: Regime Performance

**File:** `tables/regime_performance.csv`

| Regime | Days | IC | Sharpe | Max DD | Hit Rate | Coverage |
|--------|------|-----|--------|--------|----------|----------|
| Low Vol | 189 | 0.028 | 0.61 | -8% | 58% | 62% |
| Med Vol | 252 | 0.019 | 0.38 | -12% | 53% | 64% |
| High Vol | 189 | 0.011 | 0.22 | -22% | 51% | 68% |

---

### Table 4: Ablation Results

**File:** `tables/ablation_results.csv`

| Ablation | IC | AUC | Sharpe | Max DD | Coverage | Total Ret |
|----------|-----|-----|--------|--------|----------|-----------|
| Price-Only | 0.012 | 0.523 | 0.21 | -18% | 58% | +12% |
| Price+News | 0.019 | 0.547 | 0.34 | -16% | 62% | +19% |
| Price+Social | 0.015 | 0.535 | 0.27 | -14% | 60% | +15% |
| All | 0.023 | 0.558 | 0.42 | -15% | 64% | +24% |

---

### Table 5: Worst Drawdown Periods

**File:** `tables/worst_drawdowns.csv`

| Start Date | End Date | Duration (days) | Depth | Recovery Date |
|------------|----------|-----------------|-------|---------------|
| 2024-03-12 | 2024-04-05 | 24 | -15.1% | 2024-05-02 |
| 2024-07-18 | 2024-08-02 | 15 | -8.3% | 2024-08-22 |
| ... | ... | ... | ... | ... |

---

### Table 6: Best/Worst Days

**File:** `tables/extreme_days.csv`

**Best 10 days:**
| Date | Return | Position | Score | News Count Z | Post Count Z |
|------|--------|----------|-------|--------------|--------------|
| 2024-11-06 | +2.8% | 1.0 | 0.68 | 2.4 | 1.8 |
| ... | ... | ... | ... | ... | ... |

**Worst 10 days:**
| Date | Return | Position | Score | News Count Z | Post Count Z |
|------|--------|----------|-------|--------------|--------------|
| 2024-08-05 | -2.1% | 1.0 | 0.62 | 1.2 | 0.8 |
| ... | ... | ... | ... | ... | ... |

---

## Interactive Dashboard Features (HTML)

If generating an HTML dashboard, include:

1. **Hover tooltips** on all line/scatter plots (show date + value)
2. **Zoom controls** for time series plots
3. **Dropdown filters:**
   - Select ablation variant
   - Select regime bucket
   - Select date range
4. **Tabs:**
   - Overview (equity, Sharpe, IC)
   - Risk (drawdown, vol, costs)
   - Regimes (heatmaps, boxplots)
   - Ablations (comparison charts)
   - Diagnostics (calibration, ROC, PR)

**Tool recommendations:** Plotly (interactive), Matplotlib/Seaborn (static)

---

## Automation

Dashboard generation should be **fully automated**:

```bash
# After backtest completes
python -m orbit.evaluate.dashboard --run_id <run_id>

# Generates:
# reports/backtest/<run_id>/dashboard/dashboard.html
# reports/backtest/<run_id>/dashboard/dashboard.pdf
# reports/backtest/<run_id>/dashboard/plots/*.png
# reports/backtest/<run_id>/dashboard/tables/*.csv
```

---

## Acceptance Checklist

* [ ] All 19 required plots generated
* [ ] All 6 required tables exported
* [ ] HTML dashboard is interactive and loads without errors
* [ ] PDF dashboard is print-ready (all plots visible)
* [ ] Plots are publication-quality (labels, legends, titles)
* [ ] Tables have consistent formatting (2 decimal places for %)
* [ ] Dashboard generation completes in <2 minutes

---

## Example: Top-Level Summary (dashboard.html intro)

```markdown
# ORBIT Backtest Dashboard

**Run ID:** 2024-q4-v1  
**Strategy:** Long/Flat Overnight  
**Asset:** SPY  
**Period:** 2024-01-01 to 2024-12-31 (252 days)  
**Modalities:** Price + News + Social  

## Quick Stats

- **Total Return:** +24.3% (vs +18.1% buy-and-hold)
- **Sharpe Ratio:** 0.42 (vs 0.31 buy-and-hold)
- **Max Drawdown:** -15.1% (vs -19.4% buy-and-hold)
- **Hit Rate:** 54.2% (403 trades)
- **Coverage:** 64.0% (161 days long, 91 days flat)

## Key Findings

1. **Text adds value:** All-modalities IC = 0.023 vs Price-only IC = 0.012
2. **Best regime:** Low vol + Busy text (IC = 0.041, Sharpe = 0.82)
3. **Worst regime:** High vol + Quiet text (IC = 0.005, Sharpe = 0.12)
4. **Costs impact:** ~3.2% annual drag (realistic at 2bps/side)

[See detailed plots and tables below]
```

---

## Related Files

* `metrics_definitions.md` — How metrics are calculated
* `backtest_long_flat_spec.md` — Backtest execution details
* `ablations_checklist.md` — Ablation experiment specs
* `regime_analysis.md` — Regime-specific analysis
* `report_templates.md` — JSON/Parquet output schemas

---

