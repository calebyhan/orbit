# ORBIT — Risk Controls

*Last edited: 2025-11-05*

## Purpose

Define guardrails that keep behavior sane during outages, data gaps, or extreme conditions.

## Controls (v1 suggestions)

1. **Flatten on missing data**
   If curated text is missing for *T* and `flatten_on_missing_data: true`, set `position_t = 0` unless price-only mode is allowed by config.

2. **Text outage dampener**
   If news/social counts are zero due to connector failure, suppress gate activations so fusion defaults toward the price head.

3. **Max exposure**
   `position_t ∈ {0,1}` (no leverage). If proportional sizing is enabled, cap at `1.0`.

4. **Daily loss kill-switch (optional)**
   If `ret_net_t < -X bps` on the day, enforce `position_{t+1}=0` for one cooldown day. (X e.g., 150 bps)

5. **Volatility regime cap (optional)**
   If `rv_10d_spx` > 95th percentile of its history, raise the long threshold by `+0.02` to reduce trades in stressed regimes.

6. **Duplicate trade filter**
   Ignore intra-day flapping (not applicable on daily cadence). Enforce **once-per-day** trade limit.

7. **Data sanity checks**
   If any feature is NaN/inf on *T*, either impute to neutral (0) or skip scoring for *T* according to `on_feature_nan`.

## Config (example)

```yaml
risk:
  flatten_on_missing_data: true
  kill_switch_bps: 150
  vol_cap_percentile: 95
  addl_threshold_in_high_vol: 0.02
  once_per_day_trade: true
  on_feature_nan: "skip"   # or "neutral"
```

## Logging & audit

* Log which control(s) fired per day with a short reason code.
* Write a daily `risk_flags.parquet` with: `date, missing_text, high_vol, kill_switch, nan_features, reason`.

## Acceptance checklist

* Risk controls are deterministic and read only from **same-day** information.
* Backtest and live scoring both record control triggers for audit.
* Strategy never violates configured max exposure or trade frequency.

---

## Related Files

* `09-evaluation/backtest_rules.md` — Risk application
* `09-evaluation/thresholds_position_sizing.md` — Position limits
* `10-operations/failure_modes_playbook.md` — Risk breaches
