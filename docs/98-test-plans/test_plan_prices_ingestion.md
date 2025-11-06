# ORBIT — Test Plan: Price Ingestion Module

*Last edited: 2025-11-06*

## Module Under Test

`orbit.ingest.prices` — Stooq price data ingestion

---

## Test Scope

**In Scope:**
- CSV download from Stooq
- Schema validation
- Parquet conversion and storage
- Error handling and retries
- Price constraint validation

**Out of Scope:**
- Feature computation (covered in features test plan)
- Downstream processing

---

## Unit Tests

### Test 1.1: Download SPY Data

**Objective:** Verify successful CSV download for SPY

```python
def test_download_spy_csv():
    """Test downloading SPY.US CSV from Stooq."""
    from orbit.ingest.prices import fetch_stooq_csv
    
    df = fetch_stooq_csv('SPY.US', start_date='2024-11-01', end_date='2024-11-05')
    
    assert not df.empty, "Downloaded dataframe should not be empty"
    assert 'Date' in df.columns
    assert 'Close' in df.columns
    assert len(df) >= 1, "Should have at least 1 trading day"
```

### Test 1.2: Schema Validation

**Objective:** Ensure downloaded data matches expected schema

```python
def test_price_schema_validation():
    """Test schema validation for price data."""
    from orbit.ingest.prices import validate_price_schema
    import pandas as pd
    
    # Valid data
    valid_df = pd.DataFrame({
        'date': ['2024-11-05'],
        'symbol': ['SPY'],
        'open': [450.12],
        'high': [452.87],
        'low': [449.23],
        'close': [451.64],
        'volume': [85234567],
        'source': ['stooq'],
        'ingestion_ts': [pd.Timestamp.now()]
    })
    
    errors = validate_price_schema(valid_df)
    assert len(errors) == 0, f"Valid data should pass: {errors}"
    
    # Invalid data: high < low
    invalid_df = valid_df.copy()
    invalid_df['high'] = 440.0  # Below low
    
    errors = validate_price_schema(invalid_df)
    assert len(errors) > 0, "Should detect high < low violation"
```

### Test 1.3: Retry Logic

**Objective:** Test exponential backoff on failures

```python
def test_retry_on_network_error():
    """Test retry logic with exponential backoff."""
    from orbit.ingest.prices import fetch_with_retry
    from unittest.mock import patch, Mock
    
    mock_response = Mock()
    mock_response.status_code = 503  # Service unavailable
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        with pytest.raises(Exception):
            fetch_with_retry('http://test.com', max_retries=3)
        
        assert mock_get.call_count == 3, "Should retry 3 times"
```

### Test 1.4: Price Constraints

**Objective:** Validate price sanity checks

```python
def test_price_constraints():
    """Test OHLC price consistency constraints."""
    from orbit.ingest.prices import check_price_constraints
    
    # Valid OHLC
    valid = {'open': 100, 'high': 105, 'low': 98, 'close': 102}
    assert check_price_constraints(valid) == []
    
    # Invalid: high < open
    invalid1 = {'open': 100, 'high': 95, 'low': 90, 'close': 92}
    errors = check_price_constraints(invalid1)
    assert 'high < open' in str(errors)
    
    # Invalid: low > close
    invalid2 = {'open': 100, 'high': 105, 'low': 103, 'close': 102}
    errors = check_price_constraints(invalid2)
    assert 'low > close' in str(errors)
```

---

## Integration Tests

### Test 2.1: End-to-End Ingestion

**Objective:** Test complete ingestion pipeline

```python
def test_end_to_end_price_ingestion(tmp_path):
    """Test full ingestion: download → validate → store."""
    from orbit.ingest.prices import ingest_prices
    
    config = {
        'data_dir': str(tmp_path),
        'symbols': ['SPY.US'],
        'source': {'stooq': {'retries': 3}}
    }
    
    result = ingest_prices(config, date='2024-11-05')
    
    assert result['status'] == 'success'
    assert result['rows_ingested'] > 0
    
    # Check output file
    output_file = tmp_path / 'prices' / '2024' / '11' / '05' / 'SPY.parquet'
    assert output_file.exists()
    
    df = pd.read_parquet(output_file)
    assert len(df) == 1  # One row for the day
    assert df['symbol'].iloc[0] == 'SPY'
```

### Test 2.2: Multiple Symbols

**Objective:** Test ingesting multiple symbols in parallel

```python
def test_multiple_symbol_ingestion(tmp_path):
    """Test ingesting SPY, VOO, ^SPX."""
    from orbit.ingest.prices import ingest_prices
    
    config = {
        'data_dir': str(tmp_path),
        'symbols': ['SPY.US', 'VOO.US', '^SPX']
    }
    
    result = ingest_prices(config, date='2024-11-05')
    
    assert result['status'] == 'success'
    assert len(result['symbols_completed']) == 3
    
    # Check all files exist
    for symbol in ['SPY', 'VOO', 'SPX']:
        output_file = tmp_path / 'prices' / '2024' / '11' / '05' / f'{symbol}.parquet'
        assert output_file.exists(), f"{symbol} file missing"
```

### Test 2.3: Non-Trading Day Handling

**Objective:** Test behavior on weekends/holidays

