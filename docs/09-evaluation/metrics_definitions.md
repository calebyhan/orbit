# ORBIT — Metrics & Definitions

*Last edited: 2025-11-05*

## Return series

* Use **strategy daily net returns** after costs per the chosen execution variant.
* Equity curve compounds net returns from an initial equity of 1.0.

## Core metrics

* **IC (Spearman)**: rank correlation between `fused_score_t` and next-day label (return or excess return).
* **AUC (classification)**: area under ROC using `fused_score_t` vs `label_updown`.
* **Brier score**: mean squared error of probabilities vs `label_updown`.
* **Sharpe (annualized)**: `mean(ret_net_daily) / std(ret_net_daily) * sqrt(252)`.
* **Max Drawdown**: maximum peak-to-trough equity decline over the test/OOS series.
* **Hit Rate**: fraction of days with `ret_net_daily > 0` **while in a trade**.
* **Coverage**: fraction of days **in position** (position_t > 0).

## Reporting slices

* **By regime**: terciles of `rv_10d_spx`; deciles of `news_count_z` and `post_count_z`.
* **By month/quarter**: rolling IC, Sharpe, and coverage.

## Acceptance checklist

* Metrics computed on the **OOS concatenated** series (see `08-modeling/training_walkforward.md`).
* Report includes both overall and sliced metrics with consistent sample sizes.

---

## Related Files

* `01-overview/success_criteria.md` — Success thresholds
* `09-evaluation/backtest_long_flat_spec.md` — Backtest metrics
* `09-evaluation/dashboard_spec.md` — Metric visualization
