# ORBIT — Bootstrap: Historical Data Collection

*Last edited: 2025-11-11*

## Purpose

Define the **one-time bootstrap process** for collecting sufficient historical data to enable walk-forward training and backtesting. This is distinct from the daily incremental ingestion documented in other specs.

---

## Overview

Before running daily pipelines, ORBIT requires **historical baseline data** for:

1. **Prices**: Minimum 24 months (supports 12-month training + 1-month val + 1-month test with room for walk-forward)
2. **News**: Best-effort historical backfill using Alpaca REST API, alternative news APIs, or web scraping
3. **Social**: Attempt to collect 3-6 months via Reddit API (PRAW recent posts) or Pushshift archives; fallback to daily accumulation if unavailable

**Target date range**: 2020-01-01 to present (provides ~5 years for regime coverage)

---

## Prices Bootstrap (Stooq)

### How Stooq Works

The Stooq CSV endpoint returns **complete historical data** for a symbol in a single request:

```
https://stooq.com/q/d/l/?s=spy.us&i=d
```

This returns all available daily bars from inception to present.

### Bootstrap Process

**Option 1: Full History (Recommended)**

```bash
# Single run fetches all history
python -m orbit.cli ingest:prices --symbols SPY.US VOO.US ^SPX
```

The current `ingest_prices()` implementation already fetches full history. The result is a single Parquet file per symbol containing all dates.

**Option 2: Date-Range Constrained**

If you want to limit history to a specific range (e.g., last 3 years), modify `ingest/prices.py` to add a `--start-date` flag and filter the DataFrame after parsing:

```python
def ingest_prices(..., start_date: Optional[str] = None):
    # ... existing fetch logic ...
    if start_date:
        df = df[df['date'] >= start_date]
    # ... rest of pipeline ...
```

### Storage After Bootstrap

After the initial run, you will have:

```
data/raw/prices/YYYY/MM/DD/
  SPY_US.parquet  (all history)
  VOO_US.parquet  (all history)
  SPX.parquet     (all history)
```

**Note**: Current implementation writes to a date-partitioned structure using the **latest date** in the fetched data. This means the full historical file is stored under today's date. This is acceptable for bootstrap but should be refined for incremental updates.

### Validation

After bootstrap, verify you have sufficient history:

```bash
# Check date range (requires pandas)
python -c "
import pandas as pd
df = pd.read_parquet('data/raw/prices/2025/11/10/SPY_US.parquet')
print(f'Rows: {len(df)}')
print(f'Date range: {df[\"date\"].min()} to {df[\"date\"].max()}')
print(f'Required minimum: 24 months = ~504 trading days')
assert len(df) >= 504, 'Insufficient history for walk-forward training'
"
```

---

## News Bootstrap (Multiple Options)

### Option 1: Alpaca Historical News API (Primary)

Alpaca provides a **REST API** for historical news:

```
GET https://data.alpaca.markets/v1beta1/news
  ?symbols=SPY,VOO
  &start=2020-01-01T00:00:00Z
  &end=2020-01-02T00:00:00Z
  &limit=50
  &page_token=<next>
```

**Pros**: Same source as daily WS; consistent schema  
**Cons**: Rate limits; may require paid tier for deep history

### Option 2: Alternative News APIs

If Alpaca historical access is limited, consider:

**NewsAPI.org**
- Free tier: 100 requests/day, 1 month of history
- Paid tier: Deeper history, more requests
- Endpoint: `https://newsapi.org/v2/everything?q=SPY&from=2020-01-01&to=2020-01-31`

**Finnhub**
- Free tier: Company news with symbol filtering
- Endpoint: `https://finnhub.io/api/v1/company-news?symbol=SPY&from=2020-01-01&to=2020-12-31`

**Alpha Vantage**
- Free tier: News sentiment API
- Endpoint: `https://www.alpha-vantage.co/query?function=NEWS_SENTIMENT&tickers=SPY`

**Implementation**: Create source-specific parsers in `ingest/news_backfill_<source>.py` that normalize to the canonical schema:

