# ORBIT — Heads: Price, News, Social

*Last edited: 2025-11-05*

## Purpose

Specify the **per‑modality heads** that map daily features → a scalar score for day *T*. Each head is trained in a **walk‑forward** regime and obeys point‑in‑time rules.

* **Input:** feature subset for the modality on day *t* (no future info).
* **Output:**

  * **Classification task:** `p_up_head ∈ [0,1]` (probability next return > 0).
  * **Regression task:** `ret_head` (expected bps for next day).
* **Models supported (choose per head in config):**

  * Gradient‑boosted trees (**GBM**, e.g., LightGBM/XGBoost‑compatible API)
  * Small **MLP** (2–3 layers) with dropout + early stop

> Default in `config`: **GBM** for all three heads (stable on tabular, small data).

---

## 1) Price head

### Inputs (from `07-features/price_features.md`)

Recommended columns (z‑scored where applicable):

* `mom_5d_spy, mom_20d_spy, rev_1d_spy, rv_10d_spy, atrp_14d_spy, drawdown_spy, vol_z_60d_spy, basis_spy_spx, mom_5d_spx, rv_10d_spx, term_struc_vol`

### Target

* From `08-modeling/targets_labels.md` according to `labels.target` and `labels.use_excess`.

### Loss

* Classification: **logloss** (binary cross‑entropy).
* Regression: **L2** on bps (optionally Huber).

### Regularization / constraints

* `max_depth` small (≤4), `min_child_weight`/`min_data_in_leaf` tuned to avoid overfit.
* Optionally **monotonic** constraints (e.g., higher vol ⇒ lower p_up) if empirically justified.

### Output

* `price_head_score_t` (probability or expected bps) and optional **calibrated** prob (isotonic/Platt on rolling val).

---

## 2) News head

### Inputs (from `07-features/news_features.md`)

* `news_count_z, news_burst, news_novelty, news_sent_mean, news_sent_abs_mean, news_sent_max, news_recency_min`
* Optional: `news_source_weighted_mean, news_sent_trend_3d`

### Notes

* Strong sparseness: `news_count==0` days carry limited info → tree models handle this well.

### Loss & output

* Same as price head; output `news_head_score_t` (prob or bps) + calibrated prob if classification.

---

## 3) Social head

### Inputs (from `07-features/social_features.md`)

* `soc_post_count_z, soc_burst, soc_comment_velocity, soc_novelty, soc_sent_mean, soc_sent_abs_mean, soc_sarcasm_rate, soc_recency_min`
* Optional LLM: `soc_sent_llm_mean, soc_stance_bull_share, soc_stance_bear_share`

### Loss & output

* Same as others; output `social_head_score_t`.

---

## Training protocol (applies to all heads)

1. **Walk‑forward splits** from `config.training.split` (e.g., 12m train / 1m val / 1m test, step 1m).
2. **Standardization** already baked into features (rolling z‑scores). Do **not** leak by re‑fitting scalers.
3. **Class imbalance** (classification): optional balanced weights.
4. **Hyperparams**: use small grids; select by **validation** logloss/AUC (classification) or RMSE/MAE (regression).
5. **Calibration** (classification): fit **Platt** or **isotonic** on the **validation** month only, then freeze.
6. **Model artifacts**: save to `models/heads/<modality>/<run_id>/` with `model.pkl`, `calibrator.pkl` (if any), and `metadata.json` (feature list, hash, metrics).

### Early stopping

* Use rolling **validation** within each window; patience 50–100 trees (GBM) or 10 epochs (MLP). Stop on no improvement.

### Feature importance

* Persist gain/split importances (GBM) and permutation IC on val. Log the **top 10** features by modality per window.

---

## Reference hyperparameters

### GBM (default)

```yaml
model: gbm
params:
  n_estimators: 400
  learning_rate: 0.03
  max_depth: 3
  subsample: 0.8
  colsample_bytree: 0.8
  min_child_weight: 10        # or min_data_in_leaf: 50 (lib dependent)
  reg_alpha: 0.0
  reg_lambda: 1.0
  tree_method: hist           # when available
```

### MLP (alternative)

```yaml
model: mlp
params:
  hidden_layers: [32, 16]
  activation: relu
  dropout: 0.1
  l2_weight: 1e-5
  batch_size: 64
  epochs: 200
  lr: 1e-3
  early_stop_patience: 10
```

---

## Scoring (daily)

At the end of day *T* (post features build):

```python
x_price_T  = features_T[PRICE_COLS]
x_news_T   = features_T[NEWS_COLS]
x_social_T = features_T[SOC_COLS]

s_price  = model_price.predict_proba(x_price_T)[:,1]   # or predict() for regression
s_news   = model_news.predict_proba(x_news_T)[:,1]
s_social = model_social.predict_proba(x_social_T)[:,1]

# apply calibrators if present
p_price  = calib_price.transform(s_price)
p_news   = calib_news.transform(s_news)
p_social = calib_social.transform(s_social)

save_head_scores(date=T, price=p_price, news=p_news, social=p_social)
```

---

## Anti‑leak rules

* Heads train **only** on features and labels constructed with **past‑only** info (see 06/07/08 docs).
* Calibration uses the **validation** slice of each rolling window (never test).
* No leakage from future standardization, imputation, or resampling.

---

## Acceptance checklist

* Each head trains per window and saves artifacts with feature lists and metrics.
* Daily scoring produces `price_head_score_t`, `news_head_score_t`, `social_head_score_t`.
* Calibration (if enabled) is fit **only on validation** and applied consistently at score time.
* Feature importance and basic metrics are logged for audit.

---

## Related Files

* `07-features/price_features.md` — Price head inputs
* `07-features/news_features.md` — News head inputs
* `07-features/social_features.md` — Social head inputs
* `08-modeling/fusion_gated_blend.md` — Head fusion
* `08-modeling/hyperparams_tuning.md` — Hyperparameter tuning
