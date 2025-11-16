# CLI Commands Reference

*Last edited: 2025-11-15*

**Purpose**: Complete reference for all ORBIT CLI commands with usage examples.

---

## Overview

ORBIT uses a hierarchical CLI structure:

```bash
orbit [GLOBAL_OPTIONS] COMMAND SUBCOMMAND [OPTIONS]
```

Current commands in M1:
- `orbit ingest` - Data ingestion from external sources
- `orbit features` - Feature engineering (coming soon)

---

## Global Options

```bash
orbit --help              # Show help for all commands
orbit -h                  # Short form
```

---

## Ingest Commands

### `orbit ingest --help`

Show all available ingestion subcommands:

```bash
orbit ingest --help

# Output:
# positional arguments:
#   {prices,news,news-backfill}
#     prices              Ingest prices from Stooq (M1)
#     news                Ingest news from Alpaca WebSocket (M1)
#     news-backfill       Backfill historical news from Alpaca REST API (M1)
#
# options:
#   --local-sample        Use sample data from ./data/sample/ (M0 mode)
```

---

### `orbit ingest prices`

**Purpose**: Download historical and daily price data from Stooq.

**Source**: Stooq free OHLCV data
**Symbols**: SPY.US, VOO.US, ^SPX (S&P 500 index)
**Frequency**: Daily bars
**Range**: Full available history → present

```bash
# Download all price data (recommended first-time usage)
orbit ingest prices

# What it does:
# 1. Fetches SPY, VOO, and ^SPX from Stooq
# 2. Saves to data/raw/prices/{symbol}.parquet
# 3. Creates normalized curated files in data/curated/prices/
# 4. Logs results to logs/ingestion_prices_YYYYMMDD_HHMMSS.log
```

**Output files:**
```
data/raw/prices/SPY.US.parquet
data/raw/prices/VOO.US.parquet
data/raw/prices/^SPX.parquet
data/curated/prices/SPY.US.parquet
data/curated/prices/VOO.US.parquet
data/curated/prices/^SPX.parquet
```

**Best practices:**
- Run once during initial setup
- Run daily after market close (after 16:00 ET) for updates
- Schedule via cron: `0 17 * * 1-5 /path/to/orbit ingest prices`

**Detailed spec**: [prices_stooq_ingest.md](../05-ingestion/prices_stooq_ingest.md)

---

### `orbit ingest news`

**Purpose**: Stream real-time news from Alpaca WebSocket.

**Source**: Alpaca Market Data news feed (free tier)
**Symbols**: Configurable (default: SPY, VOO)
**Mode**: Long-running WebSocket stream
**Rate limit**: Free tier supports up to 30 symbols

```bash
# Stream news for SPY and VOO (recommended)
orbit ingest news --symbols SPY VOO

# What it does:
# 1. Connects to Alpaca WebSocket (wss://stream.data.alpaca.markets/v1beta1/news)
# 2. Subscribes to news for specified symbols
# 3. Buffers articles in memory (deduplication by article ID)
# 4. Flushes to disk every 5 minutes or on shutdown
# 5. Saves to data/raw/news/date=YYYY-MM-DD/news.parquet
```

**Usage patterns:**

```bash
# Run in foreground (blocks terminal, press Ctrl+C to stop gracefully)
orbit ingest news --symbols SPY VOO

# Run in background with nohup
nohup orbit ingest news --symbols SPY VOO > logs/news_stream.log 2>&1 &

# Run in tmux (recommended for remote servers)
tmux new -s news-stream
orbit ingest news --symbols SPY VOO
# Detach: Ctrl+B, then D
# Reattach: tmux attach -t news-stream

# Run in screen
screen -S news-stream
orbit ingest news --symbols SPY VOO
# Detach: Ctrl+A, then D
# Reattach: screen -r news-stream
```

