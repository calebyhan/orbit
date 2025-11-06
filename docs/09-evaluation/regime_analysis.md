# ORBIT — Regime Analysis

*Last edited: 2025-11-05*

## Purpose

Analyze model performance across different **market regimes** (volatility, trend, news intensity) to understand when and why ORBIT works. This prevents overfitting to a single market condition and guides deployment decisions.

---

## Why Regime Analysis Matters

* **Risk management:** If edge only exists in low-vol, avoid high-vol periods
* **Gate tuning:** Understand which regimes benefit from text vs pure price
* **Realistic expectations:** Index prediction is regime-dependent
* **Promotional criteria:** v1 must work across multiple regimes before extending to single stocks

---

## Regime Definitions

### 1. Volatility Regimes

Based on **realized volatility** or **VIX**:

**Deciles (preferred for balanced samples):**
- Divide test period into 10 equal-sized buckets by trailing 20-day realized vol
- Compare performance in bottom 3 deciles (low vol) vs top 3 deciles (high vol)

**Terciles:**
- Low: bottom 33%
- Medium: middle 33%
- High: top 33%

**VIX buckets (if VIX data available):**
- Low: VIX < 15
- Medium: 15 ≤ VIX < 25
- High: VIX ≥ 25
- Extreme: VIX ≥ 35

---

### 2. Trend Regimes

Based on **SPY 50-day SMA** vs current price:

**Bull:** SPY > SMA(50) + 2%  
**Neutral:** SPY within ±2% of SMA(50)  
**Bear:** SPY < SMA(50) - 2%

Or use **year-to-date return**:
- Bull: YTD > +10%
- Neutral: -5% ≤ YTD ≤ +10%
- Bear: YTD < -5%

---

### 3. News Intensity Regimes

Based on `news_count_z` from features:

**Quiet:** news_count_z ≤ -0.5  
**Normal:** -0.5 < news_count_z < 1.5  
**Busy:** news_count_z ≥ 1.5

---

### 4. Social Intensity Regimes

Based on `post_count_z` from features:

**Quiet:** post_count_z ≤ -0.5  
**Normal:** -0.5 < post_count_z < 1.5  
**Busy:** post_count_z ≥ 1.5

---

### 5. Combined Text Regimes

**Quiet text:** news_count_z ≤ 0.5 AND post_count_z ≤ 0.5  
**Busy text:** news_count_z > 1.5 OR post_count_z > 1.5  
**Mixed:** all other days

---

## Required Analyses

For each regime dimension, compute:

1. **Performance metrics** (IC, AUC, Sharpe, max DD, coverage)
2. **Hit rate** (% winning trades)
3. **Average gain/loss** per trade
4. **Number of observations** (days in regime)

---

## Analysis 1: Volatility Regimes

**Goal:** Understand if ORBIT is a "low-vol" or "high-vol" strategy.

**Bucket by:** Trailing 20-day realized vol (annualized)

**Report table:**

| Vol Regime | Days | IC | AUC | Sharpe | Max DD | Coverage | Avg Trade Ret |
|------------|------|-----|-----|--------|--------|----------|---------------|
| Low (D1-3) | 189 | 0.018 | 0.541 | 0.52 | -8% | 55% | +0.32% |
| Med (D4-7) | 252 | 0.014 | 0.528 | 0.38 | -12% | 60% | +0.21% |
| High (D8-10) | 189 | 0.008 | 0.515 | 0.18 | -22% | 68% | +0.09% |

**Interpretation example:**
- ORBIT works best in low-vol (higher IC, Sharpe)
- High-vol trades more often (higher coverage) but worse risk-adjusted returns
- **Action:** Consider flattening when realized vol > 90th percentile

---

## Analysis 2: Trend Regimes

**Goal:** Does ORBIT work in both bull and bear markets?

**Bucket by:** SPY vs 50-day SMA

**Report table:**

| Trend | Days | IC | Sharpe | Max DD | Hit Rate |
|-------|------|-----|--------|--------|----------|
| Bull | 385 | 0.016 | 0.41 | -14% | 56% |
| Neutral | 180 | 0.012 | 0.28 | -10% | 53% |
| Bear | 65 | 0.022 | 0.63 | -18% | 58% |

**Interpretation example:**
- Surprisingly strong in bear (fear-driven news more predictive?)
- Weakest in neutral (low signal)
- **Action:** Consider raising threshold in neutral regime

---

## Analysis 3: News Intensity Regimes

**Goal:** Validate that news features add value on busy news days.

**Bucket by:** news_count_z

**Report table (for Price+News ablation vs Price-Only):**

| News Regime | Days | IC (Price-Only) | IC (Price+News) | ΔIC | Sharpe (Price+News) |
|-------------|------|-----------------|-----------------|-----|---------------------|
| Quiet | 142 | 0.011 | 0.010 | -0.001 | 0.18 |
| Normal | 378 | 0.012 | 0.015 | +0.003 | 0.29 |
| Busy | 110 | 0.008 | 0.034 | +0.026 | 0.58 |

**Interpretation example:**
- News helps most on busy days (+0.026 IC lift)
- Minimal drag on quiet days (gate working correctly)
- **Action:** Gates are well-tuned; keep current formula

---

## Analysis 4: Social Intensity Regimes

**Goal:** Validate that social features add value on high-buzz days.

**Bucket by:** post_count_z

**Report table (for Price+Social ablation vs Price-Only):**

| Social Regime | Days | IC (Price-Only) | IC (Price+Social) | ΔIC | Sharpe (Price+Social) |
|---------------|------|-----------------|-------------------|-----|----------------------|
| Quiet | 158 | 0.010 | 0.009 | -0.001 | 0.17 |
| Normal | 352 | 0.013 | 0.016 | +0.003 | 0.25 |
| Busy | 120 | 0.009 | 0.028 | +0.019 | 0.47 |

