# Testing Guidelines

*Last edited: 2025-11-15*

**Purpose**: Comprehensive testing strategy for ORBIT, including unit tests, integration tests, and validation procedures.

---

## Testing Philosophy

ORBIT follows a **test-driven development (TDD)** approach where possible:

1. **Unit tests**: Test individual functions and classes in isolation
2. **Integration tests**: Test interactions between modules
3. **M0 sample tests**: Run full pipeline with synthetic data (no external APIs)
4. **Acceptance tests**: Validate against spec acceptance checklists
5. **Backtests**: Historical validation using real data

---

## Test Organization

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_io.py               # Parquet I/O utilities
├── test_config.py           # Configuration management
├── test_ingestion/          # Ingestion module tests
│   ├── test_prices.py       # Stooq price ingestion
│   ├── test_news_ws.py      # Alpaca WebSocket news
│   ├── test_news_backfill.py
│   └── test_llm_gemini.py   # Gemini sentiment scoring
├── test_preprocessing/      # Preprocessing tests
│   ├── test_deduplication.py
│   └── test_time_alignment.py
├── test_features/           # Feature engineering tests
│   ├── test_price_features.py
│   └── test_news_features.py
└── test_integration/        # End-to-end integration tests
    └── test_m0_pipeline.py  # M0 sample data pipeline
```

---

## Running Tests

### Basic Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_io.py -v

# Run specific test function
pytest tests/test_io.py::test_write_parquet -v

# Run tests matching pattern
pytest tests/ -v -k "test_news"
```

---

### Test Markers

Use markers to categorize tests:

```python
import pytest

@pytest.mark.m0
def test_sample_data_generation():
    """Test M0 sample data generation (no external APIs)."""
    pass

@pytest.mark.integration
def test_news_ingestion_pipeline():
    """Test full news ingestion pipeline."""
    pass

@pytest.mark.slow
def test_backfill_10_years():
    """Test 10-year historical backfill (takes 1+ hours)."""
    pass

@pytest.mark.requires_api
def test_alpaca_websocket():
    """Test Alpaca WebSocket connection (requires API key)."""
    pass
```

**Run specific markers:**
```bash
# Run only M0 tests (no external APIs)
pytest tests/ -v -m m0

# Run only integration tests
pytest tests/ -v -m integration

# Skip slow tests
pytest tests/ -v -m "not slow"

# Skip tests requiring API keys
pytest tests/ -v -m "not requires_api"
```

---

### Coverage Reports

```bash
# Run tests with coverage
pytest tests/ --cov=src/orbit --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Coverage targets:**
- **Unit tests**: 80%+ coverage
- **Critical paths** (ingestion, feature engineering): 90%+ coverage
- **Utilities**: 70%+ coverage

---

### Verbose Output

```bash
# Show print statements
pytest tests/ -v -s

# Show full diff on assertion failures
pytest tests/ -v --tb=long

# Show short traceback (useful for many failures)
pytest tests/ -v --tb=short
```

---

## Writing Tests

### Unit Test Structure

```python
import pytest
import pandas as pd
from orbit.utils.io import write_parquet, read_parquet

def test_write_parquet(tmp_path):
    """Test writing DataFrame to Parquet."""
    # Arrange: Create test data
    df = pd.DataFrame({
        "date": ["2025-01-01", "2025-01-02"],
        "symbol": ["SPY", "SPY"],
        "close": [500.0, 505.0]
    })
    output_path = tmp_path / "test.parquet"

    # Act: Call function
    write_parquet(df, output_path)

    # Assert: Verify results
    assert output_path.exists()
    df_read = read_parquet(output_path)
    pd.testing.assert_frame_equal(df, df_read)

def test_write_parquet_empty_dataframe(tmp_path):
    """Test writing empty DataFrame raises error."""
    df = pd.DataFrame()
    output_path = tmp_path / "empty.parquet"

    with pytest.raises(ValueError, match="Cannot write empty DataFrame"):
        write_parquet(df, output_path)
