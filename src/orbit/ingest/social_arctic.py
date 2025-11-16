"""ORBIT Social Backfill - Arctic Shift Reddit API historical post fetcher.

Fetches historical Reddit posts from Arctic Shift Photon Reddit API.
This is an unofficial archive service that provides historical Reddit data via REST API.

Implements historical social data collection as documented in:
docs/04-data-sources/reddit_arctic_api.md
docs/05-ingestion/social_reddit_ingest.md
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

from orbit import io as orbit_io


# Arctic Shift API configuration
ARCTIC_API_BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
DEFAULT_LIMIT = 25  # API caps at ~25-40 per request
TARGET_RPS = 3.5  # Target 3.5 requests/second (from empirical testing)
CHECKPOINT_INTERVAL = 100  # Save checkpoint every N requests
MAX_RETRY_ATTEMPTS = 5  # Max retries for errors

# Default subreddits for ORBIT
DEFAULT_SUBREDDITS = ["stocks", "investing", "wallstreetbets"]


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


def extract_matched_terms(title: str, body: str) -> list[str]:
    """Extract market-related terms from post text.

    Matches SPY, VOO, S&P 500 mentions while filtering false positives.

    Args:
        title: Post title
        body: Post body text

    Returns:
        List of matched terms (e.g., ["SPY", "S&P 500"])
    """
    text = f"{title} {body or ''}".lower()
    terms = []

    # SPY (filter spy camera, spying, etc.)
    if "spy" in text and not any(x in text for x in ["spy camera", "spying", "i spy", "spy on"]):
        terms.append("SPY")

    # VOO
    if "voo" in text:
        terms.append("VOO")

    # S&P 500 variants
    if any(x in text for x in ["s&p 500", "s&p500", "sp500", "s & p 500"]):
        terms.append("S&P 500")

    # S&P (filter S&P Global, S&P ratings)
    if "s&p" in text and not any(x in text for x in ["s&p global", "s&p rating"]):
        terms.append("S&P")

    # Market (filter supermarket, marketplace)
    if "market" in text and not any(x in text for x in ["supermarket", "marketplace", "market share", "marketing"]):
        terms.append("market")

    return terms if terms else ["off-topic"]


def compute_content_hash(title: str, body: str) -> str:
    """Compute SHA256 hash of post content for deduplication.

    Args:
        title: Post title
        body: Post body text

    Returns:
        SHA256 hash as hex string
    """
    content = f"{title}||{body or ''}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def hash_author(author: str) -> str:
    """Hash author username for privacy.

    Args:
        author: Reddit username

    Returns:
        Hashed username (hash_XXXXXXXX)
    """
    author_hash = hashlib.sha256(author.encode('utf-8')).hexdigest()[:8]
    return f"hash_{author_hash}"


def normalize_arctic_post(post: dict, received_at: datetime, run_id: str) -> dict:
    """Normalize Arctic Shift API post to ORBIT schema.

    Converts Arctic post format to canonical social.parquet schema.
    Maps fields and applies filtering for removed content.

    Args:
        post: Raw post dict from Arctic API
        received_at: Time post was fetched
        run_id: Unique run identifier

    Returns:
        Normalized post dict matching social.parquet schema
    """
    # Extract basic fields
    post_id = post.get("id")
    created_utc_unix = post.get("created_utc")
    subreddit = post.get("subreddit")
    author = post.get("author", "[deleted]")
    title = post.get("title", "")
    selftext = post.get("selftext", "")
    score = post.get("score", 0)
    upvote_ratio = post.get("upvote_ratio")
    num_comments = post.get("num_comments", 0)
    permalink = post.get("permalink", "")

    # Convert Unix timestamp to timezone-aware UTC datetime
    created_utc = pd.to_datetime(created_utc_unix, unit='s', utc=True)

    # Handle removed content
    removed_by = post.get("removed_by_category")
    if selftext == "[removed]" or selftext == "[deleted]":
        selftext = None  # Treat removed content as null

    # Extract matched terms
    matched_terms = extract_matched_terms(title, selftext or "")

    # Arctic API doesn't provide author karma or age
    # These fields will be null and can be enriched later via official API if needed
    author_karma = None
    author_age_days = None

    # Compute content hash for deduplication
    content_hash = compute_content_hash(title, selftext or "")

    # Hash author for privacy
    author_hashed = hash_author(author)

    # Fields for Gemini sentiment (will be filled in later processing)
    sentiment_gemini = None
    sarcasm_flag = None
    novelty_score = None

    # Ingestion tracking
    ingestion_ts = received_at
    ingestion_complete = True  # Will be updated at day-level
    ingestion_gaps_minutes = 0  # Will be updated at day-level
    last_successful_fetch_utc = received_at

    return {
        "id": post_id,
        "created_utc": created_utc,
        "subreddit": subreddit,
        "author": author_hashed,
        "author_karma": author_karma,
        "author_age_days": author_age_days,
        "title": title,
        "body": selftext,
        "permalink": permalink,
        "upvote_ratio": upvote_ratio,
        "num_comments": num_comments,
        "symbols": matched_terms,
        "sentiment_gemini": sentiment_gemini,
        "sarcasm_flag": sarcasm_flag,
        "novelty_score": novelty_score,
        "content_hash": content_hash,
        "ingestion_ts": ingestion_ts,
        "ingestion_complete": ingestion_complete,
        "ingestion_gaps_minutes": ingestion_gaps_minutes,
        "last_successful_fetch_utc": last_successful_fetch_utc,
    }


def fetch_posts_for_day(
    subreddit: str,
    date: datetime,
    limit: int = DEFAULT_LIMIT,
    timeout: int = 30,
) -> list[dict]:
    """Fetch all posts for a specific day from Arctic Shift API.

    Paginates through all posts for the day using time-based iteration.

    Args:
        subreddit: Subreddit name (without r/)
        date: Date to fetch posts for
        limit: Max posts per request (default: 25)
        timeout: Request timeout in seconds

    Returns:
        List of raw post dicts from API

    Raises:
        requests.HTTPError: If request fails
    """
    # Define time window for the day
    after = date.strftime("%Y-%m-%dT00:00")
    before = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00")

    params = {
        "subreddit": subreddit,
        "after": after,
        "before": before,
        "limit": limit,
        "sort": "desc",  # Most recent first
    }

    headers = {
        "User-Agent": os.getenv("ORBIT_USER_AGENT", "ORBIT/1.0 (Educational project; +https://github.com/calebyhan/orbit)"),
    }

    all_posts = []
    page = 0
    max_pages = 100  # Safety limit to prevent infinite loops

    while page < max_pages:
        try:
            response = requests.get(
                ARCTIC_API_BASE,
                params=params,
                headers=headers,
                timeout=timeout,
            )
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", [])

            if not posts:
                break  # No more posts

            all_posts.extend(posts)

            # Check if we got fewer than limit (indicates end of data)
            if len(posts) < limit:
                break

            # Update 'after' parameter to earliest created_utc from this batch
            # This allows pagination within the day
            earliest_timestamp = min(post["created_utc"] for post in posts)
            earliest_dt = datetime.fromtimestamp(earliest_timestamp, tz=timezone.utc)
            params["after"] = earliest_dt.strftime("%Y-%m-%dT%H:%M:%S")

            page += 1

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                # Bad request (likely reached end of data)
                break
            raise

    return all_posts


def backfill_social(
    start_date: str,
    end_date: str,
    subreddits: list[str],
    data_dir: Optional[Path] = None,
    resume: bool = True,
) -> dict:
    """Backfill historical Reddit posts from Arctic Shift API.

    Fetches posts day-by-day for specified subreddits and date range.
    Implements checkpoint/resume for reliability.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        subreddits: List of subreddit names (e.g., ["stocks", "investing"])
        data_dir: Data directory (defaults to ORBIT_DATA_DIR env var)
        resume: Whether to resume from checkpoint if exists

    Returns:
        Dict with stats: {
            "total_posts": int,
            "total_requests": int,
            "elapsed_time": float,
            "avg_rps": float,
        }
    """
    # Get data directory
    if data_dir is None:
        data_dir = Path(os.getenv("ORBIT_DATA_DIR", "./data"))

    # Parse date range
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Generate list of all dates
    date_range = pd.date_range(start_dt, end_dt, freq="D")

    # Generate run ID
    run_id = f"{datetime.now():%Y%m%d_%H%M%S}_backfill"

    # Checkpoint file
    checkpoint_file = Path(f".social_backfill_checkpoint_{run_id}.json")

    # Load checkpoint if resuming
    checkpoint = None
    if resume and checkpoint_file.exists():
        checkpoint = load_checkpoint(checkpoint_file)
        print(f"✓ Resuming from checkpoint: {checkpoint_file}")
        print(f"  Previous progress: {checkpoint['total_posts']} posts, {checkpoint['total_requests']} requests")
        print(f"  Resuming from: {checkpoint['current_date']}")

    # Initialize stats
    total_posts = checkpoint["total_posts"] if checkpoint else 0
    total_requests = checkpoint["total_requests"] if checkpoint else 0
    start_time = time.time()

    # Calculate request interval (1 / RPS)
    request_interval = 1.0 / TARGET_RPS

    # Progress bar
    total_days = len(date_range) * len(subreddits)
    progress_bar = tqdm(
        total=total_days,
        desc="Backfill progress",
        unit="day",
        initial=checkpoint["completed_days"] if checkpoint else 0,
    )

    try:
        for date in date_range:
            date_str = date.strftime("%Y-%m-%d")

            # Skip if before checkpoint date
            if checkpoint and date_str < checkpoint["current_date"]:
                continue

            for subreddit in subreddits:
                # Skip if already completed in checkpoint
                if checkpoint and f"{date_str}_{subreddit}" in checkpoint.get("completed_dates", []):
                    progress_bar.update(1)
                    continue

                # Fetch posts for this day/subreddit
                request_start = time.time()
                posts = fetch_posts_for_day(subreddit, date)
                total_requests += 1

                # Normalize posts
                received_at = datetime.now(timezone.utc)
                normalized_posts = [
                    normalize_arctic_post(post, received_at, run_id)
                    for post in posts
                ]

                # Filter posts that match our terms (not off-topic)
                matched_posts = [
                    post for post in normalized_posts
                    if "off-topic" not in post["symbols"]
                ]

                # Save to parquet if we have posts
                if matched_posts:
                    df = pd.DataFrame(matched_posts)

                    # Convert created_utc to datetime if not already
                    if not pd.api.types.is_datetime64_any_dtype(df["created_utc"]):
                        df["created_utc"] = pd.to_datetime(df["created_utc"], utc=True)

                    # Save to date-partitioned parquet
                    output_path = data_dir / "raw" / "social" / f"date={date_str}" / "social.parquet"
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Append to existing file if it exists
                    if output_path.exists():
                        existing_df = pd.read_parquet(output_path)
                        df = pd.concat([existing_df, df], ignore_index=True)
                        # Deduplicate by id
                        df = df.drop_duplicates(subset=["id"], keep="first")

                    df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

                total_posts += len(matched_posts)

                # Update progress bar
                elapsed = time.time() - start_time
                current_rps = total_requests / elapsed if elapsed > 0 else 0
                progress_bar.set_postfix({
                    "posts": total_posts,
                    "requests": total_requests,
                    "rps": f"{current_rps:.2f}",
                })
                progress_bar.update(1)

                # Save checkpoint every CHECKPOINT_INTERVAL requests
                if total_requests % CHECKPOINT_INTERVAL == 0:
                    checkpoint_data = {
                        "total_posts": total_posts,
                        "total_requests": total_requests,
                        "current_date": date_str,
                        "completed_days": progress_bar.n,
                        "completed_dates": checkpoint.get("completed_dates", []) + [f"{date_str}_{subreddit}"],
                    }
                    save_checkpoint(checkpoint_file, checkpoint_data)

                # Rate limiting - ensure we don't exceed target RPS
                request_duration = time.time() - request_start
                sleep_time = request_interval - request_duration
                if sleep_time > 0:
                    time.sleep(sleep_time)

    finally:
        progress_bar.close()

    # Calculate final stats
    elapsed_time = time.time() - start_time
    avg_rps = total_requests / elapsed_time if elapsed_time > 0 else 0

    # Remove checkpoint on successful completion
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    print(f"\n✓ Backfill complete!")
    print(f"  Posts fetched: {total_posts:,}")
    print(f"  API requests: {total_requests:,}")
    print(f"  Elapsed time: {elapsed_time / 3600:.1f}h")
    print(f"  Average rate: {avg_rps:.2f} requests/second")

    return {
        "total_posts": total_posts,
        "total_requests": total_requests,
        "elapsed_time": elapsed_time,
        "avg_rps": avg_rps,
    }


def main():
    """CLI entry point for social backfill."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Backfill historical Reddit posts from Arctic Shift API"
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--subreddits",
        nargs="+",
        default=DEFAULT_SUBREDDITS,
        help=f"Subreddits to fetch (default: {' '.join(DEFAULT_SUBREDDITS)})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Data directory (default: ORBIT_DATA_DIR env var)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Don't resume from checkpoint (start fresh)",
    )

    args = parser.parse_args()

    # Run backfill
    backfill_social(
        start_date=args.start,
        end_date=args.end,
        subreddits=args.subreddits,
        data_dir=args.data_dir,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
