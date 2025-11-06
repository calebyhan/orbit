# ORBIT — Report Templates

*Last edited: 2025-11-05*

## Files

* `reports/backtest/<run_id>/summary.json`
* `reports/backtest/<run_id>/equity_curve.parquet`
* `reports/ablations/<run_id>/*.json`
* `reports/regimes/<run_id>/*.json`

## summary.json (example schema)

```json
{
  "run_id": "UUID",
  "oos_span": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "variant": "overnight",
  "threshold": 0.55,
  "metrics": {
    "IC": 0.018,
    "AUC": 0.556,
    "Brier": 0.242,
    "Sharpe": 0.48,
    "MaxDrawdown": -0.07,
    "HitRate": 0.55,
    "Coverage": 0.43
  },
  "costs_bps_per_side": 2,
  "slippage_bps_per_side": 2,
  "notes": "Gated fusion improves over price-only on high-burst news days."
}
```

## Equity curve table

Columns: `date, position, ret_gross, costs_bps, ret_net, equity`.

## Plots (recommended)

* Equity curve vs buy/hold (normalized)
* Rolling 60d Sharpe
* Rolling monthly IC
* Precision–recall & reliability (classification)
* Threshold sweep (Sharpe vs threshold; coverage vs threshold)
* Regime bars (vol terciles; news/social deciles)

## Acceptance checklist

* All files present; plots reflect the selected execution variant and costs.
* Threshold sweep and regime breakdowns included alongside overall metrics.

---

## Related Files

* `09-evaluation/dashboard_spec.md` — Dashboard structure
* `09-evaluation/metrics_definitions.md` — Reported metrics
* `09-evaluation/regime_analysis.md` — Regime breakdowns
