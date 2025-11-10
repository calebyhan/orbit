"""ORBIT Prices Ingestion - Stooq CSV downloader.

Fetches daily OHLCV data for SPY.US, VOO.US, and ^SPX from Stooq,
normalizes to canonical schema, and writes to data/raw/prices/ and data/curated/prices/.
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


def validate_prices_df(df: pd.DataFrame) -> list[str]:
    """Run QC checks on price data.

    Args:
        df: Price DataFrame to validate

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

    # Check date monotonicity (strictly increasing within symbol)
    if df_sorted["date"].duplicated().any():
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

    Returns:
        Dict mapping symbol to DataFrame
    """
    # Default symbols
    if symbols is None:
        symbols = ["SPY.US", "VOO.US", "^SPX"]

    # Generate run_id if not provided
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(f"Starting prices ingestion (run_id: {run_id})")
    print(f"Symbols: {symbols}")

    results = {}

    for symbol in symbols:
        print(f"\nFetching {symbol}...")

        try:
            # Fetch CSV from Stooq
            csv_bytes = fetch_stooq_csv(
                symbol=symbol,
                base_url=base_url,
                polite_delay_sec=polite_delay_sec,
                retries=retries,
            )

            # Normalize to canonical schema
            df = normalize_stooq_csv(csv_bytes=csv_bytes, symbol=symbol, run_id=run_id)

            # Validate
            errors = validate_prices_df(df)
            if errors:
                print(f"  ✗ Validation failed for {symbol}:")
                for err in errors:
                    print(f"    - {err}")
                continue

            print(f"  ✓ Fetched {len(df)} rows for {symbol}")
            print(f"    Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"    Latest close: ${df.iloc[-1]['close']:.2f}")

            results[symbol] = df

            # Write raw data (append-only)
            if write_raw:
                # Get today's date for partitioning
                latest_date = pd.to_datetime(df["date"].max())
                year, month, day = latest_date.year, latest_date.month, latest_date.day

                raw_path = f"raw/prices/{year:04d}/{month:02d}/{day:02d}/{symbol.replace('.', '_').replace('^', '')}.parquet"

                orbit_io.write_parquet(df, raw_path, overwrite=True)
                print(f"    → Wrote raw data to {raw_path}")

            # Write curated data (same as raw for prices - no additional cleaning needed)
            if write_curated:
                latest_date = pd.to_datetime(df["date"].max())
                year, month, day = latest_date.year, latest_date.month, latest_date.day

                curated_path = f"curated/prices/{year:04d}/{month:02d}/{day:02d}/{symbol.replace('.', '_').replace('^', '')}.parquet"

                orbit_io.write_parquet(df, curated_path, overwrite=True)
                print(f"    → Wrote curated data to {curated_path}")

        except Exception as e:
            print(f"  ✗ Error fetching {symbol}: {e}")
            continue

    print(f"\n✓ Ingestion complete: {len(results)}/{len(symbols)} symbols succeeded")

    return results


if __name__ == "__main__":
    # CLI entrypoint for testing
    import sys

    symbols = sys.argv[1:] if len(sys.argv) > 1 else None
    results = ingest_prices(symbols=symbols)

    print("\nSummary:")
    for symbol, df in results.items():
        print(f"  {symbol}: {len(df)} rows")
