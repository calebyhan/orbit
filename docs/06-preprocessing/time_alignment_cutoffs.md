# ORBIT — Time Alignment & Cutoffs

*Last edited: 2025-11-05*

## Purpose

Define **deterministic, point‑in‑time** rules that convert source timestamps to **ET** and slice each day *T* into a fixed membership window so features are reproducible and leak‑free.

## Daily membership window (text)

* **Timezone:** `America/New_York` (ET), DST‑aware.
* **Window for day T (right‑closed):** `(T−1 15:30,  T 15:30]` in ET.

  * Items with `published_at/created_utc` **within this window** belong to day *T*.
  * Rationale: avoids double‑counting across days and anchors to the same decision boundary used by the model.

## Prices

* Use **EOD close** for *T* from Stooq when computing features for *T* and labels targeting *T+1*.

## Safety lag (training only)

* Drop any text items whose timestamp lies within **`publish_lag_minutes`** of the *upper* boundary (15:30 ET) during **training** to avoid clock jitter or edit delays contaminating labels.
* Default: **30 minutes** (configurable).

## Edits & corrections

* **Canonical time**: use the **original publication/creation time** for membership. Ignore edit times for day assignment; optionally store `edited_at` for audit.
* If a source supplies only `received_at`, fall back to it but **flag** those rows; prefer sources with `published_at`.

## Early/late sessions & holidays

* **Half days / early closes**: the cutoff **stays at 15:30 ET** to maintain a fixed research boundary (less text may fall into T on early‑close days).
* **Holidays/weekends**: no membership windows are formed; skip *T* entirely if there is no price close.

## Implementation (reference)

```python
import pandas as pd
import pytz
ET = pytz.timezone('America/New_York')

def membership_window(date_T: pd.Timestamp):
    # date_T is a naive date (YYYY-MM-DD) or tz-naive midnight
    start = ET.localize(pd.Timestamp(date_T) - pd.Timedelta(days=1)).replace(hour=15, minute=30)
    end   = ET.localize(pd.Timestamp(date_T)).replace(hour=15, minute=30)
    return start, end

def slice_day(df, ts_col, date_T, publish_lag_min=30, training=True):
    start, end = membership_window(date_T)
    ts = df[ts_col].dt.tz_convert(ET)
    mask = (ts > start) & (ts <= end)
    if training and publish_lag_min:
        mask &= (ts <= end - pd.Timedelta(minutes=publish_lag_min))
    out = df[mask].copy()
    out['window_start_et'] = start
    out['window_end_et'] = end
    out['cutoff_applied_at'] = pd.Timestamp.now(tz='UTC')
    return out
```

## Join semantics for features

* **Key:** `date = T` (trading day).
* **Inputs:**

  * `curated/news[T]` = aggregate of all items in `(T−1 15:30, T 15:30]`.
  * `curated/social[T]` = same window.
  * `curated/prices[T]` = EOD close for *T*.
* **Output:** exactly **one row** in `features_daily` per *T*.

## Audit fields (recommended)

* `window_start_et`, `window_end_et`
* `cutoff_applied_at` (UTC)
* `dropped_late_count` (number of items excluded by safety lag)
* `received_after_cutoff_count` (diagnostic; should be 0 in curated)

## QC checks

* All curated text rows for *T* satisfy `(T−1 15:30, T 15:30]` membership.
* Safety‑lagged drops are recorded when `training=True`.
* No features join contains items with timestamps beyond `window_end_et`.
* On holidays/closed days, *T* is skipped (no `features_daily` row).

## Acceptance

* The preprocessing step produces curated tables with **ET‑normalized timestamps** and **strict daily membership** that match downstream features and labels.

---

## Related Files

* `03-config/cutoffs_timezones.md` — Cutoff configuration
* `08-modeling/targets_labels.md` — Label timing
* `06-preprocessing/deduplication_novelty.md` — Temporal deduplication
