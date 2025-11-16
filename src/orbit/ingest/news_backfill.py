"""ORBIT News Backfill - Alpaca REST API historical news fetcher.

Fetches historical news from Alpaca's REST API with multi-key rotation support.
Complements the real-time WebSocket ingestion for backtesting and historical analysis.

Implements bootstrap historical data collection as documented in:
docs/05-ingestion/bootstrap_historical_data.md
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

from orbit import io as orbit_io
from orbit.utils.key_rotation import KeyRotationManager, RotationStrategy


# Alpaca REST API configuration
ALPACA_NEWS_API_BASE = "https://data.alpaca.markets/v1beta1/news"
DEFAULT_PAGE_SIZE = 50  # Max allowed by Alpaca
TARGET_RPM = 190  # Target 190 RPM (safety margin below 200 limit)
CHECKPOINT_INTERVAL = 100  # Save checkpoint every N requests
MAX_RETRY_ATTEMPTS = 5  # Max retries for 429 errors


def save_checkpoint(checkpoint_file: Path, data: dict) -> None:
    """Save checkpoint data to JSON file.

    Args:
        checkpoint_file: Path to checkpoint file
        data: Checkpoint data to save
    """
    with open(checkpoint_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def load_checkpoint(checkpoint_file: Path) -> Optional[dict]:
    """Load checkpoint data from JSON file.

    Args:
        checkpoint_file: Path to checkpoint file

    Returns:
        Checkpoint data if file exists, None otherwise
    """
    if checkpoint_file.exists():
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    return None


from orbit.utils.key_rotation import KeyRotationManager, RotationStrategy


def scan_existing_news_dates(data_dir: Path) -> set[str]:
    """Scan existing news date partitions to determine what's already ingested.

    Args:
        data_dir: Base data directory (e.g., /srv/orbit/data or ./data)

    Returns:
        Set of date strings (YYYY-MM-DD) that already have news data
    """
    raw_news_dir = data_dir / "raw" / "news"

    if not raw_news_dir.exists():
        return set()

    # Find all date partitions
    existing_dates = set()
    for partition_dir in raw_news_dir.iterdir():
        if partition_dir.is_dir() and partition_dir.name.startswith('date='):
            date_str = partition_dir.name.replace('date=', '')
            # Check if directory has parquet files
            if list(partition_dir.glob("*.parquet")):
                existing_dates.add(date_str)

    return existing_dates


def get_alpaca_creds_for_rest() -> tuple[str, str]:
    """Get Alpaca API credentials from environment for REST API.

    Uses numbered key pattern (ALPACA_API_KEY_1) for historical backfill.
    This is separate from the WebSocket key (ALPACA_API_KEY) to allow rate limit isolation.

    Returns:
        Tuple of (api_key, api_secret)

    Raises:
        ValueError: If credentials not found in environment
    """
    # Use numbered key pattern for REST API historical backfill
    api_key = os.getenv("ALPACA_API_KEY_1")
    api_secret = os.getenv("ALPACA_API_SECRET_1")

    if not api_key or not api_secret:
        raise ValueError(
            "Alpaca REST API credentials not found.\n"
            "Set ALPACA_API_KEY_1 and ALPACA_API_SECRET_1 in .env for historical backfill.\n"
            "For multi-key: Set up to ALPACA_API_KEY_5/ALPACA_API_SECRET_5 for 5x throughput.\n"
            "Note: WebSocket (orbit ingest news) uses ALPACA_API_KEY/SECRET (non-numbered)."
        )

    return api_key, api_secret


def fetch_news_page(
    symbols: list[str],
    start: str,
    end: str,
    api_key: str,
    api_secret: str,
    page_token: Optional[str] = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: int = 30,
) -> dict:
    """Fetch a single page of news from Alpaca REST API.

    Args:
        symbols: List of symbols (e.g., ["SPY", "VOO"])
        start: Start date in ISO format (e.g., "2020-01-01T00:00:00Z")
        end: End date in ISO format
        api_key: Alpaca API key
        api_secret: Alpaca API secret
        page_token: Pagination token from previous response (optional)
        page_size: Number of items per page (default: 50)
        timeout: Request timeout in seconds

    Returns:
        Dict with 'news' (list of articles) and 'next_page_token' (optional)

    Raises:
        requests.HTTPError: If request fails
    """
    # Build query parameters
    params = {
        "symbols": ",".join(symbols),
        "start": start,
        "end": end,
        "limit": page_size,
        "sort": "asc",  # Chronological order
    }

    if page_token:
        params["page_token"] = page_token

    # Make request
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "User-Agent": os.getenv("ORBIT_USER_AGENT", "ORBIT/1.0 (Educational project; +https://github.com/calebyhan/orbit)"),
    }

    response = requests.get(
        ALPACA_NEWS_API_BASE,
        params=params,
        headers=headers,
        timeout=timeout,
    )

    response.raise_for_status()
    return response.json()


def normalize_alpaca_rest_message(article: dict, received_at: datetime, run_id: str) -> dict:
    """Normalize Alpaca REST API article to canonical schema.

    This is the canonical normalization implementation - matches WebSocket ingestion.
    Both produce identical schema for seamless merging of backfill + real-time data.

    Args:
        article: Raw article from Alpaca REST API
        received_at: When we fetched this article (UTC)
        run_id: Unique run identifier

    Returns:
        Normalized article dict matching news.parquet.schema.md
    """
    import hashlib
    import json

    # Compute message ID (canonical logic shared with WebSocket)
    # Primary: Use provider's 'id' field (keep as int)
    # Fallback: SHA-1 hash of (headline + source + created_at)
    msg_id = article.get("id")
    if not msg_id:
        content = f"{article.get('headline', '')}{article.get('source', '')}{article.get('created_at', '')}"
        msg_id = hashlib.sha1(content.encode()).hexdigest()

    normalized = {
        "msg_id": msg_id,
        "published_at": pd.to_datetime(article.get("created_at") or article.get("updated_at")),
        "received_at": pd.to_datetime(received_at),
        "symbols": article.get("symbols", []),
        "headline": article.get("headline", ""),
        "summary": article.get("summary"),
        "source": article.get("source", ""),
        "url": article.get("url"),
        "raw": json.dumps(article),
        "run_id": run_id,
    }

    return normalized


def backfill_news_date_range(
    symbols: list[str],
    start_date: str,
    end_date: str,
    run_id: Optional[str] = None,
    use_multi_key: bool = True,
    quota_rpm: int = TARGET_RPM,
    write_raw: bool = True,
    resume: bool = True,
    reset: bool = False,
) -> dict:
    """Backfill historical news from Alpaca REST API.

    Optimized for single-key reliability with checkpoint/resume capability.
    By default, scans existing date partitions and skips already-ingested dates.

    Args:
        symbols: List of symbols (e.g., ["SPY", "VOO"])
        start_date: Start date in ISO format (e.g., "2020-01-01" or "2020-01-01T00:00:00Z")
        end_date: End date in ISO format
        run_id: Unique run identifier (auto-generated if None)
        use_multi_key: Whether to use multi-key rotation (default: True)
        quota_rpm: Target requests per minute for rate limiting (default: 190)
        write_raw: Whether to write to disk (default: True)
        resume: Whether to resume from checkpoint if available (default: True)
        reset: If True, re-fetch all dates; if False (default), skip existing dates

    Returns:
        Dict with statistics (articles_fetched, requests_made, elapsed_time, etc.)
    """
    # Generate run_id if not provided
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_backfill")

    # Get data directory
    data_dir = orbit_io.get_data_dir()

    # Scan existing dates (unless --reset)
    existing_dates = set()
    if not reset:
        existing_dates = scan_existing_news_dates(data_dir)
        if existing_dates:
            print(f"\nFound {len(existing_dates)} existing date partitions")
            print(f"  Date range: {min(existing_dates)} to {max(existing_dates)}")
            print(f"  Mode: Incremental (skipping already-ingested dates)")
        else:
            print("\nNo existing data found - fetching full date range")
    else:
        print("\nReset mode: Re-fetching all dates (existing data will be overwritten)")

    # Checkpoint file (still used for mid-run interruption recovery)
    checkpoint_file = Path(f".backfill_checkpoint_{run_id}.json")

    # Try to load checkpoint
    checkpoint = None
    if resume and checkpoint_file.exists():
        checkpoint = load_checkpoint(checkpoint_file)
        print(f"\n✓ Resuming from checkpoint: {checkpoint_file}")
        print(f"  Previous progress: {checkpoint['articles_fetched']} articles, {checkpoint['requests_made']} requests")
    else:
        print(f"\nStarting Alpaca news backfill (run_id: {run_id})")

    print(f"Date range: {start_date} to {end_date}")
    print(f"Symbols: {symbols}")

    # Parse dates
    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    # Add timezone if naive
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    # Resume from checkpoint if available
    if checkpoint:
        resume_date = datetime.fromisoformat(checkpoint['last_date'])
        if resume_date > start_dt:
            start_dt = resume_date
            print(f"  Resuming from: {start_dt.date()}")

    # Initialize key manager or single key
    if use_multi_key:
        try:
            # Try to load multiple keys
            key_manager = KeyRotationManager(
                env_prefix="ALPACA_API_KEY",
                max_keys=5,
                strategy=RotationStrategy.ROUND_ROBIN,
                quota_rpd=None,  # No daily quota tracking for REST API
                # Could add RPM tracking in future
            )
            num_keys = len(key_manager.keys)
            print(f"✓ Using multi-key mode ({num_keys} keys loaded)")
            print(f"  Combined throughput: ~{quota_rpm * num_keys} RPM")
        except ValueError:
            # Fall back to single key
            print("⚠ Multi-key mode requested but only single key found")
            print("  Falling back to single key mode")
            use_multi_key = False

    if not use_multi_key:
        # Single key mode
        api_key, api_secret = get_alpaca_creds_for_rest()
        print(f"✓ Using single key mode")
        print(f"  Throughput: ~{quota_rpm} RPM")

    # Statistics (restore from checkpoint if resuming)
    articles_fetched = checkpoint['articles_fetched'] if checkpoint else 0
    requests_made = checkpoint['requests_made'] if checkpoint else 0
    current_articles = []
    start_time = time.time()
    last_request_time = 0.0  # For rate limiting
    request_interval = 60.0 / quota_rpm  # Seconds between requests

    # Iterate through date range (daily chunks to respect pagination)
    current_date = start_dt
    delta = timedelta(days=1)
    total_days = (end_dt - start_dt).days

    # Progress bar
    pbar = tqdm(
        total=total_days,
        desc="Backfill progress",
        unit="day",
        initial=(start_dt - datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)).days if checkpoint else 0,
    )

    while current_date < end_dt:
        next_date = min(current_date + delta, end_dt)
        current_date_str = current_date.strftime("%Y-%m-%d")

        # Skip if this date already exists (unless reset mode)
        if not reset and current_date_str in existing_dates:
            current_date = next_date
            pbar.update(1)
            continue

        # Format for API
        start_iso = current_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = next_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Fetch all pages for this day
        page_token = None
        page_num = 0

        while True:
            page_num += 1

            # Retry loop for 429 errors
            retry_count = 0
            retry_delay = 60  # Start with 60s backoff

            while retry_count < MAX_RETRY_ATTEMPTS:
                try:
                    # Precise rate limiting: ensure we don't exceed quota_rpm
                    time_since_last = time.time() - last_request_time
                    if time_since_last < request_interval:
                        time.sleep(request_interval - time_since_last)

                    # Get API key (rotate if multi-key)
                    if use_multi_key:
                        key = key_manager.get_next_key()
                        api_key = key.key_value
                        # Extract secret from environment (keys are stored as KEY:SECRET pairs or separate)
                        api_secret = os.getenv(key.key_name.replace("KEY", "SECRET"))
                        if not api_secret:
                            # Try underscore pattern
                            secret_name = key.key_name.replace("API_KEY", "API_SECRET")
                            api_secret = os.getenv(secret_name)

                    # Fetch page
                    last_request_time = time.time()
                    response = fetch_news_page(
                        symbols=symbols,
                        start=start_iso,
                        end=end_iso,
                        api_key=api_key,
                        api_secret=api_secret,
                        page_token=page_token,
                    )

                    requests_made += 1
                    break  # Success, exit retry loop

                except requests.HTTPError as e:
                    if e.response.status_code == 429:
                        # Rate limited - exponential backoff
                        retry_count += 1
                        if retry_count >= MAX_RETRY_ATTEMPTS:
                            pbar.write(f"  ✗ Max retries reached for 429 errors, skipping day")
                            break
                        pbar.write(f"  ⚠ Rate limited (429), attempt {retry_count}/{MAX_RETRY_ATTEMPTS}, backing off {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        pbar.write(f"  ✗ HTTP error: {e}")
                        break
                except Exception as e:
                    pbar.write(f"  ✗ Error fetching page: {e}")
                    break

            # Check if we broke out of retry loop without success
            if retry_count >= MAX_RETRY_ATTEMPTS:
                break  # Skip this day

            # Process response (only if we successfully fetched)
            if retry_count < MAX_RETRY_ATTEMPTS:
                # Process articles
                articles = response.get("news", [])
                if not articles:
                    break

                # Normalize articles
                received_at = datetime.now(timezone.utc)
                for article in articles:
                    normalized = normalize_alpaca_rest_message(article, received_at, run_id)
                    current_articles.append(normalized)

                articles_fetched += len(articles)

                # Update progress bar
                pbar.set_postfix({
                    'articles': articles_fetched,
                    'requests': requests_made,
                    'rpm': f"{requests_made / ((time.time() - start_time) / 60):.1f}",
                })

                # Check for next page
                page_token = response.get("next_page_token")
                if not page_token:
                    break

                # Save checkpoint periodically
                if requests_made % CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(checkpoint_file, {
                        'run_id': run_id,
                        'last_date': current_date.isoformat(),
                        'articles_fetched': articles_fetched,
                        'requests_made': requests_made,
                        'symbols': symbols,
                    })

        # Move to next day
        current_date = next_date
        pbar.update(1)

    pbar.close()

    # Write collected articles to disk
    if write_raw and current_articles:
        print(f"\n✓ Writing {len(current_articles)} articles to disk...")

        df = pd.DataFrame(current_articles)

        # Partition by date (from published_at)
        df["date"] = pd.to_datetime(df["published_at"]).dt.date

        for date, group in df.groupby("date"):
            date_str = str(date)
            path = f"raw/news/date={date_str}/news_backfill.parquet"

            # Append to existing if present (may overlap with WebSocket data)
            orbit_io.write_parquet(group.drop(columns=["date"]), path, overwrite=False)
            print(f"  → {date_str}: {len(group)} articles")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    elapsed_str = f"{elapsed_time / 3600:.2f}h" if elapsed_time > 3600 else f"{elapsed_time / 60:.1f}m"

    # Remove checkpoint on successful completion
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    # Summary
    print("\n" + "="*60)
    print("Backfill complete!")
    print(f"  Articles fetched: {articles_fetched}")
    print(f"  API requests: {requests_made}")
    print(f"  Elapsed time: {elapsed_str}")
    print(f"  Average rate: {requests_made / (elapsed_time / 60):.1f} RPM")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Run ID: {run_id}")
    print("="*60)

    return {
        "articles_fetched": articles_fetched,
        "requests_made": requests_made,
        "elapsed_time": elapsed_time,
        "date_range": f"{start_date} to {end_date}",
        "run_id": run_id,
    }


if __name__ == "__main__":
    # CLI entrypoint for testing
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m orbit.ingest.news_backfill START_DATE END_DATE [SYMBOLS...]")
        print("Example: python -m orbit.ingest.news_backfill 2024-01-01 2024-01-31 SPY VOO")
        sys.exit(1)

    start_date = sys.argv[1]
    end_date = sys.argv[2]
    symbols = sys.argv[3:] if len(sys.argv) > 3 else ["SPY", "VOO"]

    result = backfill_news_date_range(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
    )

    print("\nFinal statistics:")
    for key, value in result.items():
        print(f"  {key}: {value}")
