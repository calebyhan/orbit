# ORBIT — news.parquet (Raw)

*Last edited: 2025-11-16*

## File Location

**Raw data (as ingested):**
- WebSocket: `data/raw/news/date=YYYY-MM-DD/news.parquet`
- Backfill: `data/raw/news/date=YYYY-MM-DD/news_backfill.parquet`

**Curated data (after preprocessing):**
- `data/curated/news/date=YYYY-MM-DD/news.parquet` (includes sentiment, novelty, quality filters)

## Raw Schema (WebSocket & Backfill)

This is the schema for **raw ingested data** before preprocessing.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `msg_id` | `int64` or `string` | No | Unique message ID (int from Alpaca API, string hash if ID missing) |
| `published_at` | `timestamp[ns, UTC]` | No | Publication timestamp (UTC, from `created_at` or `updated_at`) |
| `received_at` | `timestamp[ns, UTC]` | No | When our client received/fetched the message (UTC) |
| `symbols` | `list<string>` | No | Symbols tagged by Alpaca (e.g., ["SPY", "VOO"]) |
| `headline` | `string` | No | Article headline |
| `summary` | `string` | Yes | Article summary/snippet (empty string if not provided) |
| `source` | `string` | No | News source (e.g., "benzinga", "Reuters") |
| `url` | `string` | Yes | Article URL |
| `raw` | `string` (JSON) | No | Original message payload as JSON string (for audit) |
| `run_id` | `string` | No | Ingestion run identifier (format: YYYYMMDD_HHMMSS[_backfill]) |

## Sample Row (Raw)

```json
{
  "msg_id": 32179852,
  "published_at": "2023-05-03T06:11:16+00:00",
  "received_at": "2025-11-16T03:08:30.482886+00:00",
  "symbols": ["AAPL", "KRE", "QQQ", "SPY"],
  "headline": "Jim Cramer Identifies 4 Hurdles Facing Investors Today",
  "summary": "",
  "source": "benzinga",
  "url": "https://www.benzinga.com/markets/equities/23/05/32179852/...",
  "raw": "{\"author\": \"Bhavik Nair\", \"content\": \"\", \"created_at\": \"2023-05-03T06:11:16Z\", \"headline\": \"...\", \"id\": 32179852, \"source\": \"benzinga\", \"symbols\": [\"AAPL\", \"KRE\", \"QQQ\", \"SPY\"], \"updated_at\": \"2023-05-03T06:11:16Z\", \"url\": \"...\"}",
  "run_id": "20251116_025027_backfill"
}
```

## Constraints (Raw Data)

- `headline` length: >0 chars (no max enforced at ingestion)
- `published_at` ≤ `received_at` (with 30s tolerance for clock skew)
- `published_at` ≤ now() + 30s (not in future)
- `symbols` list: non-empty (at least one symbol from Alpaca)
- `msg_id`: unique within partition (deduplication enforced)
- `run_id` format: `YYYYMMDD_HHMMSS` or `YYYYMMDD_HHMMSS_backfill`

## Data Sources

**Two ingestion paths produce this raw schema:**

1. **WebSocket (real-time)**: `orbit ingest news`
   - Connects to Alpaca News WebSocket
   - Streams news during market hours
   - Writes to `news.parquet` (no suffix)
   - `run_id` format: `YYYYMMDD_HHMMSS`

2. **REST Backfill (historical)**: `orbit ingest news-backfill`
   - Fetches historical news via Alpaca REST API
   - Used for bootstrap and gap-filling
   - Writes to `news_backfill.parquet` (suffix)
   - `run_id` format: `YYYYMMDD_HHMMSS_backfill`

**Both produce identical schema** - preprocessing merges them transparently.

## Curated Schema (After Preprocessing)

After raw data passes through preprocessing pipeline, additional fields are computed:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| *(all raw fields)* | | | All fields from raw schema preserved |
| `is_dupe` | `bool` | No | True if near-duplicate (Hamming distance ≤3) |
| `cluster_id` | `string` | No | ID of cluster leader (earliest duplicate) |
| `novelty` | `float64` | Yes | Novelty score vs 7-day reference window [0, 1] (null for duplicates) |
| `window_start_et` | `timestamp[ns, UTC]` | No | Start of 15:30 ET cutoff window (T-1 15:30) |
| `window_end_et` | `timestamp[ns, UTC]` | No | End of 15:30 ET cutoff window (T 15:30) |
| `cutoff_applied_at` | `timestamp[ns, UTC]` | No | When preprocessing was applied |
| `sent_llm` | `float64` | Yes | Gemini sentiment score in [-1, 1] (if LLM scored) |
| `stance` | `string` | Yes | "bull", "bear", or "neutral" (if LLM scored) |
| `sarcasm` | `bool` | Yes | Sarcasm flag (if LLM scored) |
| `certainty` | `float64` | Yes | Sentiment certainty [0, 1] (if LLM scored) |
| `toxicity` | `float64` | Yes | Toxicity score [0, 1] (if LLM scored) |

