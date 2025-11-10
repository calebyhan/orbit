"""ORBIT I/O utilities for Parquet data.

Lightweight wrappers around pandas/pyarrow for reading/writing Parquet files
with schema validation and ORBIT_DATA_DIR support.
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


def get_data_dir() -> Path:
    """Get the configured data directory from ORBIT_DATA_DIR env var.

    Returns:
        Path to data directory (defaults to ./data if not set)
    """
    data_dir = os.getenv("ORBIT_DATA_DIR", "data")
    return Path(data_dir)


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
        >>> df = read_parquet("prices/2024/11/05/SPY.parquet")
        >>> df = read_parquet("prices/", filters=[("date", ">=", "2024-11-01")])
        >>> df = read_parquet("prices/2024/11/05/SPY.parquet", columns=["date", "close"])
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
        >>> write_parquet(df, "prices/2024/11/05/SPY.parquet")
        >>> write_parquet(df, "features/2024/11/05/features_daily.parquet")
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
