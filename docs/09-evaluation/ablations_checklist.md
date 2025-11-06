
*Last edited: 2025-11-05*

## Purpose

Define the **required ablation experiments** to validate that each modality (prices, news, social) contributes meaningful signal. Ablations help prevent overfitting and ensure we're not fooling ourselves.

---

## Why Ablations Matter

* **Prove incremental value:** Each modality should add risk-adjusted performance
* **Detect overfitting:** If +News or +Social hurts performance, the features may be noise
* **Guide resource allocation:** If social adds nothing, skip the Reddit scraper in production
* **Scientific rigor:** Required before promoting v1 to single-stock universe

---

## Required Ablation Runs

Every training/backtest cycle must produce these 4 variants:

### 1. **Price-Only (Baseline)**

**Modalities:** Price features only  
**Heads active:** Price head  
**Fusion:** N/A (single head)

**Expected performance:**
- IC: ~0.00–0.02
- Sharpe: ~0.1–0.3
- This is the **floor**; text must beat this to be useful

**Config:**
```yaml
ablation:
  enabled_modalities: [price]
```

---

### 2. **Price + News**

**Modalities:** Price + News features  
**Heads active:** Price head, News head  
**Fusion:** Gated blend with news gate based on `news_count_z`, `news_novelty`

**Expected lift vs baseline:**
- ΔIC: +0.01 to +0.02 (on busy news days)
- ΔSharpe: +0.1 to +0.2
- Max DD: should not increase >5 ppt

**Config:**
```yaml
ablation:
  enabled_modalities: [price, news]
```

---

### 3. **Price + Social**

**Modalities:** Price + Social features  
**Heads active:** Price head, Social head  
**Fusion:** Gated blend with social gate based on `post_count_z`, `social_novelty`

**Expected lift vs baseline:**
- ΔIC: +0.005 to +0.015 (on high-buzz days)
- ΔSharpe: +0.05 to +0.15
- May improve risk (lower DD) even if return lift is modest

**Config:**
```yaml
ablation:
  enabled_modalities: [price, social]
```

---

### 4. **All (Price + News + Social)**

**Modalities:** All three  
**Heads active:** Price, News, Social  
**Fusion:** Full gated blend

**Expected performance:**
- IC: ~0.01–0.03 (target)
- Sharpe: ~0.3–0.6 (target)
- Should be ≥ best 2-modality variant

**Config:**
```yaml
ablation:
  enabled_modalities: [price, news, social]
```

---

## Acceptance Criteria

For each ablation run, check:

### Performance Metrics

| Metric | Baseline (Price-Only) | +News | +Social | All |
|--------|----------------------|-------|---------|-----|
| Daily IC | 0.01 | ≥ baseline | ≥ baseline | ≥ best 2-mod |
| AUC | 0.52 | ≥ 0.52 | ≥ 0.52 | ≥ 0.54 |
| Sharpe | 0.2 | ≥ 0.2 | ≥ 0.2 | ≥ 0.3 |
| Max DD | -20% | ≤ baseline+5ppt | ≤ baseline+5ppt | ≤ baseline+5ppt |
| Coverage | 60% | 50-70% | 50-70% | 50-70% |

### Conditional Performance (Critical)

**On busy days** (news_count_z > 1.5 OR post_count_z > 1.5):
- Text-augmented runs should show **higher IC** and **higher Sharpe** than price-only
- If not, gates may be misconfigured

**On quiet days** (news_count_z ≤ 0.5 AND post_count_z ≤ 0.5):
- All variants should perform similarly (gates should down-weight text)
- Text should not **hurt** performance

---

## Gating Validation

For Price+News, Price+Social, and All runs:

* **Gate activation frequency:**
  - News gate: should be active (>0.5) on ~20-30% of days
  - Social gate: should be active (>0.5) on ~15-25% of days

* **Gate correlation with performance:**
  - On days where news_gate > 0.7, IC(Price+News) should exceed IC(Price-Only)
  - If not, gate formula needs tuning (see `fusion_gated_blend.md`)

---

## Ablation Report Format

**Path:** `reports/ablations/<run_id>/ablation_summary.md`

**Template:**

