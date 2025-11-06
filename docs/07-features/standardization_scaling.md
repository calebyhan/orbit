# ORBIT — Standardization & Scaling

*Last edited: 2025-11-05*

## Purpose

Ensure features are on comparable scales and **point‑in‑time safe** by applying rolling standardization with strict warmup and clipping rules.

## Principles

* **Rolling windows** only (no full‑sample statistics).
* **Warmup NA**: a feature remains **NA** until enough past observations exist.
* **Clipping**: reduce tail sensitivity while keeping order statistics.
* **Deterministic**: same inputs + seed ⇒ same outputs.

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
