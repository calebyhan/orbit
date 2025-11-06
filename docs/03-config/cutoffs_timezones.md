# ORBIT — Cutoffs & Timezones

*Last edited: 2025-11-05*

## Policy

* **Timezone:** All timestamps normalized to **America/New_York (ET)**; handle DST changes.
* **Daily cutoff:** Include **only** text (news/social) with `published_at/created_utc ≤ 15:30 ET` on day *T* for features built on *T*.
* **Safety lag (training):** additionally drop items within **publish_lag_minutes** of the cutoff to avoid timestamp jitter.
* **Prices:** Use official close prices for day *T* (Stooq EOD) when computing features and labels.

## Rationale

* Reduces look‑ahead bias from late posts/edits near the close.
* Ensures reproducible feature rows aligned to a consistent market boundary.

## Implementation notes

* Convert all source timestamps to ET **before** filtering by cutoff.
* Use exchange calendars to identify trading days; skip non‑trading days.
* Store `cutoff_applied_at` and counts of dropped late items per day for auditability.

## Pseudocode

```python
# tz-aware cutoff test
cutoff = pd.Timestamp(date_str + " 15:30", tz="America/New_York")
mask = (df.timestamp.dt.tz_convert("America/New_York") <= cutoff)
curated = df[mask].copy()

# optional lag window (e.g., 30 min)
lag_min = cfg.schedule.publish_lag_minutes
curated = curated[curated.timestamp <= cutoff - pd.Timedelta(minutes=lag_min)]
```

## Acceptance checklist

* A single, explicit cutoff boundary is implemented and logged daily.
* All timestamps are ET‑aware before filtering.
* Late items and dropped counts are reported in logs and QC tables.

---

## Related Files

* `06-preprocessing/time_alignment_cutoffs.md` — Cutoff implementation
* `04-data-sources/alpaca_news_ws.md` — News cutoff application
* `04-data-sources/reddit_api.md` — Social cutoff application
* `08-modeling/targets_labels.md` — Label timing rules