```markdown
# Ablation Summary — <run_id>

**Date:** <timestamp>  
**Train period:** <start_date> to <end_date>  
**Test period:** <start_date> to <end_date>

## Overall Metrics

| Variant | IC | AUC | Sharpe | Max DD | Coverage | Total Ret |
|---------|-----|-----|--------|--------|----------|-----------|
| Price-Only | 0.012 | 0.523 | 0.21 | -18% | 58% | +12% |
| Price+News | 0.019 | 0.547 | 0.34 | -16% | 62% | +19% |
| Price+Social | 0.015 | 0.535 | 0.27 | -14% | 60% | +15% |
| All | 0.023 | 0.558 | 0.42 | -15% | 64% | +24% |

**Winner:** All (highest Sharpe, best IC)

## Conditional Performance

### Busy Days (n=142, news_count_z > 1.5 OR post_count_z > 1.5)

| Variant | IC | Sharpe |
|---------|-----|--------|
| Price-Only | 0.008 | 0.15 |
| Price+News | 0.032 | 0.51 |
| Price+Social | 0.024 | 0.38 |
| All | 0.041 | 0.63 |

**Observation:** Text modalities shine on busy days (4x IC lift for All vs Price-Only).

### Quiet Days (n=503, news_count_z ≤ 0.5 AND post_count_z ≤ 0.5)

| Variant | IC | Sharpe |
|---------|-----|--------|
| Price-Only | 0.011 | 0.19 |
| Price+News | 0.010 | 0.18 |
| Price+Social | 0.009 | 0.17 |
| All | 0.009 | 0.17 |

**Observation:** Gates correctly down-weight text on quiet days (minimal degradation).

## Gate Statistics

| Gate | Mean | Median | Activation Rate (>0.5) |
|------|------|--------|------------------------|
| news_gate | 0.32 | 0.18 | 24% |
| social_gate | 0.28 | 0.14 | 19% |

## Acceptance

- [x] All variants beat price-only on busy days
- [x] Text does not hurt quiet-day performance
- [x] Max DD within tolerance (+5ppt)
- [x] Gates activate on appropriate days

**Verdict:** PASS — Promote to production
```

---

## Automation

Ablation runs should be **automated** in the training pipeline:

```bash
# Run all 4 ablations
python -m orbit.train --config orbit.yaml --ablation price_only
python -m orbit.train --config orbit.yaml --ablation price_news
python -m orbit.train --config orbit.yaml --ablation price_social
python -m orbit.train --config orbit.yaml --ablation all

# Generate comparison report
python -m orbit.evaluate.ablations --run_id <run_id>
```

---

## Failure Modes

### Text Hurts Performance

**Symptoms:**
- Price+News has lower Sharpe than Price-Only
- Max DD increases >5 ppt

**Diagnosis:**
- Overfitting: heads are too complex
- Leakage: cutoff not respected
- Bad sentiment scores: LLM escalation buggy

**Fix:**
- Simplify heads (fewer layers, stronger regularization)
- Audit time alignment (see `time_alignment_cutoffs.md`)
- Check sentiment scorer (run spot-checks on sample posts/headlines)

### Gates Don't Activate

**Symptoms:**
- news_gate always <0.2, even on high news_count_z days
- Performance of Price+News ≈ Price-Only everywhere

**Diagnosis:**
- Gate formula misconfigured (weights α, β too small)
- news_count_z not properly z-scored

**Fix:**
- Tune gate weights (see `fusion_gated_blend.md`)
- Verify feature standardization (see `standardization_scaling.md`)

### Text Only Helps on Extreme Days

**Symptoms:**
- IC lift only visible on top 5% of busy days
- Coverage drops to <20% when text is added

**Diagnosis:**
- Threshold τ too high, only trading on obvious events
- Gates too conservative

**Fix:**
- Lower threshold (trade more often)
- Relax gate activation formula

---

## Regime-Aware Ablations (Advanced)

For deeper analysis, repeat ablations within **regime buckets** (see `regime_analysis.md`):

* **Low vol regime** (VIX < 15): Does text still help?
* **High vol regime** (VIX > 25): Does text improve risk-adjusted returns?
* **Bull market** (SPY +10% YTD): vs **Bear market** (SPY -10% YTD)

---

## Related Files

* `metrics_definitions.md` — How IC, Sharpe, etc. are computed
* `fusion_gated_blend.md` — Gate formula and tuning
* `regime_analysis.md` — Regime-specific analysis
* `dashboard_spec.md` — Plots to visualize ablations

---

