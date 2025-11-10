"""Generate sanitized sample Parquet files for testing and CI.

This script creates minimal synthetic data that conforms to the ORBIT schemas
without requiring any external API keys or real data sources.
"""

from datetime import datetime, timedelta
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path


def generate_sample_prices(data_dir: Path, date_str: str = "2024-11-05") -> None:
    """Generate sample price data for SPY, VOO, and ^SPX.

    Args:
        data_dir: Root data directory
        date_str: Trading date (YYYY-MM-DD)
    """
    base_date = pd.Timestamp(date_str)

    # Generate 3 symbols with realistic price data
    symbols_data = []
    for symbol, base_price in [("SPY", 450.0), ("VOO", 410.0), ("^SPX", 4500.0)]:
        # Create OHLCV data with realistic constraints
        open_price = base_price
        high_price = base_price * 1.008  # +0.8% intraday high
        low_price = base_price * 0.995   # -0.5% intraday low
        close_price = base_price * 1.003 # +0.3% daily gain
        volume = 85_000_000 if symbol == "SPY" else 72_000_000 if symbol == "VOO" else 0

        symbols_data.append({
            "date": str(base_date.date()),
            "symbol": symbol,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume,
            "adjusted_close": round(close_price, 2),
            "source": "stooq",
            "ingestion_ts": pd.Timestamp("2024-11-05 16:10:00", tz="America/New_York"),
        })

    df = pd.DataFrame(symbols_data)

    # Write to sample directory
    output_dir = data_dir / "sample" / "prices" / "2024" / "11" / "05"
    output_dir.mkdir(parents=True, exist_ok=True)

    for symbol in ["SPY", "VOO", "^SPX"]:
        df_symbol = df[df["symbol"] == symbol]
        output_path = output_dir / f"{symbol}.parquet"
        df_symbol.to_parquet(output_path, index=False, compression="snappy", engine="fastparquet")

    print(f"✓ Generated sample prices: {output_dir}")


def generate_sample_news(data_dir: Path, date_str: str = "2024-11-05") -> None:
    """Generate sample news data.

    Args:
        data_dir: Root data directory
        date_str: Trading date (YYYY-MM-DD)
    """
    base_date = pd.Timestamp(date_str, tz="America/New_York")

    # Create 5 synthetic news items
    news_items = []
    headlines = [
        "Fed Holds Rates Steady Amid Inflation Concerns",
        "Tech Stocks Rally on Strong Earnings Reports",
        "Market Volatility Increases Before Election Day",
        "S&P 500 Reaches New All-Time High",
        "Economic Data Shows Continued Growth",
    ]

    for i, headline in enumerate(headlines):
        content = f"{headline}. Market analysts predict continued momentum..."
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        news_items.append({
            "id": f"alpaca_news_{date_str.replace('-', '')}_{i:04d}",
            "published_at": base_date + timedelta(hours=9 + i),
            "headline": headline,
            "summary": content,
            "author": f"Analyst_{i}",
            "source": ["Reuters", "Bloomberg", "WSJ", "CNBC", "MarketWatch"][i],
            "url": f"https://example.com/news/{i}",
            "symbols": [["SPY", "VOO"], ["SPY"], ["SPY", "VOO"], ["SPY"], ["VOO"]][i],
            "sentiment_gemini": [0.15, 0.35, -0.20, 0.45, 0.10][i],
            "novelty_score": [0.87, 0.65, 0.92, 0.45, 0.73][i],
            "content_hash": f"sha256:{content_hash}",
            "ingestion_ts": pd.Timestamp("2024-11-05 15:30:00", tz="America/New_York"),
            "ingestion_complete": True,
            "ingestion_gaps_minutes": 0,
            "last_successful_fetch_utc": pd.Timestamp("2024-11-05 20:30:00", tz="UTC"),
        })

    df = pd.DataFrame(news_items)

    # Write to sample directory
    output_dir = data_dir / "sample" / "news" / "2024" / "11" / "05"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "alpaca.parquet"
    df.to_parquet(output_path, index=False, compression="snappy", engine="fastparquet")

    print(f"✓ Generated sample news: {output_path}")