```

---

### Fixtures

Use fixtures for reusable test data and setup:

```python
# conftest.py
import pytest
import pandas as pd
from pathlib import Path

@pytest.fixture
def sample_news_df():
    """Sample news DataFrame for testing."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "headline": ["News 1", "News 2", "News 3"],
        "created_at": pd.to_datetime([
            "2025-01-01 10:00:00",
            "2025-01-01 11:00:00",
            "2025-01-01 12:00:00"
        ]),
        "symbols": [["SPY"], ["VOO"], ["SPY", "VOO"]]
    })

@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "raw").mkdir()
    (data_dir / "curated").mkdir()
    return data_dir

# test_ingestion/test_news.py
def test_filter_by_symbol(sample_news_df):
    """Test filtering news by symbol."""
    result = filter_news_by_symbol(sample_news_df, "SPY")
    assert len(result) == 2  # Articles 1 and 3
    assert all("SPY" in symbols for symbols in result["symbols"])
```

---

### Mocking External APIs

Use `unittest.mock` or `pytest-mock` to mock API calls:

```python
from unittest.mock import Mock, patch
import pytest

@patch("orbit.ingest.news_ws.websocket.WebSocketApp")
def test_websocket_connection(mock_ws):
    """Test WebSocket connection (mocked)."""
    # Arrange: Mock WebSocket
    mock_ws_instance = Mock()
    mock_ws.return_value = mock_ws_instance

    # Act: Connect
    ingester = NewsIngester(api_key="test_key")
    ingester.connect()

    # Assert: WebSocket was created with correct URL
    mock_ws.assert_called_once()
    assert "wss://stream.data.alpaca.markets" in mock_ws.call_args[0][0]

@pytest.mark.requires_api
def test_alpaca_rest_api_real():
    """Test Alpaca REST API with real credentials."""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("ALPACA_API_KEY_1")
    if not api_key:
        pytest.skip("ALPACA_API_KEY_1 not set")

    # Test real API call
    client = AlpacaClient(api_key)
    news = client.get_news("SPY", "2024-01-01", "2024-01-01")
    assert isinstance(news, list)
```

---

### Parametrized Tests

Test multiple inputs with `@pytest.mark.parametrize`:

```python
@pytest.mark.parametrize("symbol,expected_count", [
    ("SPY", 2),
    ("VOO", 2),
    ("AAPL", 0),
])
def test_filter_by_symbol_parametrized(sample_news_df, symbol, expected_count):
    """Test filtering news by various symbols."""
    result = filter_news_by_symbol(sample_news_df, symbol)
    assert len(result) == expected_count

@pytest.mark.parametrize("date,cutoff_hour,expected_count", [
    ("2025-01-01", 11, 1),  # Before 11:00, only 1 article
    ("2025-01-01", 12, 2),  # Before 12:00, 2 articles
    ("2025-01-01", 15, 3),  # Before 15:00, all 3 articles
])
def test_cutoff_filtering(sample_news_df, date, cutoff_hour, expected_count):
    """Test news cutoff at various times."""
    result = filter_by_cutoff(sample_news_df, date, cutoff_hour)
    assert len(result) == expected_count
```

---

## Integration Tests

### M0 Pipeline Test

Test the full pipeline with sample data (no external APIs):

```python
# tests/test_integration/test_m0_pipeline.py
import pytest
import subprocess
from pathlib import Path

@pytest.mark.m0
@pytest.mark.integration
def test_m0_full_pipeline(temp_data_dir, monkeypatch):
    """Test full M0 pipeline with synthetic data."""
    # Set ORBIT_DATA_DIR to temp directory
    monkeypatch.setenv("ORBIT_DATA_DIR", str(temp_data_dir))

    # Generate sample data
    result = subprocess.run(
        ["python", "src/orbit/utils/generate_samples.py"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0

    # Run ingestion with sample data
    result = subprocess.run(
        ["orbit", "ingest", "--local-sample"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0

    # Verify output files exist
    assert (temp_data_dir / "raw/prices/SPY.US.parquet").exists()
    assert (temp_data_dir / "raw/news/date=2024-01-01/news.parquet").exists()
```

---

### CLI Tests

Test CLI commands:

```python
import subprocess

def test_cli_help():
    """Test CLI help output."""
    result = subprocess.run(
        ["orbit", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "ORBIT" in result.stdout
    assert "ingest" in result.stdout

def test_cli_ingest_prices_dry_run():
    """Test prices ingestion (dry run)."""
    result = subprocess.run(
        ["orbit", "ingest", "prices", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

---

## Acceptance Testing

### Module Acceptance Checklists

Each module has an acceptance checklist in `docs/`. Run these manually after changes:

**Example: News Ingestion Acceptance Checklist**

From `docs/05-ingestion/news_alpaca_ws_ingest.md`:

```markdown
## Acceptance Checklist (M1)

* [ ] Can you connect to Alpaca WebSocket without errors?
* [ ] Are news articles deduplicated by ID?
* [ ] Does graceful shutdown flush buffer to disk?
* [ ] Are articles partitioned by date in Parquet format?
* [ ] Does the system respect rate limits (no 429 errors)?
```

**How to validate:**

```bash
# 1. Run WebSocket ingestion for 5 minutes
timeout 300 orbit ingest news --symbols SPY VOO

# 2. Check output
ls -lh data/raw/news/date=*/

# 3. Verify deduplication
python -c "
import pandas as pd
from pathlib import Path

for parquet in Path('data/raw/news').rglob('news.parquet'):
    df = pd.read_parquet(parquet)
    duplicates = df['id'].duplicated().sum()
    print(f'{parquet}: {len(df)} articles, {duplicates} duplicates')
    assert duplicates == 0, f'Found duplicates in {parquet}'
"

# 4. Check logs for errors
grep -i "error\|429" logs/ingestion_news_*.log
```

---

## Backtesting Validation

### Historical Data Validation

Validate historical backfill completeness:

```bash
# tests/validation/validate_backfill.py
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

def validate_date_coverage(start: str, end: str, data_dir: Path):
    """Validate that all dates in range have data."""
    expected_dates = pd.date_range(start, end, freq="D")
    actual_dates = [
        datetime.strptime(d.name.replace("date=", ""), "%Y-%m-%d")
        for d in (data_dir / "raw/news").glob("date=*")
    ]

    missing = set(expected_dates) - set(pd.to_datetime(actual_dates))

    # Filter out weekends (expected to have no data)
    missing_weekdays = [d for d in missing if d.weekday() < 5]

    if missing_weekdays:
        print(f"Missing {len(missing_weekdays)} weekdays:")
        for d in sorted(missing_weekdays)[:10]:
            print(f"  {d.strftime('%Y-%m-%d')}")
        return False

    print(f"✓ All {len(expected_dates)} dates covered")
    return True

if __name__ == "__main__":
    validate_date_coverage("2015-01-01", "2025-11-15", Path("data"))
```

Run validation:

```bash
python tests/validation/validate_backfill.py
```

---

### Point-in-Time Leak Detection

Ensure no future data leaks into features:

```python
# tests/validation/test_point_in_time.py
import pandas as pd
import pytest

def test_news_cutoff_respected():
    """Verify news cutoff at 15:30 ET is respected."""
    # Load features for a specific date
    features = pd.read_parquet("data/features/features_daily.parquet")
    date = "2024-01-15"
    row = features[features["date"] == date].iloc[0]

    # Load raw news for that date
    news = pd.read_parquet(f"data/raw/news/date={date}/news.parquet")

    # Check that only news before 15:30 ET was used
    cutoff = pd.Timestamp(date).replace(hour=15, minute=30, tz="US/Eastern")
    news_before_cutoff = news[news["created_at"] <= cutoff]

    # Feature should be computed from news_before_cutoff only
    expected_sentiment = news_before_cutoff["sentiment"].mean()
    assert abs(row["sentiment_mean"] - expected_sentiment) < 0.01

def test_no_forward_looking_bias():
    """Ensure features at time T don't use data from T+1."""
    features = pd.read_parquet("data/features/features_daily.parquet")

    for i in range(len(features) - 1):
        row_t = features.iloc[i]
        row_t1 = features.iloc[i + 1]

        # Features at T should not depend on prices at T+1
        assert row_t["date"] < row_t1["date"]
