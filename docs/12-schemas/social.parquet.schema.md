# ORBIT — social.parquet

*Last edited: 2025-11-16*

## File Location

**Raw:** `data/raw/social/date=YYYY-MM-DD/social.parquet`
**Curated:** `data/curated/social/date=YYYY-MM-DD/social.parquet` (after preprocessing)

**Examples:**
- `data/raw/social/date=2024-11-05/social.parquet`
- `data/curated/social/date=2024-11-05/social.parquet`

## Raw Schema (Post-Ingestion)

Written by `orbit ingest social-backfill` from Arctic Shift Reddit API.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `string` | No | Reddit post ID |
| `created_utc` | `timestamp` | No | Post creation time (UTC with TZ) |
| `subreddit` | `string` | No | Subreddit name |
| `author` | `string` | No | Hashed username (format: `hash_XXXXXXXX`) |
| `author_karma` | `int64` | Yes | Author karma (NULL for Arctic API) |
| `author_age_days` | `int64` | Yes | Account age (NULL for Arctic API) |
| `title` | `string` | No | Post title |
| `body` | `string` | Yes | Post body text (NULL if removed/deleted) |
| `permalink` | `string` | No | Reddit permalink |
| `upvote_ratio` | `float64` | Yes | Upvote ratio 0-1 (NULL for Arctic API) |
| `num_comments` | `int64` | No | Number of comments |
| `symbols` | `list<string>` | No | Matched terms: SPY, VOO, market, or "off-topic" |
| `sentiment_gemini` | `float64` | Yes | Gemini sentiment score (NULL until LLM scoring) |
| `sarcasm_flag` | `bool` | Yes | Sarcasm detection (NULL until LLM scoring) |
| `novelty_score` | `float64` | Yes | Novelty score (NULL until preprocessing) |
| `content_hash` | `string` | No | SHA256 hash for deduplication (16 chars) |
| `ingestion_ts` | `timestamp` | No | When ingested (UTC) |
| `ingestion_complete` | `bool` | No | True if full fetch completed |
| `ingestion_gaps_minutes` | `int64` | No | Minutes of gaps (0 for backfill) |
| `last_successful_fetch_utc` | `timestamp` | No | Last successful API fetch |

## Curated Schema (Post-Preprocessing)

Additional fields added by `orbit preprocess`:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| *(all raw fields)* | | | All fields from raw schema |
| `is_dupe` | `bool` | No | True if duplicate (simhash-based) |
| `cluster_id` | `string` | No | ID of duplicate cluster leader |
| `novelty` | `float64` | Yes | Novelty vs 7-day window [0,1] |
| `window_start_et` | `timestamp` | No | Membership window start (T-1 15:30 ET) |
| `window_end_et` | `timestamp` | No | Membership window end (T 15:30 ET) |
| `cutoff_applied_at` | `timestamp` | No | When preprocessing ran (UTC) |
| `dropped_late_count` | `int64` | No | Items dropped by safety lag |

## Sample Row

```json
{
  "id": "abc123xyz",
  "created_utc": "2024-11-05T13:45:00-05:00",
  "subreddit": "wallstreetbets",
  "author": "hash_u1234567",
  "author_karma": 5432,
  "author_age_days": 892,
  "title": "SPY calls printing today 🚀",
  "body": "Fed decision was bullish...",
  "permalink": "/r/wallstreetbets/comments/abc123/...",
  "upvote_ratio": 0.87,
  "num_comments": 42,
  "symbols": ["SPY"],
    "sentiment_gemini": 0.58,
  "sarcasm_flag": false,
  "novelty_score": 0.34,
  "content_hash": "sha256:def456...",
  "ingestion_ts": "2024-11-05T15:35:12-05:00",
  "ingestion_complete": true,
  "ingestion_gaps_minutes": 0,
  "last_successful_fetch_utc": "2024-11-05T20:35:12+00:00"
}
```

## Constraints

- `title` length: 5-300 chars
- `author_karma` ≥ 0
- `created_utc` ≤ `ingestion_ts`
- Sentiment scores in [-1, 1] if present
- At least one symbol mapped
- `ingestion_gaps_minutes` ≥ 0