def generate_sample_social(data_dir: Path, date_str: str = "2024-11-05") -> None:
    """Generate sample social (Reddit) data.

    Args:
        data_dir: Root data directory
        date_str: Trading date (YYYY-MM-DD)
    """
    base_date = pd.Timestamp(date_str, tz="America/New_York")

    # Create 6 synthetic Reddit posts
    social_items = []
    posts = [
        ("SPY calls printing today 🚀", "wallstreetbets", 5432, True, 0.58),
        ("Long-term outlook on VOO", "investing", 12340, False, 0.25),
        ("Market analysis: tech sector strength", "stocks", 8765, False, 0.40),
        ("SPY vs VOO comparison", "investing", 15678, False, 0.10),
        ("Fed decision was bullish", "wallstreetbets", 3421, True, 0.65),
        ("S&P 500 all-time highs discussion", "stocks", 9876, False, 0.35),
    ]

    for i, (title, subreddit, karma, sarcasm, sentiment) in enumerate(posts):
        content = f"{title}. Here's my analysis..."
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        social_items.append({
            "id": f"reddit_{date_str.replace('-', '')}_{i:06x}",
            "created_utc": base_date + timedelta(hours=10 + i * 0.75),
            "subreddit": subreddit,
            "author": f"hash_u{i:07d}",
            "author_karma": karma,
            "author_age_days": 365 + i * 100,
            "title": title,
            "body": content,
            "permalink": f"/r/{subreddit}/comments/{i}/...",
            "upvote_ratio": 0.75 + i * 0.02,
            "num_comments": 20 + i * 10,
            "symbols": [["SPY"], ["VOO"], ["SPY"], ["SPY", "VOO"], ["SPY"], ["SPY"]][i],
            "sentiment_gemini": sentiment,
            "sarcasm_flag": sarcasm,
            "novelty_score": 0.3 + i * 0.1,
            "content_hash": f"sha256:{content_hash}",
            "ingestion_ts": pd.Timestamp("2024-11-05 15:35:00", tz="America/New_York"),
            "ingestion_complete": True,
            "ingestion_gaps_minutes": 0,
            "last_successful_fetch_utc": pd.Timestamp("2024-11-05 20:35:00", tz="UTC"),
        })

    df = pd.DataFrame(social_items)

    # Write to sample directory
    output_dir = data_dir / "sample" / "social" / "2024" / "11" / "05"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "reddit.parquet"
    df.to_parquet(output_path, index=False, compression="snappy", engine="fastparquet")

    print(f"✓ Generated sample social: {output_path}")


def generate_sample_features(data_dir: Path, date_str: str = "2024-11-05") -> None:
    """Generate sample feature data (minimal for testing).

    Args:
        data_dir: Root data directory
        date_str: Trading date (YYYY-MM-DD)
    """
    base_date = pd.Timestamp(date_str)

    # Single row with representative feature values
    features = {
        "date": str(base_date.date()),
        "symbol": "SPY",

        # Price features
        "momentum_5d": 0.012,
        "momentum_20d": 0.038,
        "momentum_50d": 0.085,
        "reversal_1d": 0.003,
        "rv_10d": 0.15,
        "drawdown_20d": -0.02,
        "etf_index_basis": 0.0001,
        "vix_level": 18.5,
        "vix_change": -0.5,
        "price_z_5d": 0.8,
        "price_z_20d": 1.2,
        "vol_z": -0.3,
        "drawdown_z": -0.5,

        # News features
        "news_count_1d": 5,
        "news_count_z": 1.8,
        "news_sentiment_mean": 0.12,
        "news_sentiment_max": 0.45,
        "news_sentiment_min": -0.20,
        "news_sentiment_std": 0.23,
        "news_novelty_mean": 0.72,
        "news_source_weight": 3.5,
        "news_gemini_mean": 0.17,
        "news_event_earnings": False,
        "news_event_fed": True,
        "news_event_macro": False,
        "news_burst_flag": False,

        # Social features
        "post_count_1d": 6,
        "post_count_z": 0.9,
        "comment_velocity": 35.5,
        "social_sentiment_mean": 0.39,
        "social_sentiment_max": 0.65,
        "social_sentiment_min": 0.10,
        "social_novelty_mean": 0.50,
        "social_cred_weighted_sent": 0.42,
        "social_gemini_mean": 0.39,
        "sarcasm_rate": 0.167,
        "social_burst_flag": False,
        "wsb_sentiment": 0.62,
        "avg_author_karma": 9252.0,

        # Labels
        "label_next_return": 0.0082,
        "label_next_excess_return": 0.0015,
        "label_up_down": 1,

        # Metadata
        "feature_ts": pd.Timestamp("2024-11-05 15:32:00", tz="America/New_York"),
        "data_completeness": 1.0,
    }

    df = pd.DataFrame([features])

    # Write to sample directory
    output_dir = data_dir / "sample" / "features" / "2024" / "11" / "05"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "features_daily.parquet"
    df.to_parquet(output_path, index=False, compression="snappy", engine="fastparquet")

    print(f"✓ Generated sample features: {output_path}")


def main():
    """Generate all sample data files."""
    # Use ./data as default (or ORBIT_DATA_DIR if set)
    import os
    data_dir = Path(os.getenv("ORBIT_DATA_DIR", "data"))

    print(f"Generating sample data in {data_dir}...")

    generate_sample_prices(data_dir)
    generate_sample_news(data_dir)
    generate_sample_social(data_dir)
    generate_sample_features(data_dir)

    print("\n✓ All sample data generated successfully!")
    print(f"\nFiles created:")
    print(f"  - {data_dir}/sample/prices/2024/11/05/{{SPY,VOO,^SPX}}.parquet")
    print(f"  - {data_dir}/sample/news/2024/11/05/alpaca.parquet")
    print(f"  - {data_dir}/sample/social/2024/11/05/reddit.parquet")
    print(f"  - {data_dir}/sample/features/2024/11/05/features_daily.parquet")


if __name__ == "__main__":
    main()