**Graceful shutdown:**
- Press `Ctrl+C` once - initiates graceful shutdown
- Waits for current buffer to flush to disk
- Saves checkpoint and exits cleanly
- **Do not** press `Ctrl+C` twice (forces kill, may lose buffered data)

**API keys required:**
```bash
# In .env:
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
```

**Output files:**
```
data/raw/news/date=2025-11-15/news.parquet
data/raw/news/date=2025-11-16/news.parquet
...
```

**Best practices:**
- Run as a daemon during market hours (09:30-16:00 ET)
- Use tmux/screen for persistence on remote servers
- Monitor logs for WebSocket disconnections
- News arrives with varying delays (typically 1-30 seconds)

**Detailed spec**: [news_alpaca_ws_ingest.md](../05-ingestion/news_alpaca_ws_ingest.md)

---

### `orbit ingest news-backfill`

**Purpose**: Fetch historical news for backtesting.

**Source**: Alpaca REST API
**Date range**: User-specified start/end dates
**Symbols**: Configurable
**Rate limit**: 200 RPM per API key
**Multi-key support**: Yes (up to 5 keys for 5x throughput)

```bash
# Basic usage: backfill 10 years for SPY/VOO
orbit ingest news-backfill \
  --start 2015-01-01 \
  --end 2025-11-15 \
  --symbols SPY VOO

# What it does:
# 1. Iterates through date range day-by-day
# 2. Fetches up to 50 articles per request (Alpaca limit)
# 3. Paginates through all articles for each day
# 4. Saves to data/raw/news/date=YYYY-MM-DD/news.parquet
# 5. Creates checkpoint every 100 requests
# 6. Displays progress bar with live stats
```

**Advanced usage:**

```bash
# Backfill specific date range
orbit ingest news-backfill \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --symbols SPY VOO

# Backfill with resume capability (auto-resumes from checkpoint)
# If interrupted, just re-run the same command:
orbit ingest news-backfill \
  --start 2015-01-01 \
  --end 2025-11-15 \
  --symbols SPY VOO
# ✓ Resuming from checkpoint: .backfill_checkpoint_20251115_143022.json
```

**Multi-key setup** (5x faster backfill):

```bash
# In .env, add multiple keys:
ALPACA_API_KEY_1=key1
ALPACA_API_SECRET_1=secret1
ALPACA_API_KEY_2=key2
ALPACA_API_SECRET_2=secret2
# ... up to _5

# Run backfill (automatically detects and uses all keys)
orbit ingest news-backfill --start 2015-01-01 --end 2025-11-15 --symbols SPY VOO
# ✓ Using multi-key mode (5 keys loaded)
#   Combined throughput: ~950 RPM
```

**Performance:**
- **Single key**: 1-2 hours for 10 years of SPY/VOO news (~474K articles)
- **5 keys**: 15-20 minutes for same dataset
- **Checkpoint frequency**: Every 100 requests (auto-resume if interrupted)

**API keys required:**
```bash
# Single key (simplest):
ALPACA_API_KEY_1=your_key
ALPACA_API_SECRET_1=your_secret

# Multi-key (faster):
ALPACA_API_KEY_1 through ALPACA_API_KEY_5
ALPACA_API_SECRET_1 through ALPACA_API_SECRET_5
```

**Output files:**
```
data/raw/news/date=2015-01-01/news.parquet
data/raw/news/date=2015-01-02/news.parquet
...
data/raw/news/date=2025-11-15/news.parquet
```

**Best practices:**
- Run in tmux/screen for reliability (protects against SSH disconnects)
- Trust the checkpoint system (can resume if interrupted)
- Use single key for initial bootstrap (sufficient for 1-2 hour run)
- Use multi-key only if you need <30min backfill time
- Monitor for 429 rate limit errors (system handles them automatically)

**Detailed guide**: [04_historical_backfill.md](04_historical_backfill.md)
**Detailed spec**: [bootstrap_historical_data.md](../05-ingestion/bootstrap_historical_data.md)

