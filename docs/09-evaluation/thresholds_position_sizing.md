# ORBIT — Thresholds & Position Sizing

*Last edited: 2025-11-05*

## Purpose

Turn `fused_score_t` into a daily **long/flat signal** and an optional **position size**.

## Modes

### 1) Fixed threshold (v1 default; classification)

* If `fused_score_t > 0.55` ⇒ **long**; else **flat**.
* Tune via validation; sweep 0.50–0.65 in 0.01 steps in reports.

### 2) Coverage targeting (classification)

* Choose a desired **coverage** (e.g., 40% of days long).
* Use the rolling quantile `q_{1-coverage}` on the last N=120 trading days to set a **dynamic threshold**.

### 3) Regression cut (optional)

* If using regression fusion: go **long** when `E[r_{t+1}] > min_expected_bps` (e.g., 3 bps).

## Position sizing (optional)

* v1: **binary** (1 or 0).
* Optional proportional sizing:

  * `size_t = clip( (fused_score_t - τ) / κ, 0, 1 )`
  * Use small κ (e.g., 0.1) with caps and add **position inertia** to reduce churn.

## Inertia / cooldown (optional)

* Require the signal to stay above threshold for **K** consecutive days (e.g., K=2) before entering; symmetric for exit.

## Pseudocode

```python
def signal_and_size(fused, mode='fixed', tau=0.55, kappa=0.1, K=1,
                    coverage=None, history=None, min_expected_bps=None):
    if mode == 'coverage':
        tau = rolling_quantile(history['fused'], q=1-coverage, window=120)
    elif mode == 'regression':
        tau = min_expected_bps / 10000.0  # convert bps to decimal if needed

    raw_long = fused > tau
    long_k = consecutive_days_above(fused, tau) >= K
    long_sig = raw_long and long_k

    size = 1.0 if long_sig else 0.0
    if kappa is not None and kappa > 0:
        size = clip((fused - tau) / kappa, 0.0, 1.0) if long_sig else 0.0
    return long_sig, size
```

## Acceptance checklist

* Chosen thresholding mode is logged and reproducible.
* For coverage targeting, the quantile window excludes **future** days.
* If sizing is used, caps and inertia are documented and implemented.

---

## Related Files

* `09-evaluation/backtest_long_flat_spec.md` — Threshold usage
* `09-evaluation/risk_controls.md` — Position limits
* `09-evaluation/transaction_costs_slippage.md` — Cost impact
