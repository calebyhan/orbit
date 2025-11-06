# ORBIT — Stooq Prices

*Last edited: 2025-11-05*

## Purpose

Specify how ORBIT fetches **daily OHLCV** for `SPY.US`, `VOO.US`, and `^SPX` from **Stooq** via CSV downloads, and how to persist them in the raw lake.

## Symbols & endpoints

* **SPY (ETF):** `SPY.US`
* **VOO (ETF):** `VOO.US`
* **S&P 500 index:** `^SPX`

**CSV download pattern** (daily bars):

```
https://stooq.com/q/d/l/?s=<symbol>&i=d
```

Examples:

```
https://stooq.com/q/d/l/?s=spy.us&i=d
https://stooq.com/q/d/l/?s=voo.us&i=d
https://stooq.com/q/d/l/?s=%5Espx&i=d   # URL-encoded caret
```

> Notes
>
> * Stooq provides CSV without auth; be polite (throttle, cache).
> * Treat columns **as provided** by the vendor; do not assume split/dividend adjustment conventions. If you require adjusted series, compute them explicitly in preprocessing.

## CSV schema (source)

Columns (header row present):

* `Date` — `YYYY-MM-DD`
* `Open` — float
* `High` — float
* `Low` — float
* `Close` — float
* `Volume` — integer (may be 0 for some index series)

## Normalization → Parquet (raw lake)

For each symbol fetched:

1. Add `symbol` (e.g., `SPY.US`) and lower‑case columns.
2. Cast types (`date` as date; price columns as float; `volume` as int; missing as `NaN`).
3. Append to `data/raw/prices/` partitioned by `symbol`.

**Raw Parquet schema**

* `date: date`
* `symbol: string`
* `open: float64`
* `high: float64`
* `low: float64`
* `close: float64`
* `volume: int64` (nullable)
* `run_id: string`
* `ingested_at: timestamp[ns, UTC]`

## Fetch cadence

* Run `ingest:prices` **once after the official close** on trading days.
* Keep a simple **ETL cache** (save last ETag/content hash) to avoid re‑downloading unchanged files.

## Validation & QC

* **Monotone dates** per symbol (strictly increasing; no duplicates).
* **Row growth**: the latest run should add ≥1 new row on a trading day.
* **Bounds**: prices > 0; volumes ≥ 0.
* **Calendar**: reconcile missing dates with exchange holidays/weekends.

## Error handling

* Network 4xx/5xx → retry with backoff up to `sources.stooq.retries`.
* Empty/short files → keep previous good snapshot; log warning.
* Schema drift (unexpected headers) → fail fast with a clear error.

## Anti‑leak & time rules

* Prices are **EOD**; use day *T* close when building features for day *T* and labels for *T+1*.
* Normalize all downstream timestamps to **America/New_York** (cutoffs live in `docs/03-config/cutoffs_timezones.md`).

## Acceptance checklist

* Able to download and store CSV for `SPY.US`, `VOO.US`, `^SPX` into `data/raw/prices/` with the schema above.
* QC checks pass (dates monotone; positive prices; calendar consistent).
* Re‑runs append (no duplicates) and respect polite throttling.
* Downstream `preprocess` can compute returns and windows without NA explosions.

---

## Related Files

* `05-ingestion/prices_stooq_ingest.md` — Ingestion module implementation
* `12-schemas/prices.parquet.schema.md` — Canonical price data schema
* `03-config/cutoffs_timezones.md` — Timezone and cutoff rules
* `04-data-sources/rate_limits.md` — Rate limiting and backoff policies
* `07-features/price_features.md` — Price-based feature computations