## Data Completeness Tracking

**Purpose:** Track Reddit API availability to detect rate-limited or partial captures.

**Fields:**
- `ingestion_complete`: Set to `False` if API rate limited for >30 minutes or if <50% of expected batches completed
- `ingestion_gaps_minutes`: Sum of time periods when API was rate-limited or unreachable
- `last_successful_fetch_utc`: Updated with each successful API call; used to detect API issues

**Example Scenarios:**

**Scenario 1: Complete Day**
```python
ingestion_complete = True
ingestion_gaps_minutes = 0
# All scheduled batches (e.g., 2-6 batches throughout day) completed
```

**Scenario 2: Brief Rate Limit**
```python
ingestion_complete = True
ingestion_gaps_minutes = 15
# Rate limited for 15 minutes, then recovered
# Still considered complete (< 30 min gap)
```

**Scenario 3: Extended Rate Limiting**
```python
ingestion_complete = False
ingestion_gaps_minutes = 120
# Rate limited 1:00-3:00 PM, only morning data captured
# Marked incomplete
```

## Related Files

* `05-ingestion/social_reddit_ingest.md`
* `07-features/social_features.md`

---

## Validation Script

```bash
python -m orbit.ops.validate_schema --source social --date 2024-11-05
```

**Validation checks:**
- Schema conformance
- Sentiment scores in [-1, 1]
- `author_karma` ≥ 0
- `created_utc` ≤ `ingestion_ts`
- `created_utc` ≤ 15:30 ET cutoff
- No duplicates by `id` or `content_hash`

**Example validation:**

```python
def validate_social(file_path):
    df = pd.read_parquet(file_path)
    errors = []
    
    # Karma check
    if (df['author_karma'] < 0).any():
        errors.append("Negative karma detected")
    
    # Sentiment bounds
    for col in ['sentiment_gemini']:
        if col in df.columns:
            valid = df[col].dropna().between(-1, 1).all()
            if not valid:
                errors.append(f"{col} outside [-1, 1]")
    
    # Timestamps
    if (df['created_utc'] > df['ingestion_ts']).any():
        errors.append("created_utc > ingestion_ts")
    
    # Duplicates
    if df['id'].duplicated().any():
        errors.append(f"Duplicate IDs: {df['id'].duplicated().sum()}")
    
    return errors
```

---

## Common Access Patterns

### Load Social Data for Day

```python
df = pd.read_parquet('data/social/2024/11/05/reddit.parquet')

# Filter high-credibility posts
df_cred = df[
    (df['author_karma'] >= 1000) &
    (df['author_age_days'] >= 365)
]
```

### Compute Credibility-Weighted Sentiment

```python
# Log-scale karma weighting (capped at 10k)
df['karma_capped'] = df['author_karma'].clip(upper=10000)
df['weight'] = np.log1p(df['karma_capped'])

# Weighted sentiment (use Gemini when available)
if 'sentiment_gemini' in df.columns:
    weighted_sent = (df['sentiment_gemini'] * df['weight']).sum() / df['weight'].sum()
else:
    weighted_sent = np.nan
```

### Detect Sarcasm Rate

```python
# Sarcasm detection (from Gemini)
sarcasm_rate = df['sarcasm_flag'].mean()

print(f"Sarcasm rate: {sarcasm_rate:.2%}")
```

### Aggregate by Subreddit

```python
# Subreddit breakdowns
subreddit_agg = df.groupby('subreddit').agg({
    'id': 'count',
    'sentiment_gemini': 'mean',
    'upvote_ratio': 'mean',
    'num_comments': 'sum'
}).rename(columns={'id': 'post_count'})
```

### Check Comment Velocity

```python
# Comments per hour (last 4 hours before cutoff)
cutoff = pd.Timestamp('2024-11-05 15:30:00', tz='America/New_York')
recent = df[df['created_utc'] >= cutoff - pd.Timedelta(hours=4)]

comments_per_hour = recent['num_comments'].sum() / 4
```

---
