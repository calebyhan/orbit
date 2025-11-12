"""ORBIT News Backfill - Alpaca REST API historical news fetcher.

Fetches historical news from Alpaca's REST API with multi-key rotation support.
Complements the real-time WebSocket ingestion for backtesting and historical analysis.

Implements bootstrap historical data collection as documented in:
docs/05-ingestion/bootstrap_historical_data.md
"""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from orbit import io as orbit_io
from orbit.utils.key_rotation import KeyRotationManager, RotationStrategy


# Alpaca REST API configuration
ALPACA_NEWS_API_BASE = "https://data.alpaca.markets/v1beta1/news"
DEFAULT_PAGE_SIZE = 50  # Max allowed by Alpaca


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

    Matches the schema used by WebSocket ingestion for consistency.

    Args:
        article: Raw article from Alpaca REST API
        received_at: When we fetched this article (UTC)
        run_id: Unique run identifier

    Returns:
        Normalized article dict matching news.parquet.schema.md
    """
    import hashlib
    import json

    # Compute message ID (same logic as WebSocket)
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
    quota_rpm: int = 200,
    write_raw: bool = True,
) -> dict:
    """Backfill historical news for a date range using Alpaca REST API.

    This is the main entrypoint for historical news backfill.
    Supports multi-key rotation for 5x throughput (1,000 RPM vs 200 RPM).

    Args:
        symbols: List of symbols to fetch news for (e.g., ["SPY", "VOO"])
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        run_id: Unique run identifier (auto-generated if None)
        use_multi_key: Whether to use multi-key rotation (default: True)
        quota_rpm: Requests per minute per key (default: 200 for free tier)
        write_raw: Whether to write raw data to disk

    Returns:
        Dict with statistics:
        - articles_fetched: Total articles retrieved
        - requests_made: Total API requests
        - date_range: Date range covered
        - run_id: Run identifier

    Note:
        Data is written to ORBIT_DATA_DIR/raw/news/date=YYYY-MM-DD/news.parquet
        Set ALPACA_API_KEY_1 through ALPACA_API_KEY_5 for multi-key mode
        Or use ALPACA_API_KEY/ALPACA_API_SECRET for single key mode
    """
    # Generate run_id if not provided
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_backfill")

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
            print(f"✓ Using multi-key mode ({key_manager.num_keys} keys loaded)")
            print(f"  Combined throughput: ~{quota_rpm * key_manager.num_keys} RPM")
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

    # Statistics
    articles_fetched = 0
    requests_made = 0
    current_articles = []

    # Iterate through date range (daily chunks to respect pagination)
    current_date = start_dt
    delta = timedelta(days=1)

    while current_date < end_dt:
        next_date = min(current_date + delta, end_dt)

        # Format for API
        start_iso = current_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = next_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"\nFetching {current_date.date()}...")

        # Fetch all pages for this day
        page_token = None
        page_num = 0

        while True:
            page_num += 1

            try:
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
                response = fetch_news_page(
                    symbols=symbols,
                    start=start_iso,
                    end=end_iso,
                    api_key=api_key,
                    api_secret=api_secret,
                    page_token=page_token,
                )

                requests_made += 1

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

                print(f"  Page {page_num}: {len(articles)} articles (total: {articles_fetched})")

                # Check for next page
                page_token = response.get("next_page_token")
                if not page_token:
                    break

                # Rate limiting: simple delay between requests
                # TODO: Implement proper RPM tracking
                time.sleep(60 / quota_rpm)  # Spread requests evenly

            except requests.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited - backoff
                    print(f"  ⚠ Rate limited, backing off 60s...")
                    time.sleep(60)
                    continue
                else:
                    print(f"  ✗ HTTP error: {e}")
                    break
            except Exception as e:
                print(f"  ✗ Error fetching page: {e}")
                break

        # Move to next day
        current_date = next_date

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

    # Summary
    print("\n" + "="*60)
    print("Backfill complete!")
    print(f"  Articles fetched: {articles_fetched}")
    print(f"  API requests: {requests_made}")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"  Run ID: {run_id}")
    print("="*60)

    return {
        "articles_fetched": articles_fetched,
        "requests_made": requests_made,
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
