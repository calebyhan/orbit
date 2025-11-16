# Historical News Backfill Guide

*Last edited: 2025-11-15*

**Purpose**: Best practices for fetching 10+ years of historical news data efficiently and reliably.

---

## Overview

ORBIT's historical news backfill fetches news articles from Alpaca's REST API for backtesting and research.

**Key characteristics:**
- **Data source**: Alpaca Historical News API (REST)
- **Date range**: User-specified (typically 2015-01-01 to present)
- **Symbols**: SPY, VOO (S&P 500 ETFs)
- **Volume**: ~474,500 articles over 10 years
- **Rate limit**: 200 requests/minute per API key
- **Pagination**: 50 articles per request (Alpaca limit)

---

## Timeline Estimates

### Single Key (Recommended for Initial Bootstrap)

| Metric | Value |
|--------|-------|
| Total articles | ~474,500 |
| Articles per request | 50 (Alpaca limit) |
| Total requests | ~9,490 |
| Target rate | 190 RPM (safety margin below 200 limit) |
| Theoretical minimum | 50 minutes |
| **Realistic time** | **1-2 hours** |

**Overhead factors:**
- Occasional 429 rate limit backoff: ~10-20 min
- Network latency and retries: ~5-10 min
- Pagination overhead: ~5 min

**When to use:**
- First-time setup
- Personal research projects
- One-time historical bootstrap

---

### Multi-Key (5x Faster)

| Metric | Value |
|--------|-------|
| Number of keys | 5 |
| Combined throughput | ~950 RPM (5 × 190) |
| Theoretical minimum | 10 minutes |
| **Realistic time** | **15-20 minutes** |

**When to use:**
- Frequent re-ingestion during development
- CI/CD pipelines with time constraints
- Research requiring rapid iteration
- Large-scale backtesting

---

## Single-Key Backfill (Step-by-Step)

### Step 1: Configure API Key

Add Alpaca REST API key to `.env`:

```bash
# You can use the same key as WebSocket, or create a separate key
ALPACA_API_KEY_1=your_key_id
ALPACA_API_SECRET_1=your_secret_key
```

See [03_api_keys_configuration.md](03_api_keys_configuration.md) for details.

---

### Step 2: Run in Tmux/Screen (Recommended)

Protect against SSH disconnects and terminal closures:

```bash
# Create new tmux session
tmux new -s backfill

# Activate virtual environment
source .venv/bin/activate

# Verify CLI is available
orbit --help
```

**Why tmux/screen?**
- Persists across SSH disconnects
- Can detach and reattach anytime
- Maintains session even if local terminal closes

**Tmux quick reference:**
- Detach: `Ctrl+B`, then `D`
- Reattach: `tmux attach -t backfill`
- List sessions: `tmux ls`
- Kill session: `tmux kill-session -t backfill`

---

### Step 3: Start Backfill

```bash
# Run backfill for 10 years of SPY/VOO news
orbit ingest news-backfill \
  --start 2015-01-01 \
  --end $(date +%Y-%m-%d) \
  --symbols SPY VOO
```

**What happens:**
1. ORBIT iterates through each day in the date range
2. Fetches up to 50 articles per request (paginated)
3. Saves to `data/raw/news/date=YYYY-MM-DD/news.parquet`
4. Creates checkpoint every 100 requests
5. Displays live progress bar with statistics

**Example output:**
```
Backfill progress: 45%|████▌     | 1642/3650 [00:52<00:38, 52.1day/s]
  articles=127853, requests=2557, rpm=189.2

Backfill complete!
  Articles fetched: 474,326
  API requests: 9,487
  Elapsed time: 1.2h
  Average rate: 189.3 RPM
```

---

### Step 4: Monitor Progress

In another terminal (or detach from tmux):

```bash
# Reattach to tmux session
tmux attach -t backfill

# Or tail logs
tail -f logs/ingestion_news_backfill_*.log

# Check progress via checkpoint file
ls -lh .backfill_checkpoint_*.json
cat .backfill_checkpoint_*.json
```

---

### Step 5: Handle Interruptions

If the backfill is interrupted (SSH disconnect, system reboot, Ctrl+C):

**Just re-run the same command** - ORBIT automatically resumes from the last checkpoint:

```bash
orbit ingest news-backfill \
  --start 2015-01-01 \
  --end 2025-11-15 \
  --symbols SPY VOO
```

**Example resume output:**
```
✓ Resuming from checkpoint: .backfill_checkpoint_20251115_143022_backfill.json
  Previous progress: 127,853 articles, 2,557 requests
  Resuming from: 2022-06-15
  Remaining: 1,258 days
```

**Checkpoint system:**
- Saves progress every 100 requests
- Includes: date position, article count, request count
- Auto-deleted on successful completion
- Safe to manually delete if you want to restart from scratch

