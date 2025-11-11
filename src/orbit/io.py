"""ORBIT I/O utilities for Parquet data.

Lightweight wrappers around pandas/pyarrow for reading/writing Parquet files
with schema validation and ORBIT_DATA_DIR support.

IMPORTANT: Data storage locations
- Sample data: Always in ./data/sample/ (committed to git)
- Production model: Always in ./data/models/production/ (committed to git)
- ALL production data: In /srv/orbit/data/ (set ORBIT_DATA_DIR=/srv/orbit/data)

Without ORBIT_DATA_DIR set, operations default to ./data which should
ONLY contain sample data and production models (never raw/curated/features/scores).
"""

import os
from pathlib import Path
from typing import Optional, Union

import pandas as pd

# Try to import pyarrow, fall back to fastparquet
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_ENGINE = "pyarrow"
except ImportError:
    pa = None
    pq = None
    PARQUET_ENGINE = "fastparquet"

# Auto-load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env from current directory or parents
except ImportError:
    pass  # python-dotenv not installed, skip


def get_data_dir() -> Path:
    """Get the configured data directory from ORBIT_DATA_DIR env var.

    Returns:
        Path to data directory (defaults to ./data if not set)
        
    Important:
        - For production runs: Set ORBIT_DATA_DIR=/srv/orbit/data
        - Without ORBIT_DATA_DIR: Defaults to ./data (sample data only)
        - ./data should ONLY contain:
          * ./data/sample/ (test fixtures)
          * ./data/models/production/ (latest model)
        - ALL production data lives in /srv/orbit/data/:
          * raw/, curated/, features/, scores/, models/
    """
    data_dir = os.getenv("ORBIT_DATA_DIR", "data")
    return Path(data_dir)


def _warn_if_writing_to_repo(path: Path) -> None:
    """Warn if attempting to write production data to repo directory.
    
    Checks if path starts with ./data/raw, ./data/curated, ./data/features,
    or ./data/scores and issues a warning since these should only be in
    /srv/orbit/data/.
    """
    import warnings
    
    data_dir = get_data_dir()
    
    # Only warn if using default ./data location
    if str(data_dir) == "data" or data_dir == Path("data"):
        path_str = str(path)
        
        # Check for production data directories in repo
        production_dirs = ["data/raw/", "data/curated/", "data/features/", "data/scores/"]
        
        for prod_dir in production_dirs:
            if path_str.startswith(prod_dir):
                warnings.warn(
                    f"\n{'='*70}\n"
                    f"WARNING: Writing production data to repo directory!\n"
                    f"Path: {path}\n\n"
                    f"This directory should be in /srv/orbit/data/, not ./data/\n"
                    f"./data/ should ONLY contain sample data and production models.\n\n"
                    f"To fix: Add to your .env file (automatically loaded):\n"
                    f"  ORBIT_DATA_DIR=/srv/orbit/data\n"
                    f"Or export manually:\n"
                    f"  export ORBIT_DATA_DIR=/srv/orbit/data\n"
                    f"{'='*70}",
                    UserWarning,
                    stacklevel=3
                )
                break


def read_parquet(
    path: Union[str, Path],
    columns: Optional[list[str]] = None,
    filters: Optional[list] = None,
) -> pd.DataFrame:
    """Read Parquet file(s) with optional column selection and filtering.

    Args:
        path: File or directory path (relative paths resolved from ORBIT_DATA_DIR)
        columns: Optional list of columns to read (None = all)
        filters: Optional pyarrow filters for partition pruning

    Returns:
        DataFrame with loaded data

    Examples:
        >>> # For production (with ORBIT_DATA_DIR=/srv/orbit/data):
        >>> df = read_parquet("raw/prices/2024/11/05/SPY.parquet")  # Reads from /srv/orbit/data/raw/...
        >>> df = read_parquet("curated/prices/", filters=[("date", ">=", "2024-11-01")])
        >>> 
        >>> # For sample/testing (without ORBIT_DATA_DIR or with fixtures):
        >>> df = load_fixtures("prices")  # Always reads from ./data/sample/
    """
    path = Path(path)

    # If path is relative, resolve from ORBIT_DATA_DIR
    if not path.is_absolute():
        path = get_data_dir() / path

    # Read using pandas (handles both files and directories with partitions)
    df = pd.read_parquet(
        path,
        columns=columns,
        filters=filters,
        engine=PARQUET_ENGINE,
    )

    return df


