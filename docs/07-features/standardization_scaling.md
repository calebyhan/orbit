# ORBIT — Standardization & Scaling

*Last edited: 2025-11-06*

## Purpose

Ensure features are on comparable scales and **point‑in‑time safe** by applying rolling standardization with strict warmup and clipping rules.

## Principles

* **Rolling windows** only (no full‑sample statistics).
* **Warmup NA**: a feature remains **NA** until enough past observations exist.
* **Clipping**: reduce tail sensitivity while keeping order statistics.
* **Deterministic**: same inputs + seed ⇒ same outputs.
* **Strict lookback discipline**: Windows never include the current day to prevent data leakage.

---

## Anti-Leak Window Discipline

**Critical Rule:** When computing rolling z-scores for day T, the window must be **EXCLUSIVE** of day T itself.

**Correct Window:**
- For day T with 60-day window: Use days [T-60, T-1] (inclusive of T-1, exclusive of T)
- Formula: `window = [T - window_days, T - 1]`

**Example:**
```python
# Computing z-score for day 253 with 60-day window
# CORRECT: Use days 193-252 (60 days before day 253)
# WRONG: Use days 194-253 (includes current day - LEAKAGE)
# WRONG: Use days 1-252 (full history - wrong window size)
```

**Why This Matters:**
Including day T in its own z-score computation creates **subtle data leakage** because:
1. The current day's value influences its own standardization
2. Extreme values on day T would appear "less extreme" in their own z-score
3. This inflates backtest performance metrics artificially

**Implementation:**
```python
def zscore_rolling(series, window=60, clip=4.0):
    # Shift by 1 ensures we only use T-1 and earlier
    mu = series.shift(1).rolling(window).mean()
    sigma = series.shift(1).rolling(window).std(ddof=0)
    z = (series - mu) / sigma
    z = z.where((mu.notna()) & (sigma > 0))
    return z.clip(-clip, clip)
```

**Walk-Forward Training Context:**
- Training window: Days 1-252
- Validation window: Days 253-273
- Test window: Days 274-294

When computing features for validation day 253:
- ✅ **Correct:** Z-score uses days 193-252 (60 days ending at 252)
- ❌ **Wrong:** Z-score uses days 193-253 (includes current day)
- ❌ **Wrong:** Z-score uses days 1-252 (full training window, wrong size)

This discipline applies to **all rolling statistics**: z-scores, moving averages, rolling volatility, etc.

---

## Procedure

For each numeric feature `x_t` (excluding binary flags and already‑bounded ratios):

1. Choose window length `W` (default **60 trading days**) from config.
2. Compute rolling mean and std **using only t−W … t−1** (exclude `t`).
3. Standardize:
   `z_t = (x_t − mean_{t−1,W}) / std_{t−1,W}` if both moments exist; else `z_t = NA`.
4. **Clip** `z_t` to `[-clip_sigma, +clip_sigma]` (default **±4σ**).

## Exceptions

* Do **not** z‑score: counts already converted to `*_count_z`, binary flags, gate aliases, and variables constrained to [0,1] or [−1,1] that are already interpreted on an absolute scale.
* For volatility features (e.g., `rv_10d`), consider log transform before z‑scoring if heavy‑tailed.

## Implementation notes

* Use `rolling(window=W, min_periods=W)` with **closed='left'** in libraries that support it; otherwise index shift by 1.
* Keep both the **raw** and the **z‑scored** columns in `features_daily` when informative (name with `_z`).
* Persist the **exact W and clip_sigma** used in `models/metadata.json` for reproducibility.

## Pseudocode

```python
def zscore_rolling(series, window=60, clip=4.0):
    mu = series.shift(1).rolling(window).mean()
    sigma = series.shift(1).rolling(window).std(ddof=0)
    z = (series - mu) / sigma
    z = z.where((mu.notna()) & (sigma > 0))
    return z.clip(-clip, clip)
```

## QC & logging

* Count NA rates per feature; ensure warmup behavior is expected.
* Verify no look‑ahead by checking that z‑scores for day *t* are unchanged when you extend the data by future rows.
* **Lookback validation test:** Compute z-score for day T with data through T+10; verify z-score(T) is identical when recomputed with data through T only.
* Monitor feature distributions monthly for drift; adjust W/clip if necessary.

## Acceptance checklist

* Rolling standardization uses **past‑only** windows.
* Warmup NA and clipping rules are enforced with no forward‑fill.
* Feature columns are clearly named, and exceptions documented.

---

## Related Files

* `07-features/price_features.md` — Price feature scaling
* `07-features/news_features.md` — News feature scaling
* `07-features/social_features.md` — Social feature scaling
* `12-schemas/features_daily.parquet.schema.md` — Feature schema
