# ORBIT — Targets & Labels

*Last edited: 2025-11-06*

## Purpose

Define leak‑free **prediction targets** and **label construction** for daily S&P tracker forecasting. Labels are derived deterministically from curated prices and respect ORBIT’s cutoff rules.

---

## Prediction tasks

We support **one active task at a time** (set in `labels.target`):

1. **Classification (default)** — predict the probability the next session’s return is **positive**.
2. **Regression** — predict the **next session return** (bps), optionally on an **excess** basis vs ^SPX.

> Classification is recommended for v1; it is robust and maps directly to long/flat decisions.

---

## Base returns

Let $P_t$ be the selected price for day *t* (see **Execution price**), and define simple returns:

* **ETF return:** $r^{ETF}_{t+1} = \frac{P_{t+1}}{P_t} - 1$
* **Index return:** $r^{SPX}_{t+1} = \frac{I_{t+1}}{I_t} - 1$ where `I_t` is ^SPX close.
* **Excess return:** $r^{EX}_{t+1} = r^{ETF}_{t+1} - r^{SPX}_{t+1}$

The choice of **ETF** for training is `SPY.US`; we validate on `VOO.US` for out‑of‑sample sanity.

---

## Execution price (label alignment)

The label horizon and price points must match the backtest execution rule (`backtest.execution.trade_at`):

* `next_open`: $P_t = \text{Close}_t, P_{t+1} = \text{Open}_{t+1}$
* `next_close`: $P_t = \text{Close}_t, P_{t+1} = \text{Close}_{t+1}$

> ORBIT defaults to **next_open** to avoid using any information from day *t+1* intraday text; only prices are used.

### Label Availability Timing

Labels become available for computing IC (Information Coefficient) and drift monitoring at the following times:

* **Overnight variant (`next_open`):** Labels available at **9:35 AM ET on T+1** (5 minutes after market open for price stabilization)
* **Intraday-next variant (`next_close`):** Labels available at **4:05 PM ET on T+1** (5 minutes after market close for final settlement)

**Operational Impact:**
* IC metrics for day *T* can be computed and logged starting at the label availability time
* Drift monitoring (`drift_monitoring.md`) schedules IC checks based on execution variant + regime
* Walk-forward retraining can access labels up to *T−1* only when training on day *T*

**Example Timeline (next_open):**
```
Day T:   15:30 ET → Cutoff, features locked, model scores
Day T:   16:00 ET → Market close
Day T+1: 09:30 ET → Market open
Day T+1: 09:35 ET → Label for T now available, compute IC(score_T, label_T)
```

---

## Label definitions

### 1) Classification

* **Direction (ETF):** $y_{t}^{clf} = \mathbb{1}\{r^{ETF}_{t+1} > 0\}$
* **Direction (Excess):** if `labels.use_excess: true`, then $y_{t}^{clf} = \mathbb{1}\{r^{EX}_{t+1} > 0\}$

### 2) Regression

* **Raw return (ETF):** $y_{t}^{reg} = r^{ETF}_{t+1}$
* **Excess return:** if `labels.use_excess: true`, use $y_{t}^{reg} = r^{EX}_{t+1}$
* Store both **decimal** and **bps** (`*10000`) for convenience.

All labels are stored alongside the features row as `label_updown` (0/1) and/or `label_ret` (float), with a `label_basis ∈ {ETF, EXCESS}` tag.

---

## Anti‑leak guarantees

* Labels for day *t* depend **only** on the chosen prices at *t* and *t+1*; no text or revised data from *t+1* is used in features.
* Text membership for day *t* is `(t−1 15:30, t 15:30]` ET; labels use **only** prices beyond *t*.
* All time series joins are **by date** on trading days after ET normalization.

---

## Missing data & market holidays

* If either `P_t` or `P_{t+1}` is missing (holiday/closure), **no label** is produced for *t*; the features row for that *t* should also be absent.
* If curated text exists but prices are missing, drop the day; do not forward‑fill labels.

---

## Optional transformations (disabled by default)

* **Winsorization (labels only):** clip regression labels to ±300 bps to reduce tail impact during training. Keep unclipped copies for evaluation.
* **Class weighting:** for classification, use balanced class weights if the up/down split is highly imbalanced on short windows.

---

## Pseudocode (reference)

```python
# prices: curated daily table with columns date, symbol, open, close
spy = prices[prices.symbol == 'SPY.US'].sort_values('date').copy()
spx = prices[prices.symbol == '^SPX'].sort_values('date').copy()

if cfg.backtest.execution.trade_at == 'next_open':
    p_t   = spy['close']
    p_t1  = spy['open'].shift(-1)
    i_t   = spx['close']
    i_t1  = spx['open'].shift(-1)
else:  # next_close
    p_t   = spy['close']
    p_t1  = spy['close'].shift(-1)
    i_t   = spx['close']
    i_t1  = spx['close'].shift(-1)

ret_etf = p_t1.div(p_t).sub(1.0)
ret_spx = i_t1.div(i_t).sub(1.0)
ret_ex  = ret_etf.sub(ret_spx)

use_excess = cfg.labels.use_excess

# classification
y_clf = (ret_ex if use_excess else ret_etf).gt(0).astype('Int8')
# regression
y_reg = (ret_ex if use_excess else ret_etf).astype('float64')

labels = pd.DataFrame({
    'date': spy['date'],
    'label_updown': y_clf,
    'label_ret': y_reg,              # decimal
    'label_ret_bps': (y_reg * 10000).round(1),
    'label_basis': 'EXCESS' if use_excess else 'ETF',
})
```

---

## Acceptance checklist

* Label construction respects `trade_at` alignment and produces **no leaks**.
* Missing trading days yield **no labels** (and no features rows).
* Labels are joined to features by **date** with consistent calendars.
* `label_basis` correctly reflects `labels.use_excess` in config.

---

## Related Files

* `06-preprocessing/time_alignment_cutoffs.md` — Label timing
* `09-scoring-backtest/backtest_rules.md` — Execution variants
* `10-operations/drift_monitoring.md` — IC computation schedule
* `12-schemas/features_daily.parquet.schema.md` — Label columns
