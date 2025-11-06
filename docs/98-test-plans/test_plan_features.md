# ORBIT — Test Plan: Feature Computation

*Last edited: 2025-11-06*

## Module Under Test

`orbit.features` — Price, news, social feature computation

---

## Test Scope

**In Scope:**
- Price technical indicators (returns, volatility, momentum)
- News features (sentiment scores, counts)
- Social features (engagement, credibility)
- Time alignment to 4pm cutoffs
- Standardization and scaling

**Out of Scope:**
- Raw data ingestion (covered in ingestion test plans)
- Model training (covered in modeling test plan)

---

## Unit Tests: Price Features

### Test 1.1: Log Return Computation

**Objective:** Verify log returns calculated correctly

```python
def test_log_returns():
    """Test log return calculation."""
    from orbit.features.price import compute_log_returns
    import pandas as pd
    import numpy as np
    
    df = pd.DataFrame({
        'date': pd.date_range('2024-11-01', periods=5),
        'close': [100, 102, 101, 103, 105]
    })
    
    result = compute_log_returns(df)
    
    expected_return = np.log(102 / 100)
    assert np.isclose(result['log_return'].iloc[1], expected_return)
    assert pd.isna(result['log_return'].iloc[0]), "First row should be NaN"
```

### Test 1.2: Volatility (20-day)

**Objective:** Test rolling volatility calculation

```python
def test_volatility_20d():
    """Test 20-day rolling volatility."""
    from orbit.features.price import compute_volatility
    import pandas as pd
    import numpy as np
    
    # Synthetic data with known volatility
    np.random.seed(42)
    returns = np.random.normal(0, 0.02, 100)  # 2% daily vol
    
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'log_return': returns
    })
    
    result = compute_volatility(df, window=20)
    
    # Check shape
    assert len(result) == 100
    
    # First 19 rows should be NaN
    assert pd.isna(result['volatility_20d'].iloc[:19]).all()
    
    # Volatility should be ~0.02
    mean_vol = result['volatility_20d'].iloc[19:].mean()
    assert 0.015 < mean_vol < 0.025, f"Mean vol {mean_vol} outside expected range"
```

### Test 1.3: RSI (14-day)

**Objective:** Test RSI indicator

```python
def test_rsi_14d():
    """Test 14-day RSI calculation."""
    from orbit.features.price import compute_rsi
    import pandas as pd
    
    # Uptrend: RSI should be >50
    uptrend = pd.DataFrame({
        'date': pd.date_range('2024-11-01', periods=20),
        'close': list(range(100, 120))  # Consistent uptrend
    })
    
    result = compute_rsi(uptrend, window=14)
    
    rsi_value = result['rsi_14d'].iloc[-1]
    assert 70 < rsi_value < 100, f"Uptrend RSI {rsi_value} should be >70"
    
    # Downtrend: RSI should be <50
    downtrend = pd.DataFrame({
        'date': pd.date_range('2024-11-01', periods=20),
        'close': list(range(120, 100, -1))
    })
    
    result = compute_rsi(downtrend, window=14)
    
    rsi_value = result['rsi_14d'].iloc[-1]
    assert 0 < rsi_value < 30, f"Downtrend RSI {rsi_value} should be <30"
```

---

## Unit Tests: News Features

### Test 2.1: Sentiment Aggregation

**Objective:** Test weighted sentiment calculation

```python
def test_news_sentiment_aggregation():
    """Test aggregating news sentiment with recency weighting."""
    from orbit.features.news import aggregate_sentiment
    import pandas as pd
    
    # Articles with timestamps and sentiments
    df = pd.DataFrame({
        'published_at': pd.to_datetime([
            '2024-11-05 10:00:00',
            '2024-11-05 12:00:00',
            '2024-11-05 15:00:00'
        ], utc=True),
        'sentiment_score': [0.8, -0.3, 0.5],
        'relevance': [0.9, 0.7, 1.0]
    })
    
    # Cutoff at 4pm ET (9pm UTC)
    cutoff = pd.Timestamp('2024-11-05 21:00:00', tz='UTC')
    
    result = aggregate_sentiment(df, cutoff)
    
    # More recent article (15:00) should have higher weight
    assert result['sentiment_weighted'] > 0, "Weighted sentiment should be positive"
    assert result['news_count'] == 3
    assert 0 < result['sentiment_std'] < 1
```

### Test 2.2: Burst Detection (Z-score)

**Objective:** Test news count z-score calculation

