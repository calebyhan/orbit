# ORBIT — Social Features (Daily)

*Last edited: 2025-11-06*

## Purpose

Convert curated Reddit aggregates (by day *T*, cutoff **15:30 ET**) into daily features that capture **buzz intensity**, **stance**, and **novelty**, with credibility weighting and leak‑free construction.

## Inputs

From `data/curated/social/` (see 04‑data‑sources & 06‑preprocessing). Required columns for day *T*:

* `date: date`
* `post_count: int`
* `post_count_z: float` (vs 60‑day)
* `comment_velocity: float` (comments/hour near cutoff)
* `cred_weighted_sent: float` (in [−1,1], after quality weights)
* `sarcasm_rate: float` (0..1, if LLM available else 0)
* `novelty: float` (0..1, vs prior 7d)
* `last_item_ts: timestamp[ns, UTC]`
* `ingestion_complete: bool` — Whether Reddit API completed full day ingestion without gaps
* `ingestion_gaps_minutes: int` — Total minutes of missing data due to API limits/disconnects

Optional LLM fields per curated policy:

* `sent_llm_mean: float` (−1..1), `stance_bull_share: float` (0..1), `stance_bear_share: float` (0..1)

## Output fields (added to features row for *T*)

All features are later standardized per `standardization_scaling.md`.

| Feature                | Definition                                         | Notes                   |
| ---------------------- | -------------------------------------------------- | ----------------------- |
| `soc_post_count`       | copy of `post_count`                               | ≥0                      |
| `soc_post_count_z`     | copy of `post_count_z`                             | clip to [−5,+5]         |
| `soc_presence`         | `1{soc_post_count > 0}`                            | {0,1}                   |
| `soc_burst`            | `max(0, soc_post_count_z − 1.5)`                   | burst indicator         |
| `soc_comment_velocity` | copy of `comment_velocity`                         | unit: comments/hr       |
| `soc_novelty`          | copy of `novelty`                                  | [0,1]                   |
| `soc_sent_mean`        | copy of `cred_weighted_sent`                       | clamp to [−1,1]         |
| `soc_sent_abs_mean`    | `abs(soc_sent_mean)`                               | [0,1]                   |
| `soc_sarcasm_rate`     | copy of `sarcasm_rate`                             | 0..1 (0 if unavailable) |
| `soc_recency_min`      | minutes between **cutoff** and `last_item_ts` (ET) | ≥0                      |
| `soc_data_quality`     | `max(0, 1 − ingestion_gaps_minutes/360)`           | [0,1]; 1.0 if complete  |
| `gate_soc_intensity`   | alias of `soc_burst`                               | fusion gate input       |
| `gate_soc_novelty`     | alias of `soc_novelty`                             | fusion gate input       |

### Optional LLM‑enhanced features

| Feature                 | Definition                         |
| ----------------------- | ---------------------------------- |
| `soc_sent_llm_mean`     | copy of `sent_llm_mean` (−1..1)    |
| `soc_stance_bull_share` | copy of `stance_bull_share` (0..1) |
| `soc_stance_bear_share` | copy of `stance_bear_share` (0..1) |

## Data Quality Handling

**Data Quality Score:**
```
soc_data_quality = max(0, 1 - ingestion_gaps_minutes / 360)
# 360 minutes = 6 hours (full trading day expectation)
```

**Handling Rules:**
* **If quality < 0.5:** Treat as missing day — set all `soc_*` features to **0** (including sentiments, novelty, burst).
* **If 0.5 ≤ quality < 1.0:** Partial-day capture — include `soc_data_quality` feature, compute other features normally from available data.
* **If quality == 1.0:** Complete ingestion — normal processing, `soc_data_quality = 1.0`.

**Model Usage:**
The fusion gate (see `fusion_gated_blend.md`) will down-weight social head predictions on partial-data days by multiplying gate values by `soc_data_quality`. This allows the model to learn which quality thresholds are reliable vs unreliable.