---

## Multi-Key Backfill (5x Faster)

### Step 1: Add Multiple Keys

Edit `.env` to include up to 5 REST API keys:

```bash
# WebSocket key (separate, optional)
ALPACA_API_KEY=websocket_key
ALPACA_API_SECRET=websocket_secret

# REST API keys (numbered 1-5)
ALPACA_API_KEY_1=key_1
ALPACA_API_SECRET_1=secret_1
ALPACA_API_KEY_2=key_2
ALPACA_API_SECRET_2=secret_2
ALPACA_API_KEY_3=key_3
ALPACA_API_SECRET_3=secret_3
ALPACA_API_KEY_4=key_4
ALPACA_API_SECRET_4=secret_4
ALPACA_API_KEY_5=key_5
ALPACA_API_SECRET_5=secret_5
```

**How to get multiple keys:**
- Create multiple Alpaca accounts with different emails
- Or request additional API keys from Alpaca support
- Each account gets Paper Trading API access (free)

---

### Step 2: Run Backfill

```bash
# Same command - ORBIT auto-detects all available keys
orbit ingest news-backfill \
  --start 2015-01-01 \
  --end $(date +%Y-%m-%d) \
  --symbols SPY VOO
```

**Multi-key mode output:**
```
✓ Using multi-key mode (5 keys loaded)
  Combined throughput: ~950 RPM
  Estimated completion: 15-20 minutes

Backfill progress: 80%|████████  | 2920/3650 [00:12<00:03, 243.3day/s]
  articles=381224, requests=7625, rpm=942.5
```

**Load balancing strategy:**
- Round-robin: Rotate keys sequentially (default)
- Least-used: Use key with lowest request count
- Automatic failover if a key is rate-limited

---

## Rate Limiting and Error Handling

### Rate Limit Strategy

ORBIT targets **190 RPM per key** (safety margin below 200 limit):

```
Request interval = 60 seconds / 190 = 316ms
```

**Why 190 instead of 200?**
- Accounts for network latency variance
- Prevents occasional 429 errors
- Provides buffer for request bursts

---

### 429 Rate Limit Errors

If a key hits the rate limit, ORBIT automatically:

1. **Exponential backoff**: 60s → 120s → 240s (max 5 attempts)
2. **Key rotation**: Switch to next available key (multi-key mode)
3. **Logging**: Records 429 events for monitoring

**Example 429 handling:**
```
WARNING: Alpaca rate limit exceeded (429) for key 1
INFO: Backing off for 60 seconds
INFO: Retrying with key 2
```

---

### Network and Server Errors