```python
# Normalize all sources to:
# msg_id, published_at, symbols, headline, summary, source, url, raw
```

### Option 3: Web Scraping (Last Resort)

If APIs are cost-prohibitive, scrape financial news sites:

**Targets**:
- Yahoo Finance: `https://finance.yahoo.com/quote/SPY/news`
- MarketWatch: `https://www.marketwatch.com/investing/fund/spy`
- Seeking Alpha: `https://seekingalpha.com/symbol/SPY/news`

**Implementation considerations**:
1. **Respect robots.txt** and terms of service
2. **Rate limiting**: 1-2 requests/second max; use exponential backoff
3. **User-Agent**: Set proper identifier per `tos_compliance.md`
4. **Fragility**: Scrapers break when sites change layouts
5. **Legal**: Review TOS carefully; some sites prohibit automated access

**Example scraper structure**:

```python
import requests
from bs4 import BeautifulSoup
import time

def scrape_yahoo_news(symbol, start_date, end_date):
    """Scrape Yahoo Finance news for a symbol."""
    # WARNING: This may violate TOS - use as last resort
    # Check https://finance.yahoo.com/robots.txt first
    
    url = f"https://finance.yahoo.com/quote/{symbol}/news"
    headers = {"User-Agent": "ORBIT/1.0 (Educational; +https://github.com/calebyhan/orbit)"}
    
    # Implement date filtering, pagination, and normalization
    # Store rejected/failed scrapes in data/rejects/news/
```

**Recommendation**: Only use web scraping if:
- You've exhausted API options
- You've verified it's legally permissible
- You implement robust error handling and respect rate limits

### Bootstrap Process (Implemented in M1)

**Status**: ✅ Implemented in M1

**Implementation**: Option 1 (Alpaca REST API) with multi-key rotation support

**Module**: `src/orbit/ingest/news_backfill.py` with logic for:

1. ✅ Date range iteration from `start_date` to `end_date` (daily chunks)
2. ✅ Pagination handling for Alpaca REST API
3. ✅ Normalization to same schema as `news_alpaca_ws_ingest.md`
4. ✅ Write to `data/raw/news/date=YYYY-MM-DD/news_backfill.parquet`
5. ✅ Rate limiting (simple delay: 60/quota_rpm between requests)
6. ✅ Retry logic with 429 backoff handling
7. ✅ Multi-key rotation support (ALPACA_API_KEY_1-5 for 5x throughput)
8. ✅ Statistics tracking (articles fetched, requests made, date range)

**CLI command**:

```bash
# Single key mode
orbit ingest news-backfill \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --symbols SPY VOO

# Force single key (disable multi-key)
orbit ingest news-backfill \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --symbols SPY VOO \
  --single-key
```

**Multi-key rotation**:
- Set `ALPACA_API_KEY_1` through `ALPACA_API_KEY_5` in `.env`
- Set `ALPACA_API_SECRET_1` through `ALPACA_API_SECRET_5` in `.env`
- Automatically uses round-robin strategy
- ~200 RPM per key → ~1,000 RPM with 5 keys (5x throughput)
- Falls back to single key (`ALPACA_API_KEY`/`ALPACA_API_SECRET`) if multi-key not configured

---

## Social Bootstrap (Reddit & Alternatives)

### Reddit Historical Data Options

#### Option 1: Reddit API (PRAW) - Recent History

Reddit API has **limited historical access**:

- Can fetch recent posts (typically last 1000 posts per subreddit via `subreddit.new(limit=1000)`)
- Can fetch top posts by time period: `subreddit.top(time_filter='year')`, `time_filter='month'`
- **Realistic window**: Last 1-6 months depending on subreddit activity

**Implementation approach**:

```python
import praw

reddit = praw.Reddit(...)
for subreddit_name in ['wallstreetbets', 'stocks', 'investing']:
    subreddit = reddit.subreddit(subreddit_name)
    
    # Get recent posts (last ~1000)
    for post in subreddit.new(limit=1000):
        # Normalize to schema and filter by date
        if post.created_utc >= start_timestamp:
            # Store to data/raw/social/
```

#### Option 2: Pushshift Reddit Archive

