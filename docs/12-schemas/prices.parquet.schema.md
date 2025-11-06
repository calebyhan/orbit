# ORBIT — prices.parquet

*Last edited: 2025-11-05*

## Purpose

Define the **canonical schema** for price data (SPY, VOO, ^SPX) stored in Parquet format. This schema is enforced at ingestion and validated before downstream processing.

---

## File Location

**Path pattern:** `data/prices/YYYY/MM/DD/<symbol>.parquet`

**Example:** `data/prices/2024/11/05/spy.parquet`

---

## Schema

| Column | Type | Nullable | Description | Constraints |
|--------|------|----------|-------------|-------------|
| `date` | `date` | No | Trading date (YYYY-MM-DD) | Must be a valid trading day |
| `symbol` | `string` | No | Ticker symbol | One of: `SPY`, `VOO`, `^SPX` |
| `open` | `float64` | No | Opening price ($) | > 0 |
| `high` | `float64` | No | High price ($) | ≥ open, close, low |
| `low` | `float64` | No | Low price ($) | ≤ open, close, high |
| `close` | `float64` | No | Closing price ($) | > 0 |
| `volume` | `int64` | No | Trading volume (shares) | ≥ 0 |
| `adjusted_close` | `float64` | Yes | Adjusted for splits/dividends | > 0 (if present) |
| `source` | `string` | No | Data source | e.g., `stooq`, `yahoo` |
| `ingestion_ts` | `timestamp` | No | When ingested (ET) | ISO-8601 with timezone |

---

## Constraints (Validation Rules)

### Price Consistency

```python
assert high >= open
assert high >= close
assert high >= low
assert low <= open
assert low <= close
assert low > 0
```

### Daily Return Sanity

```python
daily_return = (close / prev_close) - 1
assert abs(daily_return) < 0.20  # Flag if >20% move (flash crash?)
```

### Volume

```python
assert volume >= 0  # Can be 0 on very low-liquidity days
```

---

## Sample Row

```json
{
  "date": "2024-11-05",
  "symbol": "SPY",
  "open": 450.12,
  "high": 452.87,
  "low": 449.23,
  "close": 451.64,
  "volume": 85234567,
  "adjusted_close": 451.64,
  "source": "stooq",
  "ingestion_ts": "2024-11-05T16:10:23-05:00"
}
```

---

## Partitioning

**Strategy:** By date (YYYY/MM/DD)

**Rationale:** Supports fast date-range queries; aligns with daily pipeline.

---

## Compression

**Format:** Snappy (default for Parquet)

**Rationale:** Good balance of compression ratio and read speed.

---

## Indexing

**Row groups:** 1 per file (small files, ~1-3 rows per day)

**Sorting:** By `date` ascending (within each symbol)

---

## Validation Script

**Run after ingestion:**

```bash
python -m orbit.ops.validate_schema --source prices --date 2024-11-05
```

**Checks:**
- Column names and types match schema
- No nulls in required columns
- Price constraints satisfied (high ≥ low, all prices > 0)
- No duplicate (date, symbol) pairs
- Daily return within sanity bounds (±20%)

**Output:** PASS / FAIL + list of violations

**Example validation code:**

```python
import pandas as pd
import pyarrow.parquet as pq

def validate_prices(file_path):
    """Validate price data against schema."""
    df = pd.read_parquet(file_path)
    
    errors = []
    
    # Required columns
    required = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'source', 'ingestion_ts']
    missing = set(required) - set(df.columns)
    if missing:
        errors.append(f"Missing columns: {missing}")
    
    # Price constraints
    if (df['high'] < df['open']).any():
        errors.append("high < open violation")
    if (df['high'] < df['close']).any():
        errors.append("high < close violation")
    if (df['high'] < df['low']).any():
        errors.append("high < low violation")
    if (df['low'] > df['open']).any():
        errors.append("low > open violation")
    if (df['low'] > df['close']).any():
        errors.append("low > close violation")
    if (df['low'] <= 0).any():
        errors.append("Non-positive prices detected")
    
    # Duplicates
    dupes = df.duplicated(subset=['date', 'symbol'])
    if dupes.any():
        errors.append(f"Duplicate rows: {dupes.sum()}")
    
    return errors

# Run validation
errors = validate_prices('data/prices/2024/11/05/SPY.parquet')
if errors:
    print("FAIL:", errors)
else:
    print("PASS")
```

---

## Common Access Patterns

### Read Single Day

```python
import pandas as pd

# Read SPY prices for specific date
df = pd.read_parquet('data/prices/2024/11/05/SPY.parquet')
```

### Read Date Range (Multiple Days)

```python
# Read all symbols for date range
df = pd.read_parquet(
    'data/prices/',
    filters=[
        ('date', '>=', '2024-11-01'),
        ('date', '<=', '2024-11-05')
    ]
)
```

### Compute Returns

```python
# Load SPY and compute returns
df = pd.read_parquet('data/prices/2024/11/01', 'data/prices/2024/11/05')
df = df[df['symbol'] == 'SPY'].sort_values('date')
df['return_1d'] = df['close'].pct_change()
df['return_5d'] = df['close'].pct_change(periods=5)
```

### Load for Feature Engineering

```python
# Load last 60 days for rolling window calculations
from datetime import datetime, timedelta

end_date = datetime(2024, 11, 5)
start_date = end_date - timedelta(days=90)  # Extra buffer for weekends

df = pd.read_parquet(
    'data/prices/',
    filters=[
        ('date', '>=', start_date.strftime('%Y-%m-%d')),
        ('date', '<=', end_date.strftime('%Y-%m-%d')),
        ('symbol', 'in', ['SPY', 'VOO', '^SPX'])
    ]
)

# Compute rolling statistics
df_spy = df[df['symbol'] == 'SPY'].sort_values('date')
df_spy['rv_10d'] = df_spy['close'].pct_change().rolling(10).std() * (252 ** 0.5)
df_spy['momentum_20d'] = df_spy['close'].pct_change(periods=20)
```

---

## Performance Tips

1. **Use filters:** Parquet partition pruning is very efficient—always filter by date when possible
2. **Select columns:** Read only needed columns: `pd.read_parquet(..., columns=['date', 'close'])`
3. **Batch reads:** Read multiple dates at once rather than looping over individual files
4. **Cache:** Keep frequently accessed price history in memory for feature computation

---

## Related Files

* `04-data-sources/stooq_prices.md` — Data source specification
* `05-ingestion/prices_stooq_ingest.md` — Ingestion implementation
* `05-ingestion/storage_layout_parquet.md` — File organization
* `10-operations/data_quality_checks.md` — Validation procedures
* `07-features/price_features.md` — Price-based feature computation

