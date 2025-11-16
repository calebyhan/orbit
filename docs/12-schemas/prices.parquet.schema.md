# ORBIT — prices.parquet

*Last edited: 2025-11-16*

## Purpose

Define the **canonical schema** for price data (SPY, VOO, ^SPX) stored in Parquet format. This schema is enforced at ingestion and validated before downstream processing.

---

## File Location

**Path pattern (raw):** `data/raw/prices/<symbol>.parquet`
**Path pattern (curated):** `data/curated/prices/<symbol>.parquet`

**Examples:**
- `data/raw/prices/SPY.US.parquet` (full history for SPY)
- `data/raw/prices/VOO.US.parquet` (full history for VOO)
- `data/raw/prices/^SPX.parquet` (full history for S&P 500 index)

**Note:** Prices use **symbol-level partitioning** (one file per symbol containing full history). Each ingestion overwrites the entire symbol file with updated history from Stooq.

---

## Schema

| Column | Type | Nullable | Description | Constraints |
|--------|------|----------|-------------|-------------|
| `date` | `date` | No | Trading date (YYYY-MM-DD) | Must be a valid trading day |
| `symbol` | `string` | No | Ticker symbol | One of: `SPY.US`, `VOO.US`, `^SPX` |
| `open` | `float64` | No | Opening price ($) | > 0 |
| `high` | `float64` | No | High price ($) | ≥ open, close, low |
| `low` | `float64` | No | Low price ($) | ≤ open, close, high |
| `close` | `float64` | No | Closing price ($) | > 0 |
| `volume` | `int64` | No | Trading volume (shares) | ≥ 0 |
| `source` | `string` | No | Data source | Fixed: `stooq` |
| `run_id` | `string` | No | Ingestion run identifier | Format: `YYYYMMDD_HHMMSS` |

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
  "symbol": "SPY.US",
  "open": 450.12,
  "high": 452.87,
  "low": 449.23,
  "close": 451.64,
  "volume": 85234567,
  "source": "stooq",
  "run_id": "20241105_161023"
}
```

---

## Partitioning

**Strategy:** Symbol-level (one file per symbol, full history)

**Rationale:**
- Simple overwrite strategy for daily updates
- Full price history always available in single file
- Fast symbol-specific queries
- Small file count (3 files total for SPY, VOO, ^SPX)

**Trade-off:** Rewrites entire history on each update, but files are small (~10MB each for 20 years of data)

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

### Read Single Symbol (Full History)

```python
import pandas as pd

# Read SPY full history
df = pd.read_parquet('data/raw/prices/SPY.US.parquet')

# Filter to specific date
spy_nov5 = df[df['date'] == '2024-11-05']
```

### Read Date Range (Single Symbol)

```python
# Read SPY and filter by date range
df = pd.read_parquet('data/raw/prices/SPY.US.parquet')
df = df[(df['date'] >= '2024-11-01') & (df['date'] <= '2024-11-05')]
```

### Read Multiple Symbols

```python
# Read all symbols
import glob
files = glob.glob('data/raw/prices/*.parquet')
dfs = [pd.read_parquet(f) for f in files]
df_all = pd.concat(dfs, ignore_index=True)
```

### Compute Returns

```python
# Load SPY and compute returns
df = pd.read_parquet('data/raw/prices/SPY.US.parquet')
df = df.sort_values('date')
df['return_1d'] = df['close'].pct_change()
df['return_5d'] = df['close'].pct_change(periods=5)
```

### Load for Feature Engineering

```python
# Load last 60 days for rolling window calculations
from datetime import datetime, timedelta

end_date = datetime(2024, 11, 5)
start_date = end_date - timedelta(days=90)  # Extra buffer for weekends

df_spy = pd.read_parquet('data/raw/prices/SPY.US.parquet')
df_spy = df_spy[(df_spy['date'] >= start_date.strftime('%Y-%m-%d')) &
                (df_spy['date'] <= end_date.strftime('%Y-%m-%d'))]
df_spy = df_spy.sort_values('date')

# Compute rolling statistics
df_spy['rv_10d'] = df_spy['close'].pct_change().rolling(10).std() * (252 ** 0.5)
df_spy['momentum_20d'] = df_spy['close'].pct_change(periods=20)
```

---

## Performance Tips

1. **Select columns:** Read only needed columns: `pd.read_parquet(..., columns=['date', 'close'])`
2. **Cache in memory:** Price files are small (~10MB each) - keep in memory for repeated access
3. **Filter after read:** Since files contain full history, filter by date range after loading
4. **Use curated for features:** Once prices are processed, use `data/curated/prices/` for feature engineering

---

## Related Files

* `04-data-sources/stooq_prices.md` — Data source specification
* `05-ingestion/prices_stooq_ingest.md` — Ingestion implementation
* `05-ingestion/storage_layout_parquet.md` — File organization
* `10-operations/data_quality_checks.md` — Validation procedures
* `07-features/price_features.md` — Price-based feature computation

