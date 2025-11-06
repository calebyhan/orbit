# ORBIT — news.parquet

*Last edited: 2025-11-06*

## File Location

`data/news/YYYY/MM/DD/alpaca.parquet`

## Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `string` | No | Unique news item ID (from Alpaca) |
| `published_at` | `timestamp` | No | Publication timestamp (ET) |
| `headline` | `string` | No | Article headline |
| `summary` | `string` | Yes | Article summary/snippet |
| `author` | `string` | Yes | Author name |
| `source` | `string` | No | News source (e.g., "Reuters", "Bloomberg") |
| `url` | `string` | Yes | Article URL |
| `symbols` | `list<string>` | Yes | Mapped symbols (["SPY", "VOO"]) |
| `sentiment_vader` | `float64` | Yes | VADER compound score (-1 to +1) |
| `sentiment_finbert` | `float64` | Yes | FinBERT score (-1 to +1) |
| `sentiment_gemini` | `float64` | Yes | Gemini score (-1 to +1, if escalated) |
| `novelty_score` | `float64` | Yes | Dissimilarity to prior 7d (0 to 1) |
| `content_hash` | `string` | No | Hash for deduplication |
| `ingestion_ts` | `timestamp` | No | When ingested (ET) |
| `ingestion_complete` | `bool` | No | True if full day captured without gaps |
| `ingestion_gaps_minutes` | `int32` | Yes | Total minutes of known disconnection/outage |
| `last_successful_fetch_utc` | `timestamp` | Yes | Last successful WS message received |

## Sample Row

```json
{
  "id": "alpaca_news_12345",
  "published_at": "2024-11-05T14:23:15-05:00",
  "headline": "Fed Holds Rates Steady Amid Inflation Concerns",
  "summary": "The Federal Reserve kept interest rates unchanged...",
  "author": "Jane Smith",
  "source": "Reuters",
  "url": "https://reuters.com/...",
  "symbols": ["SPY", "VOO"],
  "sentiment_vader": 0.12,
  "sentiment_finbert": 0.08,
  "sentiment_gemini": null,
  "novelty_score": 0.87,
  "content_hash": "sha256:abc123...",
  "ingestion_ts": "2024-11-05T15:30:02-05:00",
  "ingestion_complete": true,
  "ingestion_gaps_minutes": 0,
  "last_successful_fetch_utc": "2024-11-05T20:30:02+00:00"
}
```

## Constraints

- `headline` length: 10-500 chars
- `published_at` ≤ `ingestion_ts`
- At least one symbol mapped
- Sentiment scores in [-1, 1] if present
- `ingestion_gaps_minutes` ≥ 0 (0 if complete)
- `ingestion_complete` = False if gaps > 30 minutes

## Data Completeness Tracking

**Purpose:** Track WebSocket connection quality to detect partial day captures.

**Fields:**
- `ingestion_complete`: Set to `False` if WS disconnection lasted >5 minutes or if <80% of expected trading hours covered
- `ingestion_gaps_minutes`: Sum of all disconnection periods during trading hours (9:30-15:30 ET)
- `last_successful_fetch_utc`: Updated with each successful WS message; used to detect stale connections

**Example Scenarios:**

**Scenario 1: Complete Day**
```python
ingestion_complete = True
ingestion_gaps_minutes = 0
# All hours from 9:30-15:30 ET captured
```

**Scenario 2: Brief Disconnect**
```python
ingestion_complete = True
ingestion_gaps_minutes = 3
# WS disconnected 11:00-11:03 (3 min), reconnected successfully
# Still considered complete (< 5 min gap)
```

**Scenario 3: Major Outage**
```python
ingestion_complete = False
ingestion_gaps_minutes = 180
# WS disconnected 11:00-14:00 (3 hours), missing significant data
# Marked incomplete
```

## Related Files

* `05-ingestion/news_alpaca_ws_ingest.md`
* `07-features/news_features.md`

---

## Validation Script

```bash
python -m orbit.ops.validate_schema --source news --date 2024-11-05
```

**Validation checks:**
- Schema conformance (columns, types)
- Sentiment scores in [-1, 1]
- No duplicates by `id` or `content_hash`
- `published_at` ≤ `ingestion_ts`
- `published_at` ≤ 15:30 ET cutoff for day T
- At least one symbol mapped

**Example validation:**

```python
def validate_news(file_path):
    df = pd.read_parquet(file_path)
    errors = []
    
    # Sentiment bounds
    for col in ['sentiment_vader', 'sentiment_finbert', 'sentiment_gemini']:
        if col in df.columns:
            valid = df[col].dropna().between(-1, 1).all()
            if not valid:
                errors.append(f"{col} outside [-1, 1]")
    
    # Timestamps
    if (df['published_at'] > df['ingestion_ts']).any():
        errors.append("published_at > ingestion_ts")
    
    # Duplicates
    if df['id'].duplicated().any():
        errors.append(f"Duplicate IDs: {df['id'].duplicated().sum()}")
    
    # Symbol mapping
    if df['symbols'].isna().all():
        errors.append("No symbols mapped")
    
    return errors
```

---

## Common Access Patterns

### Load News for Single Day

```python
df = pd.read_parquet('data/news/2024/11/05/alpaca.parquet')

# Filter to SPY-relevant news
spy_news = df[df['symbols'].apply(lambda x: 'SPY' in x if x else False)]
```

### Aggregate Sentiment by Day

```python
# Load date range
df = pd.read_parquet(
    'data/news/',
    filters=[('published_at', '>=', '2024-11-01')]
)

# Daily sentiment average
daily = df.groupby(df['published_at'].dt.date).agg({
    'sentiment_vader': 'mean',
    'sentiment_finbert': 'mean',
    'novelty_score': 'mean',
    'id': 'count'
}).rename(columns={'id': 'news_count'})
```

### Filter by Source Quality

```python
# High-quality sources only
quality_sources = ['Reuters', 'Bloomberg', 'WSJ']
df_quality = df[df['source'].isin(quality_sources)]
```

### Check for News Bursts

```python
# Compute z-score of news count
daily_counts = df.groupby(df['published_at'].dt.date).size()
mean_count = daily_counts.rolling(60).mean()
std_count = daily_counts.rolling(60).std()
z_score = (daily_counts - mean_count) / std_count

# Burst days (z > 2.0)
burst_days = z_score[z_score > 2.0]
```

---