```python
def test_news_burst_detection():
    """Test burst detection via z-score."""
    from orbit.features.news import compute_news_burst
    import pandas as pd
    
    # Historical baseline: ~10 articles/day
    baseline = pd.DataFrame({
        'date': pd.date_range('2024-10-01', periods=30),
        'news_count': [10]*29 + [50]  # Spike on last day
    })
    
    result = compute_news_burst(baseline, window=20)
    
    # Last day should have high z-score
    z_score = result['news_count_z'].iloc[-1]
    assert z_score > 3, f"Spike should have z-score >3, got {z_score}"
    
    # Normal days should have z-score ~0
    normal_z = result['news_count_z'].iloc[-10:-1].mean()
    assert abs(normal_z) < 0.5, f"Normal days should have z~0, got {normal_z}"
```

### Test 2.3: Entity Extraction

**Objective:** Test extracting tickers from headlines

```python
def test_entity_extraction():
    """Test extracting ticker symbols from text."""
    from orbit.features.news import extract_entities
    
    headline = "AAPL surges 5% as iPhone sales beat, $SPY hits new high"
    
    entities = extract_entities(headline)
    
    assert 'AAPL' in entities, "Should extract AAPL"
    assert 'SPY' in entities, "Should extract SPY (with cashtag)"
    assert len(entities) == 2
```

---

## Unit Tests: Social Features

### Test 3.1: Credibility Weighting

**Objective:** Test weighting by author credibility

```python
def test_credibility_weighting():
    """Test credibility-weighted sentiment."""
    from orbit.features.social import compute_credibility_weighted_sentiment
    import pandas as pd
    
    df = pd.DataFrame({
        'author': ['expert_trader', 'new_user', 'verified_analyst'],
        'karma': [15000, 10, 8000],
        'account_age_days': [1200, 5, 900],
        'sentiment': [0.8, -0.9, 0.6]
    })
    
    result = compute_credibility_weighted_sentiment(df)
    
    # High-credibility positive sentiment should dominate
    assert result['sentiment_weighted'] > 0
    assert result['sentiment_weighted'] > result['sentiment_raw']
```

### Test 3.2: Sarcasm Detection

**Objective:** Test sarcasm flag adjusts sentiment

```python
def test_sarcasm_detection():
    """Test sarcasm adjusts sentiment."""
    from orbit.features.social import detect_sarcasm
    
    sarcastic_text = "Oh great, SPY is down again. What a shock. 🙄"
    normal_text = "SPY is performing well today"
    
    assert detect_sarcasm(sarcastic_text) == True
    assert detect_sarcasm(normal_text) == False
```

### Test 3.3: Subreddit-Specific Features

**Objective:** Test subreddit segmentation

```python
def test_subreddit_features():
    """Test computing features per subreddit."""
    from orbit.features.social import compute_subreddit_features
    import pandas as pd
    
    df = pd.DataFrame({
        'subreddit': ['wallstreetbets', 'wallstreetbets', 'stocks', 'stocks'],
        'upvotes': [1200, 800, 150, 200],
        'sentiment': [0.9, -0.3, 0.4, 0.5]
    })
    
    result = compute_subreddit_features(df)
    
    assert 'wsb_sentiment' in result
    assert 'stocks_sentiment' in result
    assert result['wsb_count'] == 2
    assert result['stocks_count'] == 2
```

---

## Integration Tests

### Test 4.1: End-to-End Feature Computation

**Objective:** Test full pipeline for one day

```python
def test_end_to_end_features(tmp_path):
    """Test computing all features for 2024-11-05."""
    from orbit.features import compute_daily_features
    
    config = {
        'data_dir': str(tmp_path),
        'cutoff_time': '16:00:00',
        'timezone': 'America/New_York'
    }
    
    # Prepare mock data
    setup_mock_data(tmp_path, date='2024-11-05')
    
    result = compute_daily_features(config, date='2024-11-05')
    
    assert result['status'] == 'success'
    
    # Load output
    output_file = tmp_path / 'features_daily' / '2024' / '11' / '05' / 'features.parquet'
    df = pd.read_parquet(output_file)
    
    # Check all feature categories present
    assert 'log_return' in df.columns
    assert 'sentiment_news' in df.columns
    assert 'sentiment_social' in df.columns
    assert 'news_count_z' in df.columns
    assert len(df) == 3  # SPY, VOO, ^SPX
```

### Test 4.2: Multi-Day Feature Computation

**Objective:** Test batch processing multiple days

```python
def test_multi_day_features(tmp_path):
    """Test computing features for 5 consecutive days."""
    from orbit.features import compute_daily_features
    
    dates = pd.date_range('2024-11-01', periods=5, freq='B')  # Business days
    
    for date in dates:
        setup_mock_data(tmp_path, date=date.strftime('%Y-%m-%d'))
        result = compute_daily_features(config, date=date.strftime('%Y-%m-%d'))
        assert result['status'] == 'success'
    
    # Check all 5 days have output
    for date in dates:
        output_file = tmp_path / 'features_daily' / date.strftime('%Y/%m/%d') / 'features.parquet'
        assert output_file.exists(), f"Missing features for {date}"
```