def write_parquet(
    df: pd.DataFrame,
    path: Union[str, Path],
    compression: str = "snappy",
    overwrite: bool = True,
) -> None:
    """Write DataFrame to Parquet with consistent compression and options.

    Args:
        df: DataFrame to write
        path: Output file path (relative paths resolved from ORBIT_DATA_DIR)
        compression: Compression codec (default: snappy)
        overwrite: Whether to overwrite existing file (default: True)

    Examples:
        >>> # For production (with ORBIT_DATA_DIR=/srv/orbit/data):
        >>> write_parquet(df, "raw/prices/2024/11/05/SPY.parquet")  # Writes to /srv/orbit/data/raw/...
        >>> write_parquet(df, "features/2024/11/05/features_daily.parquet")
        >>> 
        >>> # WARNING: Do NOT write production data without ORBIT_DATA_DIR set!
        >>> # Without it, data goes to ./data which should ONLY have sample data.
    """
    path = Path(path)

    # If path is relative, resolve from ORBIT_DATA_DIR
    if not path.is_absolute():
        path = get_data_dir() / path

    # Create parent directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Check for overwrite protection
    if path.exists() and not overwrite:
        raise FileExistsError(f"File exists and overwrite=False: {path}")

    # Warn if writing production data to repo directory
    _warn_if_writing_to_repo(path)

    # Write using pandas with available parquet engine
    df.to_parquet(
        path,
        engine=PARQUET_ENGINE,
        compression=compression,
        index=False,  # Don't write index as a column
    )


def validate_schema(
    df: pd.DataFrame,
    required_columns: list[str],
    nullable_columns: Optional[set[str]] = None,
) -> list[str]:
    """Validate DataFrame against expected schema.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        nullable_columns: Set of columns that can have nulls (default: all columns nullable)

    Returns:
        List of validation errors (empty if valid)

    Examples:
        >>> errors = validate_schema(df, ["date", "symbol", "close"])
        >>> if errors:
        ...     print(f"Validation failed: {errors}")
    """
    errors = []
    nullable_columns = nullable_columns or set()

    # Check for missing columns
    missing = set(required_columns) - set(df.columns)
    if missing:
        errors.append(f"Missing required columns: {sorted(missing)}")

    # Check for nulls in non-nullable columns
    non_nullable = set(required_columns) - nullable_columns
    for col in non_nullable:
        if col in df.columns and df[col].isna().any():
            null_count = df[col].isna().sum()
            errors.append(f"Column '{col}' has {null_count} null values (not nullable)")

    return errors


def load_fixtures(fixture_name: str) -> pd.DataFrame:
    """Load test fixture data from data/sample/ directory.

    Note: Fixtures ALWAYS load from ./data/sample/ regardless of ORBIT_DATA_DIR.
    This ensures tests work consistently without external dependencies.

    Args:
        fixture_name: Name of fixture (e.g., "prices", "news", "social")

    Returns:
        DataFrame with sample data

    Examples:
        >>> df_prices = load_fixtures("prices")
        >>> df_news = load_fixtures("news")
    """
    # Always use local data/sample/ directory, ignoring ORBIT_DATA_DIR
    # This ensures CI/tests work consistently
    local_data_dir = Path("data")

    # Map fixture name to sample file path
    fixture_paths = {
        "prices": "sample/prices/2024/11/05/SPY.parquet",
        "news": "sample/news/2024/11/05/alpaca.parquet",
        "social": "sample/social/2024/11/05/reddit.parquet",
        "features": "sample/features/2024/11/05/features_daily.parquet",
    }

    if fixture_name not in fixture_paths:
        raise ValueError(
            f"Unknown fixture: {fixture_name}. "
            f"Available: {list(fixture_paths.keys())}"
        )

    fixture_path = local_data_dir / fixture_paths[fixture_name]

    if not fixture_path.exists():
        raise FileNotFoundError(
            f"Fixture not found: {fixture_path}. "
            f"Run sample data generation first: python src/orbit/utils/generate_samples.py"
        )

    # Read directly using absolute path
    return pd.read_parquet(fixture_path, engine=PARQUET_ENGINE)