**Pushshift** (pushshift.io) provides historical Reddit data archives:

- **Status**: Service has had reliability issues; check current availability
- **API**: `https://api.pushshift.io/reddit/search/submission/?subreddit=wallstreetbets&after=1609459200&before=1612137600`
- **Pros**: Deep historical access (years of data)
- **Cons**: Service stability concerns; may have rate limits; data quality varies

**Note**: As of 2024-2025, Pushshift API access has been restricted. Check current status before implementation.

#### Option 3: Reddit Data Dumps & Archives

- **Academic datasets**: Some researchers publish Reddit datasets (check r/datasets)
- **Archive.org**: May have snapshots of subreddits
- **Private archives**: Community-maintained dumps (verify licensing)

### Bootstrap Strategy

**Recommendation for v1**: **Try to collect 3-6 months of historical data** using available methods.

**Practical approach**:

1. **Use PRAW to get recent history** (last 1000 posts per subreddit):
   ```bash
   python -m orbit.cli ingest:social:backfill \
     --method praw_recent \
     --subreddits wallstreetbets stocks investing \
     --lookback-days 180
   ```

2. **Supplement with Pushshift if available**:
   ```bash
   python -m orbit.cli ingest:social:backfill \
     --method pushshift \
     --start 2020-01-01 \
     --end 2025-11-10
   ```

3. **Filter and normalize**:
   - Apply same quality filters as `social_reddit_ingest.md`
   - Remove deleted/removed posts
   - Store in `data/raw/social/YYYY/MM/DD/reddit.parquet`

**Fallback if historical collection fails**:
1. Limited API access to history
2. Quality degrades for old posts (deleted/removed content)
3. Walk-forward training can start with `social_count=0` for early periods
4. Social features have `na_value=0` fallback in feature engineering

**Timeline**: 
- **Ideal**: 6+ months of historical data from backfill
- **Acceptable**: 3 months of historical data + daily accumulation
- **Minimum**: Start with 0 days and accumulate via daily ingestion (~60 days for meaningful z-scores)

### Implementation Checklist

- [ ] Test PRAW recent history fetch (verify 1000-post limit behavior)
- [ ] Check Pushshift API status and availability
- [ ] Implement backfill script with retry logic and rate limiting
- [ ] Validate historical data quality (check for deleted/removed posts)
- [ ] Document actual coverage achieved (e.g., "180 days for WSB, 90 days for r/stocks")
- [ ] Add data provenance metadata (source, fetch_date, coverage_start, coverage_end)

---

## Bootstrap Workflow (Full Setup)

### Step 1: Prices (Day 0)

```bash
# Fetch full history for all symbols
python -m orbit.cli ingest:prices
```

**Expected output**:
- `data/raw/prices/` and `data/curated/prices/` populated with multi-year history
- Validation shows ≥504 trading days per symbol

### Step 2: News (Best Effort, Day 0)

```bash
# Option 1: Alpaca REST backfill (if implemented)
python -m orbit.cli ingest:news:backfill --source alpaca --start 2020-01-01 --end $(date +%Y-%m-%d)

# Option 2: Alternative news API (e.g., NewsAPI, Finnhub)
python -m orbit.cli ingest:news:backfill --source newsapi --start 2024-05-01 --end $(date +%Y-%m-%d)

# Option 3: Web scraping (if APIs unavailable and TOS permits)
python -m orbit.cli ingest:news:scrape --sites yahoo,marketwatch --start 2024-01-01 --end $(date +%Y-%m-%d)

# Otherwise: Skip and start daily WS ingestion
```

### Step 3: Social (Best Effort, Day 0)

```bash
# Option 1: PRAW recent history (last 1000 posts per subreddit)
python -m orbit.cli ingest:social:backfill --method praw_recent --lookback-days 180

# Option 2: Pushshift archives (if available)
python -m orbit.cli ingest:social:backfill --method pushshift --start 2024-05-01 --end $(date +%Y-%m-%d)

# Otherwise: Start daily ingestion and accumulate
python -m orbit.cli ingest:social
```

