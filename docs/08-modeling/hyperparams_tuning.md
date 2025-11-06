# ORBIT — Hyperparameters & Tuning

*Last edited: 2025-11-05*

## Purpose

Provide **small, robust search spaces** and tuning protocols per model so we avoid overfitting on limited daily data.

---

## General rules

* Tune **within each walk‑forward window** using the **validation** slice only.
* Keep search spaces **tiny** (≤ 20 candidates) and prefer **monotone** or regularized models.
* Fix **random Seeds** per window for reproducibility.
* Track best config and **lock** it for that window; do **not** reuse across windows unless justified.

---

## Metrics & selection

* **Classification:** primary = **AUC**, tie‑breakers = Brier ↓ then LogLoss ↓.
* **Regression:** primary = **RMSE** ↓, tie‑breakers = MAE ↓ then IC ↑.
* Monitor **stability**: variance of metrics across folds/months inside the window.

---

## GBM (LightGBM/XGBoost‑style)

Search grid (example; pick 12–16 combos):

```yaml
n_estimators:   [200, 400, 800]
learning_rate:  [0.02, 0.05]
max_depth:      [3, 4]
min_data_in_leaf/min_child_weight: [25, 50, 100]
subsample:      [0.7, 0.85]
colsample_bytree: [0.7, 0.9]
reg_lambda:     [0.0, 1.0]
reg_alpha:      [0.0, 0.5]
```

Early stop on **val** (patience 50–100 trees). Keep best iteration.

### Constraints (optional)

* Monotonic constraints when justified (e.g., `rv_10d_spx` ↘ p_up). Use sparingly.

---

## MLP (tabular)

Search grid (8–12 combos):

```yaml
hidden_layers: [[32,16], [64,32], [64,32,16]]
activation: [relu]
dropout: [0.0, 0.1, 0.2]
l2_weight: [1e-6, 1e-5, 1e-4]
lr: [5e-4, 1e-3]
batch_size: [32, 64]
epochs: [200]
early_stop_patience: [10]
```

Use **weight decay** and **dropout**; avoid batch norm on tiny datasets.

---

## Fusion (gated blend)

Tune only a **handful** of parameters on **validation**:

```yaml
w_price:  [0.5, 0.6, 0.7]
w_news:   [0.1, 0.2, 0.3]
w_social: [0.1, 0.2, 0.3]
alpha_n0: [0.0]
alpha_n1: [0.5, 1.0]
alpha_n2: [0.25, 0.75]
alpha_s0: [0.0]
alpha_s1: [0.5, 1.0]
alpha_s2: [0.25, 0.75]
beta_n:   [0.5, 1.0]
beta_s:   [0.5, 1.0]
```

Regularize: L2 on alphas (e.g., 1e‑2), small L1 on betas to discourage over‑aggressive gating.

---

## Practical tips

* Prefer **AUC** over accuracy for imbalanced daily direction.
* Plot **reliability curves** (calibration) for heads and fusion.
* Keep **feature sets fixed** per window; changing features mid‑search biases results.
* Record **feature importance** drift across windows; prune unstable features.
* Use **early termination** of bad configs to save time (median stopping).

---

## Artifacts

* `models/*/metadata.json` should include: chosen params, val metrics, best_iteration (GBM), window dates, seed, library versions.
* `reports/ablations/` should log performance deltas for each modality and the fusion relative to a simple average.

---

## Acceptance checklist

* Each window selects a **single** best config per head and for fusion based on **validation** metrics.
* Search spaces are small; results are reproducible (fixed seeds).
* Artifacts and reports capture the chosen params and metrics for audit.

---

## Related Files

* `08-modeling/heads_price_news_social.md` — Model architectures
* `08-modeling/training_walkforward.md` — Training procedure
* `09-evaluation/ablations_checklist.md` — Ablation studies
