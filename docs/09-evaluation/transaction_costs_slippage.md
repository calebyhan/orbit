# ORBIT — Transaction Costs & Slippage

*Last edited: 2025-11-05*

## Purpose

Apply realistic **per-side costs** and **slippage** in basis points (bps) when trades occur.

## Definitions

* **bps:** basis points, `1 bps = 0.0001`.
* **Per-side cost:** applied **each** time you change position (enter or exit).
* **Round-trip:** two sides (enter + exit).

## Parameters (from config)

```yaml
backtest:
  execution:
    trade_at: next_open   # or next_close, see backtest_rules.md
    costs_bps_per_side: 2
    slippage_bps_per_side: 2
```

## Cost model

* On a **trade day** (position changes 0→1 or 1→0), net return is:

```
ret_net = ret_gross - ((costs_bps_per_side + slippage_bps_per_side) * sides_executed) / 10000
```

* Overnight variant long day (Close_t → Open_{t+1}):

  * If **enter** at Close_t (0→1) and **exit** at Open_{t+1} (1→0), `sides_executed = 2`.
* Days with **no position change** incur **0** additional costs.

## Examples

* 2 bps cost + 2 bps slippage per side ⇒ **4 bps per side**; **8 bps round-trip**.

## Acceptance checklist

* Costs

---

## Related Files

* `09-evaluation/backtest_long_flat_spec.md` — Cost application
* `09-evaluation/thresholds_position_sizing.md` — Position sizing
* `01-overview/assumptions_constraints.md` — Cost assumptions
