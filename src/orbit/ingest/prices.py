"""ORBIT Prices Ingestion - Stooq CSV downloader.

Fetches daily OHLCV data for SPY.US, VOO.US, and ^SPX from Stooq,
normalizes to canonical schema, and writes to /srv/orbit/data/raw/prices/
and /srv/orbit/data/curated/prices/ (or ORBIT_DATA_DIR/raw/prices if configured).
"""

import io
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from orbit import io as orbit_io


def scan_existing_dates(data_dir: Path, symbols: list[str]) -> set[str]:
    """Scan existing date partitions to determine what dates are already ingested.

    Args:
        data_dir: Base data directory (e.g., /srv/orbit/data or ./data)
        symbols: List of symbols to check

    Returns:
        Set of date strings (YYYY-MM-DD) that have data for ALL symbols
    """
    raw_prices_dir = data_dir / "raw" / "prices"

    if not raw_prices_dir.exists():
        return set()

    # Find all date partitions
    date_partitions = [d.name.replace('date=', '') for d in raw_prices_dir.iterdir() if d.is_dir() and d.name.startswith('date=')]

    # For each date, check if ALL symbols have data
    complete_dates = set()
    for date_str in date_partitions:
        date_dir = raw_prices_dir / f"date={date_str}"
        symbol_files = {f.stem for f in date_dir.glob("*.parquet")}

        # Check if all symbols are present (normalize symbol names)
        expected_symbols = {s.replace('.', '_').replace('^', '') for s in symbols}
        if expected_symbols.issubset(symbol_files):
            complete_dates.add(date_str)

    return complete_dates


def fetch_stooq_csv(
    symbol: str,
    base_url: str = "https://stooq.com/q/d/l/",
    polite_delay_sec: float = 1.0,
    retries: int = 3,
) -> bytes:
    """Fetch CSV data from Stooq for a given symbol.

    Args:
        symbol: Stock symbol (e.g., 'SPY.US', 'VOO.US', '^SPX')
        base_url: Base URL for Stooq API
        polite_delay_sec: Delay between requests (be polite!)
        retries: Number of retry attempts on failure

    Returns:
        Raw CSV bytes

    Raises:
        requests.HTTPError: If all retries fail
    """
    # URL-encode symbol (e.g., ^SPX -> %5ESPX)
    encoded_symbol = urllib.parse.quote(symbol.lower())
    url = f"{base_url}?s={encoded_symbol}&i=d"

    for attempt in range(retries):
        try:
            # Add User-Agent to be polite
            headers = {
                "User-Agent": "ORBIT/1.0 (Educational project; +https://github.com/calebyhan/orbit)"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Be polite - add delay before next request
            if polite_delay_sec > 0:
                time.sleep(polite_delay_sec)

            return response.content

        except Exception as e:
            if attempt < retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                print(f"  Retry {attempt + 1}/{retries} for {symbol} after {wait_time}s (error: {e})")
                time.sleep(wait_time)
            else:
                raise


def normalize_stooq_csv(
    csv_bytes: bytes,
    symbol: str,
    run_id: str,
) -> pd.DataFrame:
    """Normalize Stooq CSV to canonical schema.

    Args:
        csv_bytes: Raw CSV bytes from Stooq
        symbol: Symbol identifier (e.g., 'SPY.US')
        run_id: Unique run identifier

    Returns:
        DataFrame with normalized schema
    """
    # Parse CSV
    df = pd.read_csv(io.BytesIO(csv_bytes))

    # Lowercase column names
    df.columns = [c.lower() for c in df.columns]

    # Add metadata columns
    df["symbol"] = symbol
    df["source"] = "stooq"
    df["run_id"] = run_id
    df["ingested_at"] = pd.Timestamp.utcnow()

    # Parse and normalize date
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)

    # Coerce price columns to float
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Coerce volume to nullable int64
    if "volume" in df.columns:
        # First convert to numeric, coercing errors to NaN
        vol_numeric = pd.to_numeric(df["volume"], errors="coerce")
        # Round float volumes to integers (some sources provide adjusted float volumes)
        vol_rounded = vol_numeric.round()
        # Then convert to Int64 (nullable integer type)
        df["volume"] = vol_rounded.astype("Int64")
    else:
        df["volume"] = pd.NA

    # Reorder columns for consistency
    column_order = [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "run_id",
        "ingested_at",
    ]

    # Keep only columns that exist
    df = df[[col for col in column_order if col in df.columns]]

    return df


