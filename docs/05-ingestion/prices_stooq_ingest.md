# ORBIT — Ingestion: Stooq Prices

*Last edited: 2025-11-10*

## Purpose

Fetch **daily OHLCV** CSVs for `SPY.US`, `VOO.US`, and `^SPX` from **Stooq**, normalize to a canonical schema, and append to the raw Parquet lake. Runs **once after close** on trading days.

## Inputs

* **Config:** `paths.*`, `sources.stooq.*`, `universe.symbols`, `universe.benchmark` (see `docs/03-config/config_schema.yaml`).
* **Endpoints:** `https://stooq.com/q/d/l/?s=<symbol>&i=d` (daily bars).

## Outputs

* **Raw Parquet:** `data/raw/prices/<SYMBOL>.parquet` (symbol-level, all history)
* **Schema:**

  * `date: date`
  * `symbol: string` (e.g., `SPY.US`)
  * `open, high, low, close: float64`
  * `volume: int64` (nullable)
  * `run_id: string`
  * `ingested_at: timestamp[ns, UTC]`

**Note:** Prices use symbol-level partitioning (one file per symbol) rather than date-level partitioning. Each file contains the complete history for that symbol and is overwritten daily.

## Steps

1. **Resolve symbols** from config (ETFs + `^SPX`).
2. **Download CSV** for each symbol (respect `polite_delay_sec`, retries/backoff).
3. **Normalize**: lower‑case headers; coerce types; add `symbol`, `run_id`, `ingested_at`.
4. **QC**: monotone date order; positive prices; volume ≥ 0 (nullable for index).
5. **Write** to `data/raw/prices/<SYMBOL>.parquet` (overwrite mode - full history each time).
6. **Dedupe**: Anti-join on `(symbol, date)` happens naturally since Stooq provides clean data.

## Pseudocode

```python
symbols = cfg.universe.symbols + [cfg.universe.benchmark]
for sym in symbols:
    url = f"{cfg.sources.stooq.base_url}?s={urllib.parse.quote(sym.lower())}&i=d"
    csv_bytes = polite_fetch(url, delay=cfg.sources.stooq.polite_delay_sec,
                             retries=cfg.sources.stooq.retries)
    df = pd.read_csv(io.BytesIO(csv_bytes))
    df.columns = [c.lower() for c in df.columns]
    df["symbol"] = sym
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for col in ["open","high","low","close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" in df:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("Int64")
    df["run_id"] = run_id
    df["ingested_at"] = pd.Timestamp.utcnow()

    qc_monotone(df, key="date")
    qc_bounds(df, price_cols=["open","high","low","close"], min_val=0)

    # Write symbol-level parquet (all history, overwrite mode)
    symbol_clean = sym.replace('.', '_').replace('^', '')
    write_parquet(df, f"data/raw/prices/{symbol_clean}.parquet", overwrite=True)
```

## QC checks

* Dates strictly **increasing** within each symbol.
* Price columns **> 0**; `volume ≥ 0` or `NA` for index.
* **Row growth** on new trading days; warn if none.
* Calendar reconciliation against U.S. market holidays/weekends.

## Errors & retries

* Network errors/HTTP ≥ 400: exponential backoff up to `retries`; then fail with actionable message and keep previous good snapshot.
* Schema drift (missing columns): fail fast; require manual update to mapping.

## Anti‑leak & time rules

* Prices are end‑of‑day; features for day *T* use the **close of T**; labels target *T+1*.
* All downstream timestamps normalized to **America/New_York** (see `docs/03-config/cutoffs_timezones.md`).

## Acceptance checklist

* New rows for each trading day are included in the symbol file.
* Parquet schema matches the **Outputs** definition.
* QC passes (monotone dates, positive prices, sane volumes).
* Re‑run fetches full history and overwrites previous file (idempotent).
* File structure: `data/raw/prices/SPY_US.parquet` (not date-partitioned).

---

## Related Files

* `04-data-sources/stooq_prices.md` — Stooq data source spec
* `12-schemas/prices.parquet.schema.md` — Price data schema
* `05-ingestion/storage_layout_parquet.md` — Storage structure
* `10-operations/data_quality_checks.md` — Quality validation
