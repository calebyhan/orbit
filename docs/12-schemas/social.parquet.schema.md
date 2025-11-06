
*Last edited: 2025-11-05*

## File Location

`data/social/YYYY/MM/DD/reddit.parquet`

## Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `string` | No | Reddit post ID |
| `created_utc` | `timestamp` | No | Post creation time (ET) |
| `subreddit` | `string` | No | Subreddit name |
| `author` | `string` | No | Reddit username (hashed for privacy) |
| `author_karma` | `int64` | Yes | Author karma score |
| `author_age_days` | `int64` | Yes | Account age in days |
| `title` | `string` | No | Post title |
| `body` | `string` | Yes | Post body text (may be empty for link posts) |
| `permalink` | `string` | No | Reddit permalink |
| `upvote_ratio` | `float64` | Yes | Upvote ratio (0 to 1) |
| `num_comments` | `int64` | No | Number of comments |
| `symbols` | `list<string>` | Yes | Mapped symbols (["SPY", "VOO"]) |
| `sentiment_vader` | `float64` | Yes | VADER compound score (-1 to +1) |
| `sentiment_finbert` | `float64` | Yes | FinBERT score (-1 to +1) |
| `sentiment_gemini` | `float64` | Yes | Gemini score (-1 to +1, if escalated) |
| `sarcasm_flag` | `bool` | Yes | Gemini sarcasm detection |
| `novelty_score` | `float64` | Yes | Dissimilarity to prior 7d (0 to 1) |
| `content_hash` | `string` | No | Hash for deduplication |
| `ingestion_ts` | `timestamp` | No | When ingested (ET) |

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
  "sentiment_vader": 0.62,
  "sentiment_finbert": 0.45,
  "sentiment_gemini": 0.58,
  "sarcasm_flag": false,
  "novelty_score": 0.34,
  "content_hash": "sha256:def456...",
  "ingestion_ts": "2024-11-05T15:35:12-05:00"
}
```

## Constraints

- `title` length: 5-300 chars
- `author_karma` ≥ 0
- `created_utc` ≤ `ingestion_ts`
- Sentiment scores in [-1, 1] if present
- At least one symbol mapped

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
    for col in ['sentiment_vader', 'sentiment_finbert', 'sentiment_gemini']:
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

# Weighted sentiment
weighted_sent = (df['sentiment_vader'] * df['weight']).sum() / df['weight'].sum()
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
    'sentiment_vader': 'mean',
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