```

---

## Performance Testing

### Benchmark Tests

```python
import time
import pytest

@pytest.mark.slow
def test_parquet_write_performance(tmp_path):
    """Benchmark Parquet write performance."""
    import pandas as pd
    import numpy as np

    # Generate large DataFrame (1M rows)
    df = pd.DataFrame({
        "id": np.arange(1_000_000),
        "value": np.random.randn(1_000_000),
        "category": np.random.choice(["A", "B", "C"], 1_000_000)
    })

    output_path = tmp_path / "benchmark.parquet"

    # Benchmark write
    start = time.time()
    df.to_parquet(output_path, engine="pyarrow", compression="snappy")
    elapsed = time.time() - start

    # Should write 1M rows in < 1 second
    assert elapsed < 1.0, f"Write took {elapsed:.2f}s (expected < 1.0s)"

    # Verify file size (compressed)
    file_size_mb = output_path.stat().st_size / (1024 ** 2)
    assert file_size_mb < 10, f"File size {file_size_mb:.2f} MB too large"
```

---

## Continuous Integration (CI)

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: 3.11

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run M0 tests (no API keys)
      run: |
        pytest tests/ -v -m m0 --cov=src/orbit --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## Test Data Management

### Sample Data Generation

Generate synthetic data for testing:

```python
# src/orbit/utils/generate_samples.py
import pandas as pd
from pathlib import Path