| Error Code | Handling |
|------------|----------|
| 429 | Exponential backoff (60s → 120s → 240s) |
| 500, 503 | Retry with backoff (transient server errors) |
| 400, 401, 403 | Log and skip (bad request/auth, don't retry) |
| Network timeout | Retry with exponential backoff |

**Max retries**: 5 attempts per request
**Backoff strategy**: `2^attempt * base_delay` (60s base)

---

## Data Output

### Directory Structure

```
data/raw/news/
├── date=2015-01-01/
│   └── news.parquet          # All articles for this day
├── date=2015-01-02/
│   └── news.parquet
...
├── date=2025-11-15/
│   └── news.parquet
```

### Parquet Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | int64 | Alpaca article ID (unique) |
| `headline` | string | Article headline |
| `summary` | string | Article summary/snippet |
| `author` | string | Author or source |
| `created_at` | timestamp | Article publication time (UTC) |
| `updated_at` | timestamp | Last update time (UTC) |
| `url` | string | Source URL |
| `symbols` | list[string] | Related ticker symbols (e.g., ["SPY", "VOO"]) |
| `source` | string | News source (e.g., "Benzinga") |

See [news.parquet.schema.md](../12-schemas/news.parquet.schema.md) for full schema.

---

## Validation and Verification

### Check Completion

```bash
# Count total articles
python -c "
import pandas as pd
from pathlib import Path

news_dirs = Path('data/raw/news').glob('date=*')
total = 0
for d in news_dirs:
    parquet = d / 'news.parquet'
    if parquet.exists():
        df = pd.read_parquet(parquet)
        total += len(df)
print(f'Total articles: {total:,}')
"

# Expected output: Total articles: ~474,000
```

---

### Check Date Coverage

```bash
# List all dates with data
ls data/raw/news/ | grep "date=" | sort

# Should see continuous date range:
# date=2015-01-01
# date=2015-01-02
# ...
# date=2025-11-15
```

---

### Check for Gaps

```bash
# Find missing dates in range
python -c "
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

start = datetime(2015, 1, 1)
end = datetime.now()
expected_dates = pd.date_range(start, end, freq='D')

actual_dates = [
    datetime.strptime(d.name.replace('date=', ''), '%Y-%m-%d')
    for d in Path('data/raw/news').glob('date=*')
]

missing = set(expected_dates) - set(pd.to_datetime(actual_dates))
if missing:
    print(f'Missing {len(missing)} dates:')
    for d in sorted(missing)[:10]:  # Show first 10
        print(f'  {d.strftime(\"%Y-%m-%d\")}')
else:
    print('✓ No gaps found')
"
```

**Note**: Weekends and holidays may have zero articles (expected).

---

## Best Practices

### 1. Run During Off-Hours

```bash
# Schedule backfill overnight or on weekends
# Avoid interfering with real-time WebSocket streaming

# Cron example: Run every Saturday at 2 AM
0 2 * * 6 cd /path/to/orbit && source .venv/bin/activate && orbit ingest news-backfill --start 2015-01-01 --end $(date +%Y-%m-%d) --symbols SPY VOO
```

---

### 2. Monitor Logs

```bash
# Tail logs in real-time
tail -f logs/ingestion_news_backfill_*.log

# Search for errors after completion
grep -i "error\|warning" logs/ingestion_news_backfill_*.log
```

---

### 3. Use Separate Keys for WebSocket vs REST

```bash
# In .env:
ALPACA_API_KEY=websocket_key         # For real-time streaming
ALPACA_API_KEY_1=rest_key_1          # For historical backfill

# Benefit: Rate limit isolation
# WebSocket streaming won't be affected by backfill rate limits
```

---

### 4. Checkpoint Hygiene

```bash
# After successful backfill, checkpoint is auto-deleted
# If you want to force a restart from scratch:
rm -f .backfill_checkpoint_*.json
```

---

### 5. Disk Space Planning

**Storage requirements:**
- 10 years of SPY/VOO news: ~2-3 GB (compressed Parquet)
- Allow 5-10 GB for safety margin
- Parquet compression ratio: ~10:1 vs raw JSON

**Check available space:**
```bash
df -h data/raw/news/
```

---

## Troubleshooting

### "No API key found" error

```bash
# Check .env configuration
cat .env | grep "ALPACA_API_KEY_1"

# Should output:
# ALPACA_API_KEY_1=your_key_here

# Reload environment and retry
source .venv/bin/activate
orbit ingest news-backfill --start 2015-01-01 --end 2025-11-15 --symbols SPY VOO
```

---

### "429 Too Many Requests" persists

```bash
# If rate limiting continues despite 190 RPM target:
# 1. Add more keys (reduces load per key)
# 2. Check for other processes using the same key
# 3. Verify system clock is correct (rate limits are time-based)

# Check for concurrent usage:
ps aux | grep "orbit ingest"
```

---

### "Checkpoint resuming from wrong date"

```bash
# If checkpoint seems corrupted:
# 1. Delete checkpoint file
rm .backfill_checkpoint_*.json

# 2. Restart from scratch
orbit ingest news-backfill --start 2015-01-01 --end 2025-11-15 --symbols SPY VOO
```

---

### Slow progress (< 100 RPM)

```bash
# Possible causes:
# 1. Network latency - check internet connection
# 2. Server-side throttling - add more keys
# 3. Disk I/O bottleneck - check disk write speed

# Monitor real-time RPM:
tail -f logs/ingestion_news_backfill_*.log | grep "rpm="
```

---

## Comparison: Single Key vs Multi-Key

| Aspect | Single Key | 5 Keys |
|--------|------------|--------|
| **Setup complexity** | Simple | Moderate |
| **Backfill time (10 years)** | 1-2 hours | 15-20 min |
| **Combined throughput** | ~190 RPM | ~950 RPM |
| **API accounts needed** | 1 | 5 |
| **Best for** | Initial setup, personal use | Rapid iteration, CI/CD |
| **Reliability** | High (checkpoint/resume) | High (auto-failover) |
| **Cost** | FREE | FREE |

**Recommendation:**
- Start with **single key** for simplicity
- Upgrade to **multi-key** only if 1-2 hour backfill is too slow for your workflow

---

## Next Steps

After successful backfill:

1. **Verify data**: Run validation scripts (see above)
2. **Start real-time streaming**: `orbit ingest news --symbols SPY VOO`
3. **Run sentiment analysis**: `python -m orbit.ingest.llm_gemini` (M1)
4. **Build features**: `orbit features build` (coming in M2)

---

## Related Documentation

- [02_cli_commands.md](02_cli_commands.md) - CLI reference
- [03_api_keys_configuration.md](03_api_keys_configuration.md) - API key setup
- [bootstrap_historical_data.md](../05-ingestion/bootstrap_historical_data.md) - Technical spec
- [rate_limits.md](../04-data-sources/rate_limits.md) - Rate limit strategies
- [alpaca_news_ws.md](../04-data-sources/alpaca_news_ws.md) - Alpaca API details