**Interpretation example:**
- Social helps on busy days (+0.019 IC lift)
- No harm on quiet days
- **Action:** Social gate working as designed

---

## Analysis 5: Combined Regimes (2D)

**Goal:** Identify "sweet spots" (e.g., low vol + busy text).

**Report table (Days × Performance):**

|                | Quiet Text | Normal Text | Busy Text |
|----------------|-----------|-------------|-----------|
| **Low Vol**    | IC: 0.015, Sharpe: 0.42 | IC: 0.020, Sharpe: 0.55 | IC: 0.038, Sharpe: 0.82 |
| **Med Vol**    | IC: 0.010, Sharpe: 0.28 | IC: 0.014, Sharpe: 0.35 | IC: 0.025, Sharpe: 0.51 |
| **High Vol**   | IC: 0.005, Sharpe: 0.12 | IC: 0.009, Sharpe: 0.18 | IC: 0.014, Sharpe: 0.29 |

**Interpretation example:**
- Best performance: Low vol + Busy text (IC=0.038, Sharpe=0.82)
- Worst: High vol + Quiet text (IC=0.005, Sharpe=0.12)
- **Action:** Raise threshold in High Vol + Quiet Text regime (or flatten entirely)

---

## Regime-Specific Gates (Advanced)

If certain regimes show poor performance, consider **regime-aware gating**:

```python
if realized_vol_percentile > 90:
    # High vol: flatten or trade less aggressively
    threshold *= 1.5
elif news_count_z > 2 and realized_vol_percentile < 50:
    # Low vol + big news: boost text weight
    news_gate *= 1.2
```

Document any regime-specific rules in `fusion_gated_blend.md` and `risk_controls.md`.

---

## Visualization Specs

### 1. Heatmap: IC by Vol × Text Regimes

**Axes:**
- X: Text intensity (Quiet, Normal, Busy)
- Y: Volatility (Low, Med, High)
- Color: IC value

**Tool:** matplotlib, seaborn

---

### 2. Box Plot: Sharpe by Regime

**X-axis:** Regime buckets (e.g., Low Vol, Med Vol, High Vol)  
**Y-axis:** Daily Sharpe (rolling 20d)  
**Box:** 25th/50th/75th percentiles  
**Whiskers:** Min/max

---

### 3. Time Series: Cumulative Return by Regime

**Lines:**
- Price-Only (all days)
- All modalities (all days)
- All modalities (low vol only)
- All modalities (busy text only)

**Goal:** Show which regimes drive cumulative alpha.

---

## Output Artifacts

**Path:** `reports/regime_analysis/<run_id>/`

**Files:**
- `regime_metrics.parquet` — Daily rows with regime labels + performance
- `regime_summary.json` — Aggregated stats per regime
- `regime_plots.pdf` — Heatmaps, box plots, time series
- `regime_report.md` — Narrative summary with interpretation

---

## Acceptance Checklist

* [ ] At least 3 regime dimensions analyzed (vol, news, social)
* [ ] Each regime bucket has ≥30 observations (for statistical validity)
* [ ] IC and Sharpe reported for each bucket
* [ ] Conditional performance (text ablations) analyzed within regimes
* [ ] Regime-specific failure modes identified and documented
* [ ] Visualizations generated and saved to reports/

---

## Failure Modes

### Edge Only in One Regime

**Symptom:** IC > 0.02 in low-vol, but IC ≈ 0 in med/high vol

**Diagnosis:** Model overfitting to low-vol conditions (or edge genuinely regime-specific)

**Action:**
- If genuine: add regime classifier to flatten in unfavorable regimes
- If overfitting: regularize heads more, expand training data

---

### Text Hurts in High Vol

**Symptom:** Price-Only outperforms All in high-vol regime

**Diagnosis:** Sentiment is noisy in volatile markets; gates should down-weight but may not be aggressive enough

**Action:**
- Add vol-dependent gate damping: `news_gate *= max(0.5, 1 - vol_z)`
- Consider flattening when vol > 90th percentile

---

### No Regime Differences

**Symptom:** IC and Sharpe similar across all vol/trend/text regimes

**Diagnosis:** 
- Regime definitions too coarse
- Model is robust (good!) or has no real edge (bad)

**Action:**
- Refine regime buckets (use deciles instead of terciles)
- Check if baseline (buy-and-hold) also shows no regime differences

---

## Related Files

* `metrics_definitions.md` — Metric calculation details
* `ablations_checklist.md` — Ablation experiments per modality
* `fusion_gated_blend.md` — Gate formula (may need regime-specific tuning)
* `risk_controls.md` — Regime-based flattening rules
* `dashboard_spec.md` — Visualization specs

---

## Example: Monthly Regime Report

**Run ID:** 2024-q4-v1  
**Test Period:** 2024-01-01 to 2024-12-31

**Key Findings:**

1. **Volatility:** ORBIT works best in low-to-medium vol (Sharpe 0.5+). High-vol trades show hit-rate <52%.
2. **Trend:** Surprisingly strong in bear markets (IC=0.026 vs 0.015 in bull). Fear-driven news may be more predictive.
3. **Text Intensity:** On busy text days (news_count_z > 1.5 OR post_count_z > 1.5), IC lifts from 0.011 → 0.032 (+190% relative).
4. **Sweet Spot:** Low vol + Busy text (n=38 days) → IC=0.041, Sharpe=0.89, Hit-rate=61%.

**Recommendations:**
- Flatten when realized vol > 95th percentile
- Raise threshold in neutral trend + quiet text days
- Keep current gates (working as designed)

---

