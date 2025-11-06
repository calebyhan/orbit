# ORBIT — Price Features (Daily)

*Last edited: 2025-11-05*

## Purpose

Define deterministic, leak‑free **daily features** derived from Stooq OHLCV for SPY/VOO and the index (^SPX). These features are computed at the **end of day T** and used to predict **T+1**.

## Inputs

* `data/curated/prices/` with columns: `date, symbol, open, high, low, close, volume`
* Symbols required: `SPY.US`, `VOO.US`, `^SPX`
* Trading calendar aligned to ET (see `06-preprocessing/time_alignment_cutoffs.md`).

## Output (to features row)

All fields are **per trading day T** and **z‑scored later** (see `standardization_scaling.md`).

| Field            | Formula / Definition                      | Notes                                       |
| ---------------- | ----------------------------------------- | ------------------------------------------- |
| `ret_1d_spy`     | `(close_t / close_{t-1}) - 1`             | simple return                               |
| `overnight_spy`  | `(open_t / close_{t-1}) - 1`              | gap return                                  |
| `intraday_spy`   | `(close_t / open_t) - 1`                  |                                             |
| `mom_5d_spy`     | `(close_t / close_{t-5}) - 1`             | momentum                                    |
| `mom_20d_spy`    | `(close_t / close_{t-20}) - 1`            | momentum                                    |
| `rev_1d_spy`     | `-ret_1d_spy`                             | 1‑day reversal proxy                        |
| `rv_10d_spy`     | `sqrt(252) * stdev(ret_1d_spy, 10)`       | annualized realized vol                     |
| `atrp_14d_spy`   | `ATR(14) / close_t`                       | average true range %                        |
| `drawdown_spy`   | `(close_t / rolling_max(close, 252)) - 1` | since 52‑week high                          |
| `vol_z_60d_spy`  | `zscore(volume, 60)`                      | volume pressure                             |
| `basis_spy_spx`  | `ret_1d_spy - ret_1d_spx`                 | ETF–index basis (excess)                    |
| `mom_5d_spx`     | `(spx_close_t / spx_close_{t-5}) - 1`     | index momentum (for excess labels)          |
| `rv_10d_spx`     | `sqrt(252) * stdev(ret_1d_spx, 10)`       | index vol regime                            |
| `term_struc_vol` | `rv_10d_spy - rv_20d_spy`                 | short vs medium vol (requires `rv_20d_spy`) |

> **ATR(14)** uses standard Wilder’s smoothing on True Range: `TR_t = max(high_t − low_t, |high_t − close_{t-1}|, |low_t − close_{t-1}|)`.

## Anti‑leak rules

* Use only **prices up to and including the close of T**.
* Labels target **T+1** (see `08-modeling/targets_labels.md`).
* No forward‑filled values beyond available history windows.

## NA / window rules

* Features with lookback **N** are **NA** for the first `N` valid rows. Do **not** forward‑fill.
* Downstream standardization handles NA by **leaving as NA**; modelers should drop rows with insufficient history in each rolling window.

## Pseudocode (reference)

```python
df = prices.query("symbol == 'SPY.US'").sort_values('date').assign(
    ret_1d_spy = df.close.pct_change(),
    overnight_spy = df.open.div(df.close.shift(1)).sub(1.0),
    intraday_spy = df.close.div(df.open).sub(1.0),
    mom_5d_spy = df.close.div(df.close.shift(5)).sub(1.0),
    mom_20d_spy = df.close.div(df.close.shift(20)).sub(1.0),
    rev_1d_spy = lambda x: -x.ret_1d_spy,
)
rv10 = df.ret_1d_spy.rolling(10).std() * (252 ** 0.5)
df['rv_10d_spy'] = rv10
tr = np.maximum.reduce([
    df.high - df.low,
    (df.high - df.close.shift(1)).abs(),
    (df.low - df.close.shift(1)).abs(),
])
atr14 = wilder_ema(tr, 14)
df['atrp_14d_spy'] = atr14 / df.close
roll_max = df.close.rolling(252).max()
df['drawdown_spy'] = df.close.div(roll_max).sub(1.0)
df['vol_z_60d_spy'] = zscore(df.volume, 60)
# join ^SPX returns for basis
spx = prices.query("symbol == '^SPX'").sort_values('date')
spx['ret_1d_spx'] = spx.close.pct_change()
df = df.merge(spx[['date','ret_1d_spx','close']].rename(columns={'close':'spx_close'}), on='date')
df['basis_spy_spx'] = df.ret_1d_spy - df.ret_1d_spx
```

## Acceptance checklist

* All formulas are computable from Stooq OHLCV without external data.
* First‑N rows for each rolling feature are **NA** (no look‑ahead).
* `basis_spy_spx` uses same‑day returns (T) and **not** future values.
* Output integrates cleanly into the single **features row per day**.

---

## Related Files

* `04-data-sources/stooq_prices.md` — Price data source
* `12-schemas/prices.parquet.schema.md` — Price schema
* `07-features/standardization_scaling.md` — Feature normalization
* `08-modeling/heads_price_news_social.md` — Price model head