**Examples:**
```python
# 0 gaps → quality = 1.0 (complete day)
# 30 min gaps → quality ≈ 0.917 (partial, usable)
# 180 min gaps → quality = 0.5 (borderline)
# 360+ min gaps → quality = 0.0 (treat as missing)
```

**Distinguishing Data Capture vs Quiet Day:**
* **Low `post_count` + quality = 1.0:** Truly quiet day (valid signal)
* **Low `post_count` + quality < 0.5:** Data capture issue (treat as missing)

## Defaults & NA rules

* If `post_count == 0` **and** `quality ≥ 0.5`: set `soc_*` sentiments/novelty/sarcasm to **0**, `soc_recency_min = 0`, `soc_presence = 0`.
* If **quality < 0.5:** set **all** `soc_*` features to **0** (unreliable partial day).
* Z‑scores like `soc_post_count_z` are **NA** until the 60‑day window exists; **do not** forward‑fill.

## Clipping & caps

* Clip z‑scores to **[−5,+5]** and sentiments to **[−1,1]**.

## Anti‑leak rules

* Curated aggregates must include **only** posts with `created_utc ≤ 15:30 ET` on day *T*.
* `soc_recency_min` uses `cutoff_ET(T) − last_item_ts_ET` (never after‑cutoff events).

## Pseudocode (reference)

```python
row = curated_social.loc[curated_social.date == T].squeeze()
feat = {}
feat['soc_post_count'] = int(row['post_count'])
feat['soc_post_count_z'] = float(row['post_count_z']) if pd.notna(row['post_count_z']) else np.nan
feat['soc_presence'] = 1 if feat['soc_post_count'] > 0 else 0
feat['soc_burst'] = max(0.0, (feat['soc_post_count_z'] if pd.notna(feat['soc_post_count_z']) else 0.0) - 1.5)
feat['soc_comment_velocity'] = float(row.get('comment_velocity', 0.0) or 0.0)
feat['soc_novelty'] = float(row.get('novelty', 0.0) or 0.0)
feat['soc_sent_mean'] = np.clip(float(row.get('cred_weighted_sent', 0.0) or 0.0), -1, 1)
feat['soc_sent_abs_mean'] = abs(feat['soc_sent_mean'])
feat['soc_sarcasm_rate'] = np.clip(float(row.get('sarcasm_rate', 0.0) or 0.0), 0, 1)
# recency
cutoff_et = et_localize(pd.Timestamp(T)).replace(hour=15, minute=30)
last_ts_et = row['last_item_ts'].tz_convert('America/New_York') if pd.notna(row['last_item_ts']) else cutoff_et
feat['soc_recency_min'] = max(0.0, (cutoff_et - last_ts_et).total_seconds() / 60.0)
# gates
feat['gate_soc_intensity'] = feat['soc_burst']
feat['gate_soc_novelty'] = feat['soc_novelty']
# optional LLM fields
for k_src, k_dst in [('sent_llm_mean','soc_sent_llm_mean'),
                     ('stance_bull_share','soc_stance_bull_share'),
                     ('stance_bear_share','soc_stance_bear_share')]:
    if k_src in row:
        feat[k_dst] = row[k_src]
```

## Acceptance checklist

* Features compute from curated social **only**; no per‑item leaks.
* Empty‑social days yield defined defaults and do not propagate NaNs.
* `gate_soc_intensity` and `gate_soc_novelty` exist for fusion.
* Optional LLM features are included only when available and otherwise omitted.

---

## Related Files

* `04-data-sources/reddit_api.md` — Social data source
* `12-schemas/social.parquet.schema.md` — Social schema
* `06-preprocessing/quality_filters_social.md` — Quality filters
* `08-modeling/heads_price_news_social.md` — Social model head
* `08-modeling/fusion_gated_blend.md` — Social burst gating
