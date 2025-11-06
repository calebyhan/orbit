# ORBIT — Training & Walk‑Forward Evaluation

*Last edited: 2025-11-05*

## Purpose

Define a **purged, rolling walk‑forward** procedure that trains heads + fusion on past data, tunes on a **validation slice**, and evaluates on a **held‑out test slice**, repeating across time to produce robust out‑of‑sample (OOS) metrics and artifacts.

---

## Split semantics

Configured via `training.split` in `orbit.yaml`:

* `train_months` — e.g., **12**
* `val_months` — e.g., **1**
* `test_months` — e.g., **1**
* `roll_step_months` — e.g., **1** (slide forward by this many months per window)

### Embargo (purge) rule

Because our label uses *t+1* prices, put a **1 trading‑day embargo** between train and val/test to avoid any label/feature adjacency effects. (Config: `embargo_days: 1`).

### Window diagram

```
|<----- train M ----->|<- val V ->|<- test T ->|
                      ^ embargo (1d)
then slide forward by roll_step_months and repeat
```

---

## Workflow per window (date range W)

1. **Assemble data**: load `features_daily` with aligned `labels` for dates ≤ end_of_test(W).
2. **Slice** into **train**, **val**, **test** using calendar months; apply the **embargo** gap.
3. **Fit heads** (price/news/social) on **train** only (hyperparams fixed or tuned on **val** within this window). Save artifacts to `models/heads/<modality>/<run_id>/W/`.
4. **Score heads** on **train/val/test**; optionally **calibrate** probabilities on **val** then apply to **val/test**.
5. **Fit fusion (gated blend)** parameters on **val** using head scores + gate inputs; save to `models/fusion/<run_id>/W/`.
6. **Score fusion** on **val/test** → `p_up_fused_t` (or `ret_fused_t`).
7. **Record metrics** on **val** and **test** (IC, AUC/Brier or RMSE, Sharpe via simple long/flat backtest within window).
8. **Persist predictions** for **test** to `data/scores/<run_id>/scores_W.parquet` with columns: `date, p_price, p_news, p_social, p_fused, label_*`.

Repeat for all windows; then **concat all test predictions** in chronological order to form the **full OOS series**.

---

## Randomness & reproducibility

* Set global seeds (`cfg.training.seed`) for GBM/MLP libraries and NumPy.
* Do **not** reshuffle time; keep deterministic month boundaries.
* Persist `metadata.json` per window with: commit hash (if available), config snapshot, feature list, library versions, run timestamps.

---

## Metrics captured

For **validation** and **test** in each window:

* **Classification**: `IC`, `AUC`, `Brier`, **hit‑rate** at decision threshold, **Sharpe** (long/flat, costs), **coverage**.
* **Regression**: `IC` (vs next returns), `RMSE`, `MAE`, **Sharpe**, **coverage**.
* **By regime** (optional): slice metrics by `rv_10d_spx` terciles and `news_count_z`/`post_count_z` deciles.

Aggregate across windows by **concatenating all test predictions** and recomputing metrics on the combined OOS series. Also report **per‑window** metrics for stability.

---

## Storage layout

```
models/
  heads/
    price/<run_id>/W/{model.pkl, calibrator.pkl?, metadata.json}
    news/<run_id>/W/{...}
    social/<run_id>/W/{...}
  fusion/
    <run_id>/W/{fusion_params.json, calibrator.pkl?, metadata.json}

data/scores/<run_id>/scores_W.parquet    # per-window predictions
reports/
  backtest/<run_id>/{window_*.json, oos_summary.json, plots/}
```

---

## CLI examples

Train/score a single window inferred from `--date`:

```sh
train:fit --date 2025-11-04 --run_id auto
score:daily --date 2025-11-04 --run_id <resolved>
```

Run the **full walk‑forward** over a historical span:

```sh
train:walkforward --start 2018-01-01 --end 2025-11-01 --run_id auto
```

---

## QC checks

* Embargo enforced (no overlapping rows between train and val/test within a window).
* Calibration fit only on **val**; applied to **val/test** (never train).
* Test predictions exist for every date in the test slice and **nowhere else**.
* OOS concatenation strictly retains chronological order; metrics recomputed on combined series match per‑window when segmented.

---

## Acceptance checklist

* The procedure yields a **single, contiguous OOS prediction series** built from concatenated **test** slices across windows.
* All artifacts are saved per window with complete metadata for reproducibility.
* Reported OOS metrics (IC/AUC/Brier/Sharpe/Drawdown/Hit‑rate/Coverage) are reproducible given the same config and seed.

---

## Related Files

* `08-modeling/hyperparams_tuning.md` — Hyperparameters
* `09-evaluation/acceptance_gates.md` — Training validation gates
* `10-operations/drift_monitoring.md` — Performance monitoring