---

## Features Commands (M2 - Coming Soon)

### `orbit features build`

**Purpose**: Generate engineered features from raw data.

**Status**: Not yet implemented (planned for M2)

**Planned usage:**
```bash
# Build features for specified date range
orbit features build --start 2024-01-01 --end 2024-12-31

# Build features incrementally (only new data)
orbit features build --incremental
```

**Planned outputs:**
- `data/features/features_daily.parquet` - Daily feature matrix
- Price features: returns, volatility, technical indicators
- News features: sentiment aggregations, volume Z-scores
- Social features: post counts, engagement metrics

**Detailed spec**: [news_features.md](../07-features/news_features.md), [price_features.md](../07-features/price_features.md)

---

## M0 Mode (Offline Testing)

For rapid prototyping without external APIs:

```bash
# Generate synthetic sample data
python src/orbit/utils/generate_samples.py

# Run commands with sample data
orbit ingest --local-sample
orbit features --from-sample
```

**Use cases:**
- CI/CD testing
- Development without API keys
- Schema validation
- Performance benchmarking

---

## Common Workflows

### Initial Setup (First Time)

```bash
# 1. Setup repository (see 01_repository_setup.md)
# 2. Configure API keys (see 03_api_keys_configuration.md)

# 3. Ingest historical prices (one-time, ~1 minute)
orbit ingest prices

# 4. Backfill historical news (one-time, 1-2 hours with single key)
orbit ingest news-backfill \
  --start 2015-01-01 \
  --end $(date +%Y-%m-%d) \
  --symbols SPY VOO

# 5. Start real-time news stream (long-running)
tmux new -s news-stream
orbit ingest news --symbols SPY VOO
# Detach: Ctrl+B, then D
```

---

### Daily Operations

```bash
# Morning (before market open):
# - Check that news stream is still running
tmux attach -t news-stream  # Should see live news flowing

# After market close (after 16:00 ET):
# - Update price data
orbit ingest prices

# - Features and modeling (coming in M2+)
# orbit features build --incremental
# orbit train fit --daily
```

---

### Development/Testing

```bash
# Run unit tests
pytest tests/ -v

# Run specific test
pytest tests/test_io.py -v

# Run with verbose output
pytest tests/test_io.py -v --tb=short

# Generate sample data for testing
python src/orbit/utils/generate_samples.py
```

---

## Logs and Debugging

All commands write logs to `logs/` directory:

```bash
# View recent logs
ls -lt logs/

# Tail live ingestion logs
tail -f logs/ingestion_news_YYYYMMDD_HHMMSS.log

# Search for errors
grep ERROR logs/*.log

# Check WebSocket disconnections
grep -i "disconnect\|reconnect" logs/ingestion_news_*.log
```

**Log levels** (set in `.env`):
```bash
ORBIT_LOG_LEVEL=DEBUG   # Verbose (development)
ORBIT_LOG_LEVEL=INFO    # Normal (production)
ORBIT_LOG_LEVEL=WARNING # Quiet (only warnings/errors)
```

---

## Exit Codes

All ORBIT commands use standard exit codes:

- `0` - Success
- `1` - General error (check logs)
- `2` - Configuration error (missing API keys, invalid config)
- `130` - Interrupted by user (Ctrl+C)

**Example usage in scripts:**
```bash
#!/bin/bash
orbit ingest prices
if [ $? -ne 0 ]; then
  echo "Price ingestion failed!"
  exit 1
fi
```

---

## Related Documentation

- [01_repository_setup.md](01_repository_setup.md) - Initial setup
- [03_api_keys_configuration.md](03_api_keys_configuration.md) - API key setup
- [04_historical_backfill.md](04_historical_backfill.md) - Backfill guide
- [05_development_workflow.md](05_development_workflow.md) - Development practices
- [runbook.md](../10-operations/runbook.md) - Production operations
