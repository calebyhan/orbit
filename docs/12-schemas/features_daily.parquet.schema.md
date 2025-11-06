
*Last edited: 2025-11-05*

## File Location

`data/features/YYYY/MM/DD/features_daily.parquet`

## Purpose

**One row per trading day** with all price, news, and social features computed up to 15:30 ET cutoff.

## Schema

### Identifiers

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `date` | `date` | No | Trading date |
| `symbol` | `string` | No | Always "SPY" for v1 index model |

### Price Features (13 columns)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `momentum_5d` | `float64` | Yes | 5-day return |
| `momentum_20d` | `float64` | Yes | 20-day return |
| `momentum_50d` | `float64` | Yes | 50-day return |
| `reversal_1d` | `float64` | Yes | 1-day return (contrarian) |
| `rv_10d` | `float64` | Yes | 10-day realized vol |
| `drawdown_20d` | `float64` | Yes | Max drawdown from 20d peak |
| `etf_index_basis` | `float64` | Yes | SPY - ^SPX return spread |
| `vix_level` | `float64` | Yes | VIX level (optional) |
| `vix_change` | `float64` | Yes | 1-day VIX change |
| `price_z_5d` | `float64` | Yes | Z-score of momentum_5d |
| `price_z_20d` | `float64` | Yes | Z-score of momentum_20d |
| `vol_z` | `float64` | Yes | Z-score of rv_10d |
| `drawdown_z` | `float64` | Yes | Z-score of drawdown |

### News Features (15 columns)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `news_count_1d` | `int64` | Yes | News items published today (≤15:30 ET) |
| `news_count_z` | `float64` | Yes | Z-score vs 60d avg |
| `news_sentiment_mean` | `float64` | Yes | Mean sentiment (all items) |
| `news_sentiment_max` | `float64` | Yes | Max positive sentiment |
| `news_sentiment_min` | `float64` | Yes | Max negative sentiment |
| `news_sentiment_std` | `float64` | Yes | Sentiment volatility |
| `news_novelty_mean` | `float64` | Yes | Mean novelty score |
| `news_source_weight` | `float64` | Yes | Source-quality-weighted count |
| `news_finbert_mean` | `float64` | Yes | FinBERT sentiment mean |
| `news_gemini_mean` | `float64` | Yes | Gemini sentiment mean (if escalated) |
| `news_vader_mean` | `float64` | Yes | VADER sentiment mean |
| `news_event_earnings` | `bool` | Yes | Keyword: "earnings" mentioned |
| `news_event_fed` | `bool` | Yes | Keyword: "Fed" / "FOMC" mentioned |
| `news_event_macro` | `bool` | Yes | Keyword: "GDP" / "CPI" / "jobs" |
| `news_burst_flag` | `bool` | Yes | news_count_z > 2.0 |

### Social Features (15 columns)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `post_count_1d` | `int64` | Yes | Reddit posts today |
| `post_count_z` | `float64` | Yes | Z-score vs 60d avg |
| `comment_velocity` | `float64` | Yes | Comments per post |
| `social_sentiment_mean` | `float64` | Yes | Mean sentiment (all posts) |
| `social_sentiment_max` | `float64` | Yes | Max positive sentiment |
| `social_sentiment_min` | `float64` | Yes | Max negative sentiment |
| `social_novelty_mean` | `float64` | Yes | Mean novelty score |
| `social_cred_weighted_sent` | `float64` | Yes | Karma-weighted sentiment |
| `social_finbert_mean` | `float64` | Yes | FinBERT sentiment mean |
| `social_gemini_mean` | `float64` | Yes | Gemini sentiment mean |
| `social_vader_mean` | `float64` | Yes | VADER sentiment mean |
| `sarcasm_rate` | `float64` | Yes | % posts flagged as sarcastic |
| `social_burst_flag` | `bool` | Yes | post_count_z > 2.0 |
| `wsb_sentiment` | `float64` | Yes | r/wallstreetbets specific sentiment |
| `avg_author_karma` | `float64` | Yes | Mean karma of posters |

### Labels (3 columns)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `label_next_return` | `float64` | Yes | Next-day return (overnight for v1) |
| `label_next_excess_return` | `float64` | Yes | Next-day return - ^SPX return |
| `label_up_down` | `int8` | Yes | 1 if up, 0 if down |

### Metadata

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `feature_ts` | `timestamp` | No | When features computed |
| `data_completeness` | `float64` | No | % of expected data sources present (0-1) |

---

## Total Columns

**46 feature columns** + 3 labels + 4 metadata = **53 columns**

---

## Sample Row

