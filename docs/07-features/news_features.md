# ORBIT — News Features (Daily)

*Last edited: 2025-11-06*

## Purpose

Turn curated Alpaca news (by day *T*, cutoff **15:30 ET**) into deterministic daily features that capture **intensity**, **novelty**, and **polarity**, without leaking future information.

## Inputs

From `data/curated/news/` (see 04‑data‑sources & 06‑preprocessing). Required columns for day *T*:

* `date: date`
* `count: int`
* `count_z: float` (vs 60‑day history)
* `novelty: float` (mean ∈ [0,1])
* `sent_mean: float` (Gemini mean in [−1,1])
* `sent_max: float` (per‑day max in [−1,1])
* `source_weighted_mean: float` (optional)
* `last_item_ts: timestamp[ns, UTC]` (latest `published_at` ≤ 15:30 ET)
* `ingestion_complete: bool` (True if full day captured without gaps)
* `ingestion_gaps_minutes: int` (Total minutes of known disconnection)

> All curated values must be computed **only** from items with `published_at ≤ 15:30 ET` on day *T* (point‑in‑time discipline).

## Output fields (added to the single features row for *T*)

All features are later standardized per `standardization_scaling.md`.

| Feature               | Definition                                                       | Domain / Notes                   |
| --------------------- | ---------------------------------------------------------------- | -------------------------------- |
| `news_count`          | copy of curated `count`                                          | `≥ 0`                            |
| `news_count_z`        | copy of curated `count_z`                                        | clip to [−5, +5] before modeling |
| `news_presence`       | `1{news_count > 0}`                                              | {0,1}                            |
| `news_burst`          | `max(0, news_count_z − 1.5)`                                     | highlights unusually busy days   |
| `news_novelty`        | copy of curated `novelty`                                        | [0,1]; higher = more novel       |
| `news_sent_mean`      | copy of curated mean sentiment                                   | clamp to [−1,1]                  |
| `news_sent_abs_mean`  | `abs(news_sent_mean)`                                            | [0,1]                            |
| `news_sent_max`       | copy of curated max sentiment                                    | clamp to [−1,1]                  |
| `news_recency_min`    | minutes between **cutoff** (15:30 ET) and `last_item_ts` (in ET) | `≥ 0` (0 if no news)             |
| `news_data_quality`   | `max(0, 1 - ingestion_gaps_minutes/360)`                         | [0,1]; 1.0 if complete, 0.5 if 3h gaps |
| `gate_news_intensity` | alias of `news_burst`                                            | used by fusion gate              |
| `gate_news_novelty`   | alias of `news_novelty`                                          | used by fusion gate              |

### Optional (if available in curated table)

| Feature                     | Definition                                                      |
| --------------------------- | --------------------------------------------------------------- |
| `news_source_weighted_mean` | copy of `source_weighted_mean` (provider credibility weighting) |
| `news_sent_trend_3d`        | 3‑day change in `news_sent_mean` (requires lagged values)       |

## NA / defaults

* If `news_count == 0`: set `news_sent_* = 0`, `news_novelty = 0`, `news_recency_min = 0`, and `news_presence = 0`.
* Z‑scores (like `news_count_z`) are **NA** during warmup until the 60‑day standardization window is available; do **not** forward‑fill.

## Data Quality Handling

**Purpose:** Handle partial-day data captures from WebSocket outages.

**Data Quality Score:**
```python
news_data_quality = max(0, 1 - ingestion_gaps_minutes / 360)
# 360 minutes = 6 hours (full trading day expectation)
# Examples:
#   0 gaps → quality = 1.0 (perfect)
#   30 min gaps → quality = 0.92 (excellent)
#   180 min gaps → quality = 0.5 (poor)
#   360+ min gaps → quality = 0.0 (unusable)
```

**Handling Rules:**

**If `news_data_quality < 0.5` (>3 hours of gaps):**
- Treat as missing day
- Set all news features to 0: `news_count=0`, `news_sent_mean=0`, `news_novelty=0`
- Set `news_presence=0`
- Log warning: "News data incomplete for day T (quality={quality})"

**If `0.5 ≤ news_data_quality < 1.0` (some gaps but usable):**
- Include `news_data_quality` as feature (model can learn reliability patterns)
- Keep computed features but flag as partial
- Log info: "News data partially complete for day T (quality={quality})"

**If `news_data_quality == 1.0` (no gaps):**
- Normal processing
- `news_data_quality` feature still included for model consistency

**Model Usage:**
The `news_data_quality` feature allows the model to:
- Down-weight predictions when data quality is lower
- Learn that partial-data days are less reliable
- Distinguish between "genuinely quiet news day" vs "data capture issue"

## Clipping & caps

* Clip any z‑scores to **[−5, +5]**.
* Clamp sentiments to **[−1, 1]** before downstream use.

## Anti‑leak rules

* Use **only** curated records with `published_at ≤ 15:30 ET` for day *T*.
* `news_recency_min` must compute `cutoff_ET(T) − last_item_ts_ET` (never from after 15:30 events).

## Pseudocode (reference)

```python
row = curated_news.loc[curated_news.date == T].squeeze()
feat = {}
feat['news_count'] = int(row['count'])
feat['news_count_z'] = float(row['count_z']) if pd.notna(row['count_z']) else np.nan
feat['news_presence'] = 1 if feat['news_count'] > 0 else 0
feat['news_burst'] = max(0.0, (feat['news_count_z'] if pd.notna(feat['news_count_z']) else 0.0) - 1.5)
feat['news_novelty'] = float(row.get('novelty', 0.0) or 0.0)
feat['news_sent_mean'] = np.clip(float(row.get('sent_mean', 0.0) or 0.0), -1, 1)
feat['news_sent_abs_mean'] = abs(feat['news_sent_mean'])
feat['news_sent_max'] = np.clip(float(row.get('sent_max', 0.0) or 0.0), -1, 1)
# recency in minutes relative to cutoff
cutoff_et = et_localize(pd.Timestamp(T)).replace(hour=15, minute=30)
last_ts_et = row['last_item_ts'].tz_convert('America/New_York') if pd.notna(row['last_item_ts']) else cutoff_et
feat['news_recency_min'] = max(0.0, (cutoff_et - last_ts_et).total_seconds() / 60.0)
# gate aliases
feat['gate_news_intensity'] = feat['news_burst']
feat['gate_news_novelty'] = feat['news_novelty']
```

## Acceptance checklist

* Feature values are computable from curated news **without** per‑item leaks.
* Empty‑news days produce defined defaults and do not propagate NaNs.
* Z‑score features honor warmup NA and clipping rules.
* Gate inputs `gate_news_intensity` and `gate_news_novelty` exist for fusion.

---

## Related Files

* `04-data-sources/alpaca_news_ws.md` — News data source
* `12-schemas/news.parquet.schema.md` — News schema
* `06-preprocessing/deduplication_novelty.md` — Novelty computation
* `08-modeling/heads_price_news_social.md` — News model head
* `08-modeling/fusion_gated_blend.md` — News burst gating
