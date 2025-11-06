# ORBIT — Backtest: Long/Flat Specification

*Last edited: 2025-11-05*

## Purpose

Define the complete specification for simulating a **long/flat** strategy on SPY/VOO using the daily fused score. This is the primary evaluation method for ORBIT v1.

---

## Strategy Overview

* **Universe:** SPY or VOO (single asset)
* **Positions:** Long (1.0) or Flat (0.0). No shorting in v1.
* **Rebalance frequency:** Daily at market close or next open (see variants below)
* **Signal:** Daily `fused_score_t` from the gated fusion model
* **Decision rule:** If `score_t > τ` → Long, else Flat

---

## Execution Variants

### Variant 1: Overnight (default for v1)

* **Signal generation:** End of day T (before 16:00 ET close)
* **Entry:** Close_T (if signal says long)
* **Exit:** Open_{T+1}
* **Return captured:** Overnight return = `(Open_{T+1} / Close_T) - 1`
* **Label alignment:** Must match `targets_labels.md` with `trade_at = next_open`

**Pros:**  
- Decision can be made after 15:30 ET cutoff but before close  
- Captures overnight gap moves (often driven by after-hours news)

**Cons:**  
- Overnight risk exposure

### Variant 2: Intraday-Next

* **Signal generation:** End of day T
* **Entry:** Open_{T+1}
* **Exit:** Close_{T+1}
* **Return captured:** Intraday return = `(Close_{T+1} / Open_{T+1}) - 1`
* **Label alignment:** Must match `targets_labels.md` with `trade_at = next_close`

**Pros:**  
- No overnight exposure  
- Simpler execution in live setting

**Cons:**  
- Misses overnight moves (which may be where edge is)

> **Default:** ORBIT v1 uses **Variant 1 (Overnight)** to maximize signal utility from news/social published before cutoff.

---

## Trade Logic (Pseudocode)

```python
for t in trading_days:
    # Get signal from model
    score_t = fused_score[t]
    
    # Decision rule (see thresholds_position_sizing.md)
    if score_t > threshold_long:
        position_t = 1.0  # Long
    else:
        position_t = 0.0  # Flat
    
    # Execution (Overnight variant)
    if position_t == 1.0:
        entry_price = close[t]
        exit_price = open[t+1]
        gross_return = (exit_price / entry_price) - 1
        
        # Apply costs (see transaction_costs_slippage.md)
        costs_bps = cost_per_side_bps * 2  # Entry + exit
        net_return = gross_return - (costs_bps / 10000)
    else:
        net_return = 0.0
    
    # Update equity
    equity[t+1] = equity[t] * (1 + net_return)
```

---

## Transaction Costs

* **Base cost:** 1–3 bps per side (configurable in `orbit.yaml`)
* **Applied:** Both on entry and exit
* **Total cost per round-trip:** 2–6 bps
* See `transaction_costs_slippage.md` for detailed cost model

**Example:**  
- cost_per_side_bps = 2  
- Round-trip cost = 4 bps = 0.04%  
- Gross return = 0.5% → Net return = 0.5% - 0.04% = 0.46%

---

## Thresholds & Position Sizing

* **Threshold (τ):** Minimum score to enter long position (default: 0.55 for probability, 0.001 for expected return)
* **Position sizing:** Binary (0 or 1) in v1. Future versions may add fractional sizing based on confidence.
* See `thresholds_position_sizing.md` for tuning methodology

---

## Handling Missing Data

* **Missing prices:** If `Open_{t+1}` or `Close_t` is NaN (e.g., holiday), skip that day entirely
* **Missing signal:** If `fused_score_t` is NaN (e.g., ingestion failure), **default to flat** (risk-off)
* Log all missing data events to `logs/backtest_<run_id>.log`

---

## Risk Controls

* **Max position:** 1.0 (100% long or 0% flat). No leverage in v1.
* **Drawdown monitoring:** Track rolling max drawdown; flag if exceeds -25%
* **Volatility check:** If realized vol > 2× trailing 60d avg, consider flattening (optional, see `risk_controls.md`)

See `risk_controls.md` for detailed risk management rules.

---

## Output Artifacts

### 1. Equity Curve (Parquet)

**Path:** `reports/backtest/<run_id>/equity_curve.parquet`

**Schema:**
```
date: date
position: float64  # 0.0 or 1.0
score: float64     # fused_score_t
threshold: float64 # threshold used
entry_price: float64
exit_price: float64
ret_gross: float64
costs_bps: float64
ret_net: float64
equity: float64
```

### 2. Summary Metrics (JSON)

**Path:** `reports/backtest/<run_id>/summary.json`

**Contents:**
```json
{
  "strategy": "long_flat_overnight",
  "asset": "SPY",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "total_days": 1258,
  "trading_days": 945,
  "coverage": 0.68,
  "total_return": 0.42,
  "annualized_return": 0.084,
  "annualized_volatility": 0.145,
  "sharpe_ratio": 0.58,
  "max_drawdown": -0.18,
  "hit_rate": 0.54,
  "avg_win": 0.008,
  "avg_loss": -0.007,
  "win_loss_ratio": 1.14,
  "turnover_annual": 180
}
```

### 3. Daily Metrics (Parquet)

**Path:** `reports/backtest/<run_id>/daily_metrics.parquet`

**Schema:**
```
date: date
ret_net: float64
equity: float64
drawdown: float64  # From running max
```

---

## Acceptance Checklist

* [ ] Execution variant clearly specified in config and code
* [ ] Labels in training match execution variant (overnight vs intraday)
* [ ] Costs applied on both entry and exit
* [ ] Missing data handled gracefully (flat position + logging)
* [ ] Equity curve has no look-ahead bias (all joins respect point-in-time)
* [ ] Output artifacts written to `reports/backtest/<run_id>/`
* [ ] Summary metrics match manual spot-checks on 3-5 sample days

---

## Comparison to Buy-and-Hold

Every backtest report should include a **benchmark comparison:**

* **Benchmark:** Buy-and-hold SPY from start to end
* **Comparison metrics:** Total return, Sharpe, max DD, volatility
* **Goal:** Strategy should show positive risk-adjusted alpha (higher Sharpe) and/or lower drawdown

---

## Example Configuration

```yaml
backtest:
  variant: overnight  # or 'intraday_next'
  threshold_long: 0.55
  cost_per_side_bps: 2.0
  flatten_on_missing_data: true
  risk_controls:
    max_drawdown_pct: 25.0
    vol_multiplier_flatten: 2.0
```

---

## Related Files

* `backtest_rules.md` — High-level backtest rules (this spec elaborates)
* `thresholds_position_sizing.md` — How to set and tune thresholds
* `transaction_costs_slippage.md` — Detailed cost model
* `risk_controls.md` — Risk management rules
* `metrics_definitions.md` — How metrics are calculated

---

