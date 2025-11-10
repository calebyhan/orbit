# ORBIT — Storage Layout (Parquet)

*Last edited: 2025-11-10*

## Purpose

Define the **folder hierarchy and file naming conventions** for all Parquet data stored in the ORBIT pipeline. This ensures consistent organization, efficient querying, and clear audit trails.

This doc covers the full production layout at `/srv/orbit/data/`. For the smaller in-repo layout (`./data/`) see `docs/02-architecture/workspace_layout.md`.

---

## Directory Structure (Production: `/srv/orbit/data/`)

```
/srv/orbit/data/
├── raw/                    # Raw ingested data (no cleaning)
│   ├── prices/
│   │   └── YYYY/
│   │       └── MM/
│   │           └── DD/
│   │               ├── SPY.parquet
│   │               ├── VOO.parquet
│   │               └── ^SPX.parquet
│   ├── news/
│   │   └── YYYY/
│   │       └── MM/
│   │           └── DD/
│   │               └── alpaca.parquet
│   ├── social/
│   │   └── YYYY/
│   │       └── MM/
│   │           └── DD/
│   │               └── reddit.parquet
│   └── gemini/             # Raw LLM request/response logs
│       └── YYYY/
│           └── MM/
│               └── DD/
│                   └── batch_<timestamp>.json
│
├── curated/                # Cleaned, deduplicated data
│   ├── prices/
│   │   └── YYYY/
│   │       └── MM/
│   │           └── DD/
│   │               ├── SPY.parquet
│   │               └── ...
│   ├── news/
│   │   └── YYYY/
│   │       └── MM/
│   │           └── DD/
│   │               └── alpaca.parquet
│   └── social/
│       └── YYYY/
│           └── MM/
│               └── DD/
│                   └── reddit.parquet
│
├── features/               # Engineered features
│   └── YYYY/
│       └── MM/
│           └── DD/
│               └── features_daily.parquet
│
├── scores/                 # Model predictions
│   └── <run_id>/
│       └── scores.parquet
│
├── models/                 # Trained model archive
│   └── <run_id>/
│       └── <window_id>/
│           ├── heads/
│           │   ├── price/
│           │   │   ├── model.pkl
│           │   │   └── calibrator.pkl (optional)
│           │   ├── news/
│           │   │   ├── model.pkl
│           │   │   └── calibrator.pkl (optional)
│           │   └── social/
│           │       ├── model.pkl
│           │       └── calibrator.pkl (optional)
│           └── fusion/
│               ├── fusion_params.json
│               └── calibrator.pkl (optional)
│
└── rejects/                # Failed quality checks
    └── <source>/
        └── <reason>/
            └── YYYY-MM-DD.parquet
```

**Note:** The repo also contains a smaller `./data/` with sample data and the production model. See `docs/02-architecture/workspace_layout.md` for that structure.

---

## Partitioning Strategy

### Date-Based Partitioning (Prices, News, Social, Features)

* **Format:** `YYYY/MM/DD/` (4-digit year, 2-digit month, 2-digit day)
* **Example:** `data/prices/2024/11/05/SPY.parquet`
* **Rationale:**
  * Efficient daily incremental updates
  * Easy date range queries
  * Clear temporal organization
  * Aligns with daily pipeline execution

### Run-Based Partitioning (Scores, Models)

* **Format:** `<run_id>/` where `run_id` is UUID or timestamp-based identifier
* **Example:** `data/scores/20241105_153042/scores.parquet`
* **Rationale:**
  * Isolates different experimental runs
  * Enables A/B testing and comparison
  * Preserves historical model versions

---

## File Naming Conventions

### Prices

* **Pattern:** `<SYMBOL>.parquet`
* **Examples:** `SPY.parquet`, `VOO.parquet`, `^SPX.parquet`
* **One file per symbol per day**

### News

* **Pattern:** `alpaca.parquet`
* **All news items for the day in single file**
* **Future:** If multiple news sources added, use `<source>.parquet` (e.g., `bloomberg.parquet`)

### Social

* **Pattern:** `reddit.parquet`
* **All Reddit posts/comments for the day in single file**
* **Future:** If multiple social sources added, use `<platform>.parquet` (e.g., `twitter.parquet`)

### Features

* **Pattern:** `features_daily.parquet`
* **Contains one row per trading day with all features for SPY/VOO**

### Scores

* **Pattern:** `scores.parquet`
* **Append-only file within each run_id directory**
* **Contains date column for temporal queries**

---

## Schema Enforcement

Each parquet file **must** conform to its schema definition:

* **Prices:** `docs/12-schemas/prices.parquet.schema.md`
* **News:** `docs/12-schemas/news.parquet.schema.md`
* **Social:** `docs/12-schemas/social.parquet.schema.md`
* **Features:** `docs/12-schemas/features_daily.parquet.schema.md`

Validation runs automatically during ingestion via:
```bash
python -m orbit.ops.validate_schema --source <prices|news|social|features> --date YYYY-MM-DD
```

---

## Append vs Overwrite Semantics

| Data Type | Write Mode | Location | Rationale |
|-----------|------------|----------|-----------|
| Raw Prices | **Overwrite** | `/srv/orbit/data/raw/prices/` | Daily static snapshot; may receive late corrections |
| Raw News | **Append** | `/srv/orbit/data/raw/news/` | Continuous stream; dedupe via content_hash |
| Raw Social | **Append** | `/srv/orbit/data/raw/social/` | Continuous stream; dedupe via post ID |
| Curated (all) | **Overwrite** | `/srv/orbit/data/curated/` | Recomputed daily from raw after cleaning |
| Features | **Overwrite** | `/srv/orbit/data/features/` | Recomputed daily from curated sources |
| Scores | **Append** | `/srv/orbit/data/scores/` | Accumulate predictions over time |
| Models | **Write-once** | `/srv/orbit/data/models/` + `./data/models/production/` | Immutable after training; production copy in repo |

---

## Retention Policy

| Data Type | Location | Retention | Rationale |
|-----------|----------|-----------|-----------|
| **Raw ingestion** (prices/news/social) | `/srv/orbit/data/raw/` | **Indefinite** | Audit trail, can regenerate downstream |
| **Curated** | `/srv/orbit/data/curated/` | **2 years** | Covers walk-forward history |
| **Features** | `/srv/orbit/data/features/` | **2 years** | Covers walk-forward history |
| **Scores** | `/srv/orbit/data/scores/` | **1 year per run_id** | Performance analysis |
| **Models (archive)** | `/srv/orbit/data/models/` | **Top 5 runs + production** | A/B testing, rollback |
| **Models (production)** | `./data/models/production/` | **Current only** | In repo, updated on promotion |
| **Rejects** | `/srv/orbit/data/rejects/` + `./data/rejects/` (samples) | **90 days (external), indefinite (repo samples)** | Debugging, quality monitoring |

---

## Metadata Files

Each directory **should** contain:

* `_metadata.json`: Schema version, ingestion timestamp, row counts
* `_SUCCESS`: Empty marker file indicating complete write

Example `_metadata.json`:
```json
{
  "schema_version": "1.0",
  "ingestion_ts": "2024-11-05T15:35:22-05:00",
  "row_count": 3,
  "symbols": ["SPY", "VOO", "^SPX"],
  "source": "stooq"
}
```

---

## Compression

* **Codec:** `snappy` (default for pyarrow)
* **Rationale:** Good balance of compression ratio and read speed
* **Alternative:** `gzip` for archival storage (better compression, slower reads)

---

## Access Patterns

### Daily Incremental Updates
```python
# Read latest day
df = pd.read_parquet(f"data/prices/2024/11/05/SPY.parquet")
```

### Date Range Queries
```python
# Read multiple days (pyarrow handles partitions efficiently)
df = pd.read_parquet("data/prices/", 
                     filters=[("date", ">=", "2024-11-01"),
                              ("date", "<=", "2024-11-05")])
```

### Feature Lookback Windows
```python
# Read last 60 days for z-score calculation
start_date = (today - timedelta(days=60)).strftime("%Y/%m/%d")
end_date = today.strftime("%Y/%m/%d")
df = pd.read_parquet(f"data/features/", 
                     filters=[("date", ">=", start_date)])
```

---

## Backup Strategy

* **Daily snapshots:** Sync `data/` to S3/GCS after each pipeline run
* **Immutable archives:** Monthly archives of raw data (prices/news/social)
* **Model checkpoints:** Git LFS or cloud storage for model binaries

---

## Acceptance Checklist

- [ ] All dates follow `YYYY/MM/DD` partitioning
- [ ] File names match conventions (symbol.parquet for prices, source.parquet for text)
- [ ] Schemas validated on write
- [ ] `_metadata.json` written alongside data files
- [ ] Compression enabled (snappy)
- [ ] No duplicate rows within single partition (enforced by dedupe logic)

---

## Related Files

* `12-schemas/*.md` — Parquet schema definitions
* `05-ingestion/prices_stooq_ingest.md` — Price ingestion
* `05-ingestion/news_alpaca_ws_ingest.md` — News ingestion
* `05-ingestion/social_reddit_ingest.md` — Social ingestion
* `10-operations/data_quality_checks.md` — Schema validation procedures