def generate_sample_prices(output_dir: Path):
    """Generate sample price data."""
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D")
    df = pd.DataFrame({
        "date": dates,
        "open": 500 + np.random.randn(len(dates)).cumsum(),
        "high": 505 + np.random.randn(len(dates)).cumsum(),
        "low": 495 + np.random.randn(len(dates)).cumsum(),
        "close": 500 + np.random.randn(len(dates)).cumsum(),
        "volume": np.random.randint(50_000_000, 100_000_000, len(dates))
    })

    output_path = output_dir / "raw/prices/SPY.US.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

def generate_sample_news(output_dir: Path):
    """Generate sample news data."""
    for date in pd.date_range("2024-01-01", "2024-12-31", freq="D"):
        date_str = date.strftime("%Y-%m-%d")
        num_articles = np.random.randint(10, 50)

        df = pd.DataFrame({
            "id": range(num_articles),
            "headline": [f"News {i} for {date_str}" for i in range(num_articles)],
            "created_at": [date + pd.Timedelta(minutes=i*10) for i in range(num_articles)],
            "symbols": [["SPY"] for _ in range(num_articles)]
        })

        output_path = output_dir / f"raw/news/date={date_str}/news.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)

if __name__ == "__main__":
    data_dir = Path(os.getenv("ORBIT_DATA_DIR", "./data"))
    generate_sample_prices(data_dir)
    generate_sample_news(data_dir)
    print(f"✓ Sample data generated in {data_dir}")
```

---

## Test Documentation

Every test should have a clear docstring:

```python
def test_deduplicate_news_by_id():
    """
    Test deduplication of news articles by ID.

    Scenario:
        - Given a DataFrame with duplicate article IDs
        - When deduplicate_news() is called
        - Then only unique articles remain (keeping first occurrence)

    Related spec: docs/06-preprocessing/deduplication_novelty.md
    """
    pass
```

---

## Related Documentation

- [test_plan_prices_ingestion.md](../98-test-plans/test_plan_prices_ingestion.md) - Prices ingestion test plan
- [test_plan_features.md](../98-test-plans/test_plan_features.md) - Features test plan
- [test_plan_modeling.md](../98-test-plans/test_plan_modeling.md) - Modeling test plan
- [05_development_workflow.md](05_development_workflow.md) - Development practices
- [acceptance_gates.md](../09-evaluation/acceptance_gates.md) - Acceptance criteria