```python
def test_non_trading_day():
    """Test ingestion on non-trading day (e.g., Sunday)."""
    from orbit.ingest.prices import ingest_prices
    
    result = ingest_prices(config, date='2024-11-03')  # Sunday
    
    assert result['status'] == 'skipped'
    assert 'non-trading day' in result['message'].lower()
```

---

## Performance Tests

### Test 3.1: Ingestion Speed

**Objective:** Verify ingestion completes within time budget

```python
def test_ingestion_performance():
    """Test that ingestion completes within 2 minutes."""
    import time
    from orbit.ingest.prices import ingest_prices
    
    start = time.time()
    result = ingest_prices(config, date='2024-11-05')
    duration = time.time() - start
    
    assert duration < 120, f"Ingestion took {duration}s, exceeds 2min limit"
```

### Test 3.2: Rate Limit Compliance

**Objective:** Ensure polite delay respected

```python
def test_rate_limit_compliance():
    """Test polite delay between requests."""
    from orbit.ingest.prices import ingest_prices
    from unittest.mock import patch
    import time
    
    delays = []
    original_get = requests.get
    
    def tracked_get(*args, **kwargs):
        delays.append(time.time())
        return original_get(*args, **kwargs)
    
    with patch('requests.get', side_effect=tracked_get):
        ingest_prices(config, symbols=['SPY.US', 'VOO.US'])
    
    # Check delays between requests
    if len(delays) > 1:
        gaps = [delays[i+1] - delays[i] for i in range(len(delays)-1)]
        assert all(g >= 0.9 for g in gaps), "Should have ≥1s delay between requests"
```

---

## Data Quality Tests

### Test 4.1: No Duplicate Dates

**Objective:** Ensure no duplicate (date, symbol) pairs

```python
def test_no_duplicate_dates(tmp_path):
    """Test that re-running ingestion doesn't create duplicates."""
    from orbit.ingest.prices import ingest_prices
    
    # Run twice
    ingest_prices(config, date='2024-11-05')
    ingest_prices(config, date='2024-11-05')
    
    output_file = tmp_path / 'prices' / '2024' / '11' / '05' / 'SPY.parquet'
    df = pd.read_parquet(output_file)
    
    duplicates = df.duplicated(subset=['date', 'symbol'])
    assert duplicates.sum() == 0, "Should not have duplicate rows"
```

### Test 4.2: Timestamp Accuracy

**Objective:** Verify ingestion_ts is set correctly

```python
def test_ingestion_timestamp():
    """Test that ingestion_ts is within reasonable bounds."""
    import pandas as pd
    from orbit.ingest.prices import ingest_prices
    
    before = pd.Timestamp.now(tz='America/New_York')
    result = ingest_prices(config, date='2024-11-05')
    after = pd.Timestamp.now(tz='America/New_York')
    
    df = pd.read_parquet(result['output_file'])
    ingestion_ts = df['ingestion_ts'].iloc[0]
    
    assert before <= ingestion_ts <= after, "ingestion_ts should be during test run"
```

---

## Error Handling Tests

### Test 5.1: Network Timeout

**Objective:** Test graceful handling of network timeouts

```python
def test_network_timeout():
    """Test handling of network timeout."""
    from orbit.ingest.prices import ingest_prices
    from unittest.mock import patch
    import requests
    
    with patch('requests.get', side_effect=requests.Timeout):
        result = ingest_prices(config, date='2024-11-05')
        
        assert result['status'] == 'failed'
        assert 'timeout' in result['error'].lower()
```

### Test 5.2: Invalid CSV Format

**Objective:** Test handling of malformed CSV

```python
def test_invalid_csv_format():
    """Test handling of unexpected CSV format."""
    from orbit.ingest.prices import parse_stooq_csv
    
    # Malformed CSV missing 'Close' column
    bad_csv = "Date,Open,High\n2024-11-05,100,105\n"
    
    with pytest.raises(ValueError, match="Missing required column"):
        parse_stooq_csv(bad_csv)
```

### Test 5.3: Disk Space Exhaustion

**Objective:** Test behavior when disk full

```python
def test_disk_space_error():
    """Test handling of disk full condition."""
    from orbit.ingest.prices import ingest_prices
    from unittest.mock import patch
    
    with patch('pandas.DataFrame.to_parquet', side_effect=OSError("No space left")):
        result = ingest_prices(config, date='2024-11-05')
        
        assert result['status'] == 'failed'
        assert 'disk' in result['error'].lower() or 'space' in result['error'].lower()
```

---

## Acceptance Criteria

- [ ] All unit tests pass (100% coverage for core functions)
- [ ] Integration tests pass for single and multiple symbols
- [ ] Performance: Ingestion completes in <2 minutes for 1 day
- [ ] No data quality issues (duplicates, missing timestamps, invalid prices)
- [ ] Error handling: Graceful failures with clear error messages
- [ ] Rate limits: Polite delay respected (≥1s between requests)
- [ ] Documentation: Test results logged to `tests/results/prices_ingestion.log`

---

## Related Files

* `04-data-sources/stooq_prices.md` — Data source specification
* `05-ingestion/prices_stooq_ingest.md` — Module implementation
* `12-schemas/prices.parquet.schema.md` — Schema definition
* `99-templates/TEMPLATE_test_plan.md` — Test plan template