```json
{
  "date": "2024-11-05",
  "symbol": "SPY",
  "momentum_5d": 0.012,
  "momentum_20d": 0.038,
  "news_count_z": 1.8,
  "news_sentiment_mean": 0.12,
  "post_count_z": 0.9,
  "social_sentiment_mean": 0.15,
  "label_next_return": 0.0082,
  "label_up_down": 1,
  "feature_ts": "2024-11-05T15:32:00-05:00",
  "data_completeness": 1.0
}
```

---

## Constraints

- Exactly 1 row per trading day
- NaN rate ≤5% per feature column
- Z-scores typically in [-5, 5] range
- Labels computed with correct lags (no leakage)

---

## Related Files

* `07-features/*.md` — Feature definitions
* `08-modeling/targets_labels.md` — Label construction

---

## Validation Script

```bash
python -m orbit.ops.validate_schema --source features --date 2024-11-05
```

**Validation checks:**
- Exactly 1 row per trading day
- All required columns present
- NaN rate ≤ 5% per feature
- Z-scores typically in [-5, 5]
- Label computed with correct lag
- `data_completeness` ∈ [0, 1]

**Example validation:**

```python
def validate_features(file_path):
    df = pd.read_parquet(file_path)
    errors = []
    
    # Row count
    if len(df) != 1:
        errors.append(f"Expected 1 row, got {len(df)}")
    
    # NaN rates
    nan_rates = df.isna().mean()
    high_nan = nan_rates[nan_rates > 0.05]
    if not high_nan.empty:
        errors.append(f"High NaN rates: {high_nan.to_dict()}")
    
    # Z-score ranges
    z_cols = [c for c in df.columns if '_z' in c]
    for col in z_cols:
        if df[col].abs().max() > 10:
            errors.append(f"{col} has extreme z-score: {df[col].max()}")
    
    # Data completeness
    if not (0 <= df['data_completeness'].iloc[0] <= 1):
        errors.append("data_completeness outside [0, 1]")
    
    return errors
```

---

## Common Access Patterns

### Load Single Day Features

```python
df = pd.read_parquet('data/features/2024/11/05/features_daily.parquet')
row = df.iloc[0]

# Access features
price_features = [c for c in df.columns if c.startswith('momentum') or c.startswith('rv')]
news_features = [c for c in df.columns if c.startswith('news_')]
social_features = [c for c in df.columns if c.startswith('post_') or c.startswith('social_')]
```

### Load Window for Training

```python
# Load 252 trading days for training
from datetime import datetime, timedelta

end_date = datetime(2024, 11, 5)
start_date = end_date - timedelta(days=365)  # Approximate, covers 252 trading days

df = pd.read_parquet(
    'data/features/',
    filters=[
        ('date', '>=', start_date.strftime('%Y-%m-%d')),
        ('date', '<=', end_date.strftime('%Y-%m-%d'))
    ]
)

# Sort and verify no gaps
df = df.sort_values('date')
assert len(df) >= 252, f"Insufficient data: {len(df)} rows"
```

### Split Features by Modality

```python
def split_features(df):
    """Split feature dataframe by modality."""
    price_cols = [c for c in df.columns if any(x in c for x in ['momentum', 'rv', 'drawdown', 'etf', 'vix', 'price_z'])]
    news_cols = [c for c in df.columns if c.startswith('news_')]
    social_cols = [c for c in df.columns if c.startswith('post_') or c.startswith('social_') or 'wsb' in c or 'sarcasm' in c]
    
    X_price = df[price_cols]
    X_news = df[news_cols]
    X_social = df[social_cols]
    
    return X_price, X_news, X_social

X_price, X_news, X_social = split_features(df)
```

### Compute Feature Importance

```python
# Analyze which features have highest correlation with label
correlations = df[[c for c in df.columns if not c.startswith('label_')]].corrwith(df['label_up_down'])
top_features = correlations.abs().sort_values(ascending=False).head(20)
```

### Check Data Quality

```python
# Check completeness over time
df['data_completeness'].plot(title='Data Completeness Over Time')

# Check NaN patterns
nan_summary = df.isna().sum().sort_values(ascending=False)
print("Features with most NaNs:")
print(nan_summary.head(10))

# Check for data gaps
date_range = pd.date_range(df['date'].min(), df['date'].max(), freq='B')  # Business days
missing_dates = set(date_range) - set(df['date'])
if missing_dates:
    print(f"Missing {len(missing_dates)} trading days")
```

### Prepare for Modeling

```python
# Standard ML prep
from sklearn.model_selection import train_test_split

# Drop metadata
feature_cols = [c for c in df.columns if c not in ['date', 'symbol', 'feature_ts', 'data_completeness'] and not c.startswith('label_')]
label_col = 'label_up_down'

X = df[feature_cols]
y = df[label_col]

# Handle NaNs
X = X.fillna(X.median())  # Or more sophisticated imputation

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)  # No shuffle for time series
```

---

---