Run daily ingestion going forward. Social features will have zeros/nulls for periods without data.

### Step 4: Verify Bootstrap

```bash
# Check data availability
python -m orbit.ops.validate_bootstrap \
  --required-history 24months \
  --check-prices \
  --check-news-optional \
  --check-social-optional
```

**Acceptance criteria**:
- Prices: ≥24 months available
- News: Best-effort (target: 12+ months via API; minimum: 3 months; fallback: 0 days with daily WS started)
- Social: Best-effort (target: 3-6 months; acceptable: 0 days with daily accumulation started)

### Step 5: Build Historical Features

```bash
# Generate features for all available dates
python -m orbit.cli features:build --backfill --start 2020-01-01
```

This creates `data/features/YYYY/MM/DD/features_daily.parquet` for each trading day.

### Step 6: Initial Walk-Forward Training

```bash
# Train on historical windows
python -m orbit.cli train:walkforward \
  --start 2021-01-01 \
  --end 2025-11-10 \
  --run_id bootstrap_001
```

**Note**: Requires ≥12 months of features before first window can train.

---

## Incremental Updates (After Bootstrap)

Once bootstrap is complete, switch to **daily incremental mode**:

1. **Prices**: Fetch today's bar only (Stooq still returns full history; filter in code or use cache to skip re-writes)
2. **News**: Run WS client continuously during market hours
3. **Social**: Poll Reddit API 2-6 times per day
4. **Features**: Build features for today only
5. **Training**: Roll forward training window by 1 day (or retrain weekly)

See `docs/05-ingestion/scheduler_jobs.md` for daily orchestration.

---

## Storage Considerations

### Disk Space

Estimated storage for 5 years of data:

- Prices: ~5 MB (3 symbols × ~1,250 trading days × 4 OHLCV fields)
- News: ~500 MB - 2 GB (depends on article count and summary text length)
- Social: ~100 MB - 500 MB (depends on post volume)
- Features: ~10 MB (1 row per day × ~50 features)

**Total**: ~1-3 GB for full bootstrap

### Retention Policy

See `docs/05-ingestion/storage_layout_parquet.md`:

- Raw data: **Indefinite** (can regenerate downstream)
- Curated/Features: **2 years** rolling
- Models: **Top 5 + production**

---

## Troubleshooting

### "Insufficient history" error during training

**Cause**: Bootstrap didn't fetch enough historical data  
**Fix**: Check `data/raw/prices/` date range; re-run ingest with earlier start date

### News backfill fails with 401/403

**Cause**: Invalid Alpaca API keys or rate limit  
**Fix**: Verify `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY`; respect rate limits (see `04-data-sources/rate_limits.md`)

### Social features all zeros

**Cause**: No historical Reddit data (expected)  
**Fix**: Wait for 60+ days of daily ingestion; social ablations will show limited value until then

---

## Acceptance Checklist

- [ ] Prices: ≥24 months (504 trading days) for SPY, VOO, ^SPX
- [ ] News: Historical data via API/scraping (target ≥3 months) OR daily WS ingestion started
- [ ] Social: Historical data via PRAW/Pushshift (target 3-6 months) OR daily ingestion started
- [ ] Data provenance documented: sources used, date ranges achieved, known gaps
- [ ] Features: Generated for all available price dates (with text features=0 for missing periods)
- [ ] Walk-forward training: First window (12M train + 1M val + 1M test) runs successfully
- [ ] Backtest: Can simulate strategy over ≥1 year of OOS data

---

## Related Files

* `05-ingestion/prices_stooq_ingest.md` — Daily price ingestion
* `05-ingestion/news_alpaca_ws_ingest.md` — Daily news ingestion (WS)
* `05-ingestion/social_reddit_ingest.md` — Daily social ingestion
* `05-ingestion/scheduler_jobs.md` — Daily orchestration
* `05-ingestion/storage_layout_parquet.md` — Storage conventions
* `08-modeling/training_walkforward.md` — Walk-forward requirements
* `09-evaluation/backtest_long_flat_spec.md` — Backtest data needs

---

**Last edited: 2025-11-10**
