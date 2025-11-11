# ORBIT — Storage Layout (Parquet)

*Last edited: 2025-11-10*

## Purpose

Define the **folder hierarchy and file naming conventions** for all Parquet data stored in the ORBIT pipeline. This ensures consistent organization, efficient querying, and clear audit trails.

**Critical distinction:**
- **`./data/`** (in repo): Contains ONLY sample data and production models (committed to git)
- **`/srv/orbit/data/`** (external): Contains ALL production/real data (never committed)

This doc primarily covers the production layout at `/srv/orbit/data/`. For sample data structure, see `docs/02-architecture/workspace_layout.md`.

---

## Directory Overview

### Production Data (External): `/srv/orbit/data/`

**ALL real/production data lives here exclusively:**

```
/srv/orbit/data/
├── raw/                    # Raw ingested data (no cleaning)
│   ├── prices/
│   │   ├── SPY_US.parquet       # All SPY history
│   │   ├── VOO_US.parquet       # All VOO history
│   │   └── SPX.parquet          # All S&P 500 index history
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
│   │   ├── SPY_US.parquet       # All SPY history (cleaned)
│   │   ├── VOO_US.parquet       # All VOO history (cleaned)
│   │   └── SPX.parquet          # All S&P 500 index history (cleaned)
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
├── models/                 # Trained model archive (all experiments)
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

### Sample Data (In Repo): `./data/`

**ONLY sample data and production models (committed to git):**

```
./data/
├── sample/                 # Test fixtures for CI/development
│   ├── prices/2024/11/05/
│   ├── news/2024/11/05/
│   ├── social/2024/11/05/
│   └── features/2024/11/05/
│
└── models/
    └── production/         # Latest vetted production model (promoted from /srv/orbit/data/models/)
        ├── heads/
        └── fusion/
```

**Important:** `./data/raw/`, `./data/curated/`, `./data/features/`, `./data/scores/` should **NEVER** exist in the repo. All production data belongs in `/srv/orbit/data/`.

---

## Partitioning Strategy

### Symbol-Level Partitioning (Prices)

**Prices use symbol-level partitioning** (one file per symbol with all history):

* **Format:** `<SYMBOL>.parquet` (e.g., `SPY_US.parquet`, `SPX.parquet`)
* **Example:** `/srv/orbit/data/raw/prices/SPY_US.parquet`
* **Rationale:**
  * Bootstrap fetches all history at once (thousands of rows)
  * Daily updates are simple overwrites with +1 new row
  * Efficient for time-series queries on a single symbol
  * Prices dataset is small enough (3 symbols, ~50k rows total)
  * Simplifies deduplication (anti-join on date within symbol)

### Date-Based Partitioning (News, Social, Features)

* **Format:** `YYYY/MM/DD/` (4-digit year, 2-digit month, 2-digit day)
* **Example:** `/srv/orbit/data/raw/news/2024/11/05/alpaca.parquet`
* **Rationale:**
  * Efficient daily incremental updates
  * Easy date range queries for text data
  * Clear temporal organization
  * Aligns with daily pipeline execution
  * Text data is append-heavy (hundreds of items per day)

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

* **Pattern:** `<SYMBOL>.parquet` (symbol-level, all history)
* **Examples:** `SPY_US.parquet`, `VOO_US.parquet`, `SPX.parquet`
* **Note:** Special characters replaced: `.` → `_`, `^` → removed
* **Contains:** All historical data for the symbol (updated daily with full history)

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
| **Sample data** | `./data/sample/` | **Indefinite** | Essential for CI/testing |

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

### Single Symbol Time-Series
```python
# Read all history for one symbol
df = pd.read_parquet("/srv/orbit/data/raw/prices/SPY_US.parquet")

# Filter to specific date range (efficient with parquet row groups)
df_filtered = df[df['date'] >= '2024-01-01']
```

### Multiple Symbols
```python
# Read multiple symbols
symbols = ['SPY_US', 'VOO_US', 'SPX']
dfs = {sym: pd.read_parquet(f"/srv/orbit/data/raw/prices/{sym}.parquet") 
       for sym in symbols}

# Or combine into one dataframe
df_all = pd.concat([pd.read_parquet(f"/srv/orbit/data/raw/prices/{sym}.parquet") 
                    for sym in symbols], ignore_index=True)
```
### News/Social Date Range Queries
```python
# Read multiple days (pyarrow handles partitions efficiently)
df = pd.read_parquet("data/news/", 
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

* **Daily snapshots:** Sync `/srv/orbit/data/` to S3/GCS after each pipeline run
* **Immutable archives:** Monthly archives of raw data (prices/news/social) from `/srv/orbit/data/raw/`
* **Model checkpoints:** Git LFS for production model in `./data/models/production/`; cloud storage for archive in `/srv/orbit/data/models/`

---

## Storage Location Summary

**In repository (`./data/`):**
- ✅ Sample data (`./data/sample/`)
- ✅ Production model (`./data/models/production/`)
- ❌ NO raw, curated, features, scores, or model archives

**External (`/srv/orbit/data/`):**
- ✅ ALL raw data
- ✅ ALL curated data
- ✅ ALL features
- ✅ ALL scores
- ✅ ALL model archives
- ✅ ALL rejects

**Environment variable:**
```bash
# MUST be set for all production operations
export ORBIT_DATA_DIR=/srv/orbit/data
```

**Default behavior:** If `ORBIT_DATA_DIR` is unset, code defaults to `./data` which should ONLY contain sample data and production models.

---

## Acceptance Checklist

- [ ] All dates follow `YYYY/MM/DD` partitioning
- [ ] File names match conventions (symbol.parquet for prices, source.parquet for text)
- [ ] Schemas validated on write
- [ ] `_metadata.json` written alongside data files
- [ ] Compression enabled (snappy)
- [ ] No duplicate rows within single partition (enforced by dedupe logic)
- [ ] `ORBIT_DATA_DIR=/srv/orbit/data` set for all production runs
- [ ] `./data/` contains ONLY sample data and production models (no raw/curated/features)

---

## Related Files

* `12-schemas/*.md` — Parquet schema definitions
* `05-ingestion/prices_stooq_ingest.md` — Price ingestion
* `05-ingestion/news_alpaca_ws_ingest.md` — News ingestion
* `05-ingestion/social_reddit_ingest.md` — Social ingestion
* `10-operations/data_quality_checks.md` — Schema validation procedures