---

## Data Quality Tests

### Test 5.1: No Missing Values in Key Features

**Objective:** Ensure critical features have no NaNs

```python
def test_no_missing_critical_features():
    """Test that critical features have no missing values."""
    from orbit.features import compute_daily_features
    
    result = compute_daily_features(config, date='2024-11-05')
    df = pd.read_parquet(result['output_file'])
    
    critical_features = [
        'log_return',
        'volatility_20d',
        'sentiment_news',
        'sentiment_social',
        'news_count'
    ]
    
    for feat in critical_features:
        missing = df[feat].isna().sum()
        assert missing == 0, f"Feature {feat} has {missing} missing values"
```

### Test 5.2: Feature Value Ranges

**Objective:** Validate features within expected bounds

```python
def test_feature_value_ranges():
    """Test that features fall within expected ranges."""
    from orbit.features import compute_daily_features
    
    result = compute_daily_features(config, date='2024-11-05')
    df = pd.read_parquet(result['output_file'])
    
    # Sentiment scores: [-1, 1]
    assert (df['sentiment_news'] >= -1).all() and (df['sentiment_news'] <= 1).all()
    assert (df['sentiment_social'] >= -1).all() and (df['sentiment_social'] <= 1).all()
    
    # Volatility: positive
    assert (df['volatility_20d'] > 0).all()
    
    # RSI: [0, 100]
    assert (df['rsi_14d'] >= 0).all() and (df['rsi_14d'] <= 100).all()
    
    # Counts: non-negative integers
    assert (df['news_count'] >= 0).all()
    assert (df['post_count'] >= 0).all()
```

### Test 5.3: Standardization Check

**Objective:** Verify z-scores have mean~0, std~1

```python
def test_standardization():
    """Test that standardized features have correct statistics."""
    from orbit.features import compute_daily_features
    import pandas as pd
    
    # Compute features for 30 days to test standardization
    dates = pd.date_range('2024-10-01', periods=30, freq='B')
    
    dfs = []
    for date in dates:
        setup_mock_data(tmp_path, date=date.strftime('%Y-%m-%d'))
        result = compute_daily_features(config, date=date.strftime('%Y-%m-%d'))
        df = pd.read_parquet(result['output_file'])
        dfs.append(df)
    
    all_features = pd.concat(dfs)
    
    # Check z-scored features
    for col in ['news_count_z', 'post_count_z']:
        mean = all_features[col].mean()
        std = all_features[col].std()
        
        assert abs(mean) < 0.1, f"{col} mean {mean} should be ~0"
        assert 0.9 < std < 1.1, f"{col} std {std} should be ~1"
```

---

## Performance Tests

### Test 6.1: Computation Speed

**Objective:** Verify feature computation completes in time budget

```python
def test_feature_computation_speed():
    """Test that feature computation completes within 5 minutes."""
    import time
    from orbit.features import compute_daily_features
    
    start = time.time()
    result = compute_daily_features(config, date='2024-11-05')
    duration = time.time() - start
    
    assert duration < 300, f"Feature computation took {duration}s, exceeds 5min limit"
```

### Test 6.2: Memory Usage

**Objective:** Ensure memory usage stays reasonable

```python
def test_memory_usage():
    """Test memory usage during feature computation."""
    import psutil
    import os
    from orbit.features import compute_daily_features
    
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / 1024**2  # MB
    
    result = compute_daily_features(config, date='2024-11-05')
    
    mem_after = process.memory_info().rss / 1024**2
    mem_increase = mem_after - mem_before
    
    assert mem_increase < 1024, f"Memory increased by {mem_increase}MB, exceeds 1GB limit"
```

---

## Acceptance Criteria

- [ ] All unit tests pass (price, news, social features)
- [ ] Integration test: Full pipeline completes successfully
- [ ] Data quality: No missing values in critical features
- [ ] Data quality: All features within expected ranges
- [ ] Performance: Computation completes in <5 minutes
- [ ] Memory: Peak usage <1GB increase
- [ ] Standardization: Z-scores have mean~0, std~1
- [ ] Documentation: Test results logged to `tests/results/features.log`

---

## Related Files

* `07-features/price_features.md` — Price feature specifications
* `07-features/news_features.md` — News feature specifications
* `07-features/social_features.md` — Social feature specifications
* `07-features/standardization_scaling.md` — Normalization approach
* `12-schemas/features_daily.parquet.schema.md` — Output schema
* `99-templates/TEMPLATE_test_plan.md` — Test plan template