def validate_prices_df(df: pd.DataFrame, allow_single_date: bool = False) -> list[str]:
    """Run QC checks on price data.

    Args:
        df: Price DataFrame to validate
        allow_single_date: If True, skip monotonicity checks (for single-day ingestion)

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if df.empty:
        errors.append("DataFrame is empty")
        return errors

    # Check required columns
    required_cols = ["date", "symbol", "open", "high", "low", "close"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        errors.append(f"Missing required columns: {missing}")
        return errors

    # Sort by date for monotonicity check
    df_sorted = df.sort_values("date")

    # Check date monotonicity (strictly increasing within symbol) - only if multiple dates
    if not allow_single_date and df_sorted["date"].duplicated().any():
        dup_dates = df_sorted[df_sorted["date"].duplicated()]["date"].unique()
        errors.append(f"Duplicate dates found: {dup_dates}")

    # Price constraints
    if (df["low"] <= 0).any():
        errors.append("Non-positive prices detected (low <= 0)")

    if (df["high"] < df["low"]).any():
        errors.append("Price constraint violated: high < low")

    if (df["high"] < df["open"]).any():
        errors.append("Price constraint violated: high < open")

    if (df["high"] < df["close"]).any():
        errors.append("Price constraint violated: high < close")

    if (df["low"] > df["open"]).any():
        errors.append("Price constraint violated: low > open")

    if (df["low"] > df["close"]).any():
        errors.append("Price constraint violated: low > close")

    # Volume constraints (nullable, but if present should be >= 0)
    if "volume" in df.columns:
        if (df["volume"].notna() & (df["volume"] < 0)).any():
            errors.append("Negative volume detected")

    return errors


def ingest_prices(
    symbols: Optional[list[str]] = None,
    base_url: str = "https://stooq.com/q/d/l/",
    polite_delay_sec: float = 1.0,
    retries: int = 3,
    run_id: Optional[str] = None,
    write_raw: bool = True,
    write_curated: bool = True,
    reset: bool = False,
    start_date: Optional[str] = None,
) -> dict[str, pd.DataFrame]:
    """Ingest prices from Stooq for specified symbols.

    Args:
        symbols: List of symbols to fetch (defaults to SPY.US, VOO.US, ^SPX)
        base_url: Stooq API base URL
        polite_delay_sec: Delay between requests
        retries: Number of retry attempts
        run_id: Unique run identifier (auto-generated if None)
        write_raw: Whether to write raw data to disk
        write_curated: Whether to write curated data to disk
        reset: If True, re-fetch all history; if False (default), only fetch missing dates
        start_date: Optional start date (YYYY-MM-DD) to limit history fetch

    Returns:
        Dict mapping symbol to DataFrame
        
    Note:
        Data is written to ORBIT_DATA_DIR/raw/prices/date=YYYY-MM-DD/{symbol}.parquet.
        By default, scans existing dates and only fetches new/missing dates.
        Use --reset to force re-ingestion of all historical data.
        For production, set ORBIT_DATA_DIR=/srv/orbit/data before running.
        Without it, defaults to ./data which should ONLY contain sample data.
    """
    # Default symbols
    if symbols is None:
        symbols = ["SPY.US", "VOO.US", "^SPX"]

    # Generate run_id if not provided
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Get data directory
    data_dir = orbit_io.get_data_dir()

    # Scan existing dates (unless --reset)
    existing_dates = set()
    if not reset:
        existing_dates = scan_existing_dates(data_dir, symbols)
        if existing_dates:
            print(f"Found {len(existing_dates)} existing date partitions")
            print(f"  Date range: {min(existing_dates)} to {max(existing_dates)}")
            print(f"  Mode: Incremental (only fetching new/missing dates)")
        else:
            print("No existing data found - fetching full history")
    else:
        print("Reset mode: Re-fetching all historical data")

    print(f"Starting prices ingestion (run_id: {run_id})")
    print(f"Symbols: {symbols}")

    results = {}
    total_dates_written = 0

    for symbol in symbols:
        print(f"\nFetching {symbol}...")

        try:
            # Fetch CSV from Stooq (always fetches full history)
            csv_bytes = fetch_stooq_csv(
                symbol=symbol,
                base_url=base_url,
                polite_delay_sec=polite_delay_sec,
                retries=retries,
            )

            # Normalize to canonical schema
            df = normalize_stooq_csv(csv_bytes=csv_bytes, symbol=symbol, run_id=run_id)

            # Apply start_date filter if provided
            if start_date:
                df = df[df['date'] >= start_date]
                print(f"  Filtered to dates >= {start_date}")

            # Filter to only new dates (unless reset mode)
            if not reset and existing_dates:
                df_new = df[~df['date'].isin(existing_dates)]
                skipped = len(df) - len(df_new)
                if skipped > 0:
                    print(f"  Skipping {skipped} already-ingested dates")
                df = df_new

            if df.empty:
                print(f"  ℹ No new dates to ingest for {symbol}")
                continue

            # Validate
            errors = validate_prices_df(df, allow_single_date=True)
            if errors:
                print(f"  ✗ Validation failed for {symbol}:")
                for err in errors:
                    print(f"    - {err}")
                continue

            print(f"  ✓ Fetched {len(df)} rows for {symbol}")
            print(f"    Date range: {df['date'].min()} to {df['date'].max()}")
            if not df.empty:
                print(f"    Latest close: ${df.iloc[-1]['close']:.2f}")

            results[symbol] = df

            # Write raw data (date-partitioned)
            if write_raw:
                symbol_clean = symbol.replace('.', '_').replace('^', '')
                
                # Group by date and write to separate partitions
                dates_written = 0
                for date_str, group in df.groupby('date'):
                    raw_path = f"raw/prices/date={date_str}/{symbol_clean}.parquet"
                    orbit_io.write_parquet(group, raw_path, overwrite=True)
                    dates_written += 1
                
                total_dates_written += dates_written
                print(f"    → Wrote raw data to {dates_written} date partitions")

            # Write curated data (same as raw for prices - no additional cleaning needed)
            if write_curated:
                symbol_clean = symbol.replace('.', '_').replace('^', '')
                
                # Group by date and write to separate partitions
                for date_str, group in df.groupby('date'):
                    curated_path = f"curated/prices/date={date_str}/{symbol_clean}.parquet"
                    orbit_io.write_parquet(group, curated_path, overwrite=True)
                
                print(f"    → Wrote curated data to {dates_written} date partitions")

        except Exception as e:
            print(f"  ✗ Error fetching {symbol}: {e}")
            continue

    print(f"\n✓ Ingestion complete: {len(results)}/{len(symbols)} symbols succeeded")
    if total_dates_written > 0:
        print(f"  Total date partitions written: {total_dates_written}")

    return results


if __name__ == "__main__":
    # CLI entrypoint for testing
    import sys

    symbols = sys.argv[1:] if len(sys.argv) > 1 else None
    results = ingest_prices(symbols=symbols)

    print("\nSummary:")
    for symbol, df in results.items():
        print(f"  {symbol}: {len(df)} rows")