**Curated location**: `data/curated/news/date=YYYY-MM-DD/news.parquet`

**Preprocessing steps** (in order):
1. **Cutoff enforcement**: Filter to (T-1 15:30, T 15:30] ET window (see `cutoffs.py`)
2. **Deduplication**: Simhash with 3-gram tokenization, Hamming distance ≤3 (see `dedupe.py`)
3. **Novelty scoring**: Compare vs 7-day reference window (see `dedupe.py`)
4. **LLM sentiment** (optional): Gemini 2.5 Flash-Lite batch scoring (see `llm_gemini.py`)

**Notes:**
- LLM fields (`sent_llm`, `stance`, `sarcasm`, `certainty`, `toxicity`) are **optional** and only present if LLM scoring was run
- Novelty is null for duplicates (only cluster leaders get novelty scores)
- Deduplication uses simhash (64-bit), not content hashing

## Related Files

* `05-ingestion/news_alpaca_ws_ingest.md`
* `07-features/news_features.md`

---

## Validation Script (Raw Data)

```bash
python -m orbit.ops.validate_schema --source news --date 2025-11-15
```

**Validation checks for raw data:**
- Schema conformance (columns, types)
- No duplicates by `msg_id` within partition
- `published_at` ≤ `received_at` (with tolerance)
- `published_at` not in future
- `symbols` list non-empty
- `headline` non-empty

**Example validation:**

```python
def validate_raw_news(file_path):
    df = pd.read_parquet(file_path)
    errors = []
    
    # Required columns
    required = ['msg_id', 'published_at', 'received_at', 'symbols', 
                'headline', 'source', 'url', 'raw', 'run_id']
    missing = set(required) - set(df.columns)
    if missing:
        errors.append(f"Missing columns: {missing}")
    
    # Timestamps
    # Allow 30s tolerance for clock skew
    tolerance = pd.Timedelta(seconds=30)
    invalid_ts = (df['published_at'] > df['received_at'] + tolerance).sum()
    if invalid_ts > 0:
        errors.append(f"published_at > received_at: {invalid_ts} rows")
    
    # Future timestamps
    now = pd.Timestamp.utcnow()
    future = (df['published_at'] > now + tolerance).sum()
    if future > 0:
        errors.append(f"Future published_at: {future} rows")
    
    # Duplicates
    dupes = df['msg_id'].duplicated().sum()
    if dupes > 0:
        errors.append(f"Duplicate msg_id: {dupes}")
    
    # Empty fields
    empty_headlines = (df['headline'].str.strip() == '').sum()
    if empty_headlines > 0:
        errors.append(f"Empty headlines: {empty_headlines}")
    
    # Empty symbols
    empty_symbols = df['symbols'].apply(lambda x: len(x) == 0 if isinstance(x, list) else True).sum()
    if empty_symbols > 0:
        errors.append(f"Empty symbols: {empty_symbols}")
    
    return errors
```

---

## Common Access Patterns

### Load Raw News for Single Day

```python
import pandas as pd
import glob

# Load all news for a specific date (WebSocket + backfill)
date_path = 'data/raw/news/date=2023-05-03'
files = glob.glob(f'{date_path}/*.parquet')
df = pd.concat([pd.read_parquet(f) for f in files])

# Filter to SPY-relevant news
spy_news = df[df['symbols'].apply(lambda x: 'SPY' in x if isinstance(x, list) else False)]

print(f"Total news: {len(df)}, SPY-tagged: {len(spy_news)}")
```

### Merge WebSocket and Backfill Data

```python
# Load both sources for date range
import glob

all_files = glob.glob('data/raw/news/date=2023-*/news*.parquet')
df = pd.concat([pd.read_parquet(f) for f in all_files])

# Deduplicate by msg_id (prefer WebSocket over backfill if duplicate)
df = df.sort_values('run_id').drop_duplicates(subset='msg_id', keep='first')

print(f"Total unique news items: {len(df)}")
```

### Count News by Source

```python
df = pd.read_parquet('data/raw/news/date=2023-05-03/news_backfill.parquet')

source_counts = df['source'].value_counts()
print(source_counts)
# benzinga    45
# reuters     12
# ...
```

### Filter by Symbols

```python
# Articles mentioning both SPY and VOO
spy_voo = df[df['symbols'].apply(
    lambda x: 'SPY' in x and 'VOO' in x if isinstance(x, list) else False
)]
```

### Check Ingestion Coverage

```python
import glob
from datetime import datetime, timedelta

# Check which dates have data
dates = sorted(set([
    p.split('date=')[1].split('/')[0] 
    for p in glob.glob('data/raw/news/date=*/news*.parquet')
]))

print(f"Data coverage: {dates[0]} to {dates[-1]}")
print(f"Total days: {len(dates)}")

# Find gaps
date_objs = [datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
expected_days = (date_objs[-1] - date_objs[0]).days + 1
print(f"Missing days: {expected_days - len(dates)}")
```

---
