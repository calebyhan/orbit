"""ORBIT Preprocessing Pipeline.

Unified preprocessing pipeline that applies:
1. Time alignment and cutoff enforcement (15:30 ET)
2. Deduplication (within-day)
3. Novelty scoring (vs 7-day reference window)

Implements M1 deliverable: Preprocess hooks
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from orbit import io as orbit_io
from orbit.preprocess import cutoffs, dedupe


def preprocess_news_day(
    date: str,
    data_dir: Optional[Path] = None,
    reference_window_days: int = 7,
    safety_lag_minutes: int = 30,
    training: bool = True,
    write_curated: bool = True,
) -> pd.DataFrame:
    """Preprocess news data for a single day.

    Applies cutoff enforcement, deduplication, and novelty scoring.

    Args:
        date: Date to process (YYYY-MM-DD)
        data_dir: Data directory (defaults to ORBIT_DATA_DIR)
        reference_window_days: Days in reference window for novelty
        safety_lag_minutes: Safety lag for training (minutes before cutoff)
        training: Whether this is for training (applies safety lag)
        write_curated: Whether to write curated output

    Returns:
        Preprocessed dataframe

    Writes:
        data/curated/news/date=YYYY-MM-DD/news.parquet
    """
    if data_dir is None:
        data_dir = Path(os.getenv("ORBIT_DATA_DIR", "./data"))

    # Load raw news for this date
    raw_path = data_dir / "raw" / "news" / f"date={date}" / "news.parquet"
    if not raw_path.exists():
        print(f"No raw news data for {date}")
        return pd.DataFrame()

    df = pd.read_parquet(raw_path)

    if df.empty:
        print(f"Empty raw news data for {date}")
        return pd.DataFrame()

    # Apply cutoff enforcement
    df = cutoffs.apply_cutoff(
        df,
        ts_column='published_at',
        date_T=pd.Timestamp(date),
        safety_lag_minutes=safety_lag_minutes,
        training=training,
    )

    if df.empty:
        print(f"No news items within cutoff window for {date}")
        return pd.DataFrame()

    # Load reference data for novelty scoring
    reference_df = None
    if reference_window_days > 0:
        reference_dfs = []
        for i in range(1, reference_window_days + 1):
            ref_date = (pd.Timestamp(date) - timedelta(days=i)).strftime('%Y-%m-%d')
            ref_path = data_dir / "curated" / "news" / f"date={ref_date}" / "news.parquet"
            if ref_path.exists():
                ref_df = pd.read_parquet(ref_path)
                reference_dfs.append(ref_df)

        if reference_dfs:
            reference_df = pd.concat(reference_dfs, ignore_index=True)

    # Apply deduplication and novelty scoring
    df = dedupe.dedupe_and_score_novelty(
        df,
        text_column='headline',
        id_column='msg_id',
        reference_df=reference_df,
        window_days=reference_window_days,
    )

    # Write curated output
    if write_curated:
        curated_path = data_dir / "curated" / "news" / f"date={date}" / "news.parquet"
        curated_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(curated_path, index=False, engine="pyarrow", compression="snappy")
        print(f"✓ Wrote curated news: {curated_path}")

    # Log stats
    total = len(df)
    dupes = df['is_dupe'].sum() if 'is_dupe' in df.columns else 0
    novel = df['novelty'].mean() if 'novelty' in df.columns else None

    print(f"News {date}: {total} items ({dupes} dupes, avg novelty={novel:.3f if novel else 0:.3f})")

    return df


def preprocess_social_day(
    date: str,
    data_dir: Optional[Path] = None,
    reference_window_days: int = 7,
    safety_lag_minutes: int = 30,
    training: bool = True,
    write_curated: bool = True,
) -> pd.DataFrame:
    """Preprocess social data for a single day.

    Applies cutoff enforcement, deduplication, and novelty scoring.

    Args:
        date: Date to process (YYYY-MM-DD)
        data_dir: Data directory (defaults to ORBIT_DATA_DIR)
        reference_window_days: Days in reference window for novelty
        safety_lag_minutes: Safety lag for training (minutes before cutoff)
        training: Whether this is for training (applies safety lag)
        write_curated: Whether to write curated output

    Returns:
        Preprocessed dataframe

    Writes:
        data/curated/social/date=YYYY-MM-DD/social.parquet
    """
    if data_dir is None:
        data_dir = Path(os.getenv("ORBIT_DATA_DIR", "./data"))

    # Load raw social for this date
    raw_path = data_dir / "raw" / "social" / f"date={date}" / "social.parquet"
    if not raw_path.exists():
        print(f"No raw social data for {date}")
        return pd.DataFrame()

    df = pd.read_parquet(raw_path)

    if df.empty:
        print(f"Empty raw social data for {date}")
        return pd.DataFrame()

    # Apply cutoff enforcement
    df = cutoffs.apply_cutoff(
        df,
        ts_column='created_utc',
        date_T=pd.Timestamp(date),
        safety_lag_minutes=safety_lag_minutes,
        training=training,
    )

    if df.empty:
        print(f"No social items within cutoff window for {date}")
        return pd.DataFrame()

    # Combine title and body for deduplication
    df['text_combined'] = df['title'] + ' ' + df['body'].fillna('')

    # Load reference data for novelty scoring
    reference_df = None
    if reference_window_days > 0:
        reference_dfs = []
        for i in range(1, reference_window_days + 1):
            ref_date = (pd.Timestamp(date) - timedelta(days=i)).strftime('%Y-%m-%d')
            ref_path = data_dir / "curated" / "social" / f"date={ref_date}" / "social.parquet"
            if ref_path.exists():
                ref_df = pd.read_parquet(ref_path)
                if 'text_combined' not in ref_df.columns:
                    ref_df['text_combined'] = ref_df['title'] + ' ' + ref_df['body'].fillna('')
                reference_dfs.append(ref_df)

        if reference_dfs:
            reference_df = pd.concat(reference_dfs, ignore_index=True)

    # Apply deduplication and novelty scoring
    df = dedupe.dedupe_and_score_novelty(
        df,
        text_column='text_combined',
        id_column='id',
        reference_df=reference_df,
        window_days=reference_window_days,
    )

    # Drop temporary column
    df = df.drop(columns=['text_combined'])

    # Write curated output
    if write_curated:
        curated_path = data_dir / "curated" / "social" / f"date={date}" / "social.parquet"
        curated_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(curated_path, index=False, engine="pyarrow", compression="snappy")
        print(f"✓ Wrote curated social: {curated_path}")

    # Log stats
    total = len(df)
    dupes = df['is_dupe'].sum() if 'is_dupe' in df.columns else 0
    novel = df['novelty'].mean() if 'novelty' in df.columns else None

    print(f"Social {date}: {total} items ({dupes} dupes, avg novelty={novel:.3f if novel else 0:.3f})")

    return df


def preprocess_date_range(
    start_date: str,
    end_date: str,
    sources: list[str] = ['news', 'social'],
    data_dir: Optional[Path] = None,
    reference_window_days: int = 7,
    safety_lag_minutes: int = 30,
    training: bool = True,
) -> dict:
    """Preprocess data for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        sources: List of sources to process (['news', 'social'])
        data_dir: Data directory
        reference_window_days: Days in reference window for novelty
        safety_lag_minutes: Safety lag for training
        training: Whether this is for training

    Returns:
        Dict with processing statistics
    """
    if data_dir is None:
        data_dir = Path(os.getenv("ORBIT_DATA_DIR", "./data"))

    date_range = pd.date_range(start_date, end_date, freq='D')

    stats = {
        'total_days': len(date_range),
        'processed_news': 0,
        'processed_social': 0,
        'total_news_items': 0,
        'total_social_items': 0,
    }

    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        print(f"\nProcessing {date_str}...")

        if 'news' in sources:
            df = preprocess_news_day(
                date_str,
                data_dir=data_dir,
                reference_window_days=reference_window_days,
                safety_lag_minutes=safety_lag_minutes,
                training=training,
            )
            if not df.empty:
                stats['processed_news'] += 1
                stats['total_news_items'] += len(df)

        if 'social' in sources:
            df = preprocess_social_day(
                date_str,
                data_dir=data_dir,
                reference_window_days=reference_window_days,
                safety_lag_minutes=safety_lag_minutes,
                training=training,
            )
            if not df.empty:
                stats['processed_social'] += 1
                stats['total_social_items'] += len(df)

    return stats
