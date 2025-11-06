# ORBIT — Backtest Rules

*Last edited: 2025-11-05*

## Purpose

Simulate a **long/flat** strategy on SPY/VOO using the daily fused score, with explicit execution prices, costs, and holding rules.

## Variants (pick one in config)

* **Overnight (default for v1)** — aligns with `labels.trade_at = next_open` **labels**:

  * **Entry:** at **Close_t** if `signal_t == long`
  * **Exit:** at **Open_{t+1}`**
  * Realized return: `Open_{t+1}/Close_t - 1`
  * Requires decision ready **before 16:00 ET**. Our 15:30 cutoff supports this; in live, schedule pre-close.
* **Intraday-next** — if you prefer not to hold overnight:

  * **Entry:** at **Open_{t+1}`**
  * **Exit:** at **Close_{t+1}`**
  * Realized return: `Close_{t+1}/Open_{t+1} - 1`
  * If you choose this, **set labels accordingly** (see `08-modeling/targets_labels.md`).

> The docs and sample config assume the **Overnight** variant unless you explicitly switch.

## Signal & state

* Daily `fused_score_t` → **Signal_t** via rules in `thresholds_position_sizing.md`
* Positions are **binary** (1 = long, 0 = flat) for v1.

## Cash & compounding

* Strategy equity evolves by compounding **net daily returns after costs**.
* Start equity = 1.0.

## Holidays & missing data

* If `Open_{t+1}` (or `Close_{t+1}` for intraday) is missing (holiday), **no trade**; carry flat PnL for that gap.

## Output artifacts

* `reports/backtest/<run_id>/equity_curve.parquet`:

  * `date, position, ret_gross, costs_bps, ret_net, equity`
* `reports/backtest/<run_id>/summary.json` (key metrics)

## Acceptance checklist

* Execution prices are consistent with the chosen variant and labels.
* Costs applied per trade direction (both entry and exit).
* Equity curve has no look-ahead joins and no missing price-induced NaNs.

---

## Related Files

* `09-evaluation/backtest_long_flat_spec.md` — Strategy specification
* `09-evaluation/transaction_costs_slippage.md` — Cost model
* `09-evaluation/risk_controls.md` — Risk limits
