"""ORBIT Preprocessing - Time Alignment & Cutoffs.

Implements point-in-time cutoff enforcement as documented in:
docs/06-preprocessing/time_alignment_cutoffs.md

Ensures all data respects the 15:30 ET daily cutoff to prevent lookahead bias.
"""

import pandas as pd
import pytz
from typing import Tuple, Optional


# Timezone constants
ET = pytz.timezone('America/New_York')
UTC = pytz.UTC

# Daily cutoff time (15:30 ET)
CUTOFF_HOUR = 15
CUTOFF_MINUTE = 30

# Safety lag for training (minutes before cutoff to drop items)
DEFAULT_SAFETY_LAG_MINUTES = 30


def membership_window(date_T: pd.Timestamp) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Compute the membership window for trading day T.

    Window is (T-1 15:30, T 15:30] in ET (right-closed).

    Args:
        date_T: Trading date (timezone-naive or ET-aware)

    Returns:
        Tuple of (start, end) timestamps in ET

    Example:
        >>> membership_window(pd.Timestamp("2024-11-05"))
        (Timestamp('2024-11-04 15:30:00-0500', tz='America/New_York'),
         Timestamp('2024-11-05 15:30:00-0500', tz='America/New_York'))
    """
    # Ensure date_T is a naive datetime (just the date)
    if isinstance(date_T, str):
        date_T = pd.Timestamp(date_T)

    # Strip timezone if present
    if date_T.tz is not None:
        date_T = date_T.tz_localize(None)

    # Build timestamps in ET
    start = ET.localize(
        pd.Timestamp(date_T) - pd.Timedelta(days=1)
    ).replace(hour=CUTOFF_HOUR, minute=CUTOFF_MINUTE, second=0, microsecond=0)

    end = ET.localize(
        pd.Timestamp(date_T)
    ).replace(hour=CUTOFF_HOUR, minute=CUTOFF_MINUTE, second=0, microsecond=0)

    return start, end


def apply_cutoff(
    df: pd.DataFrame,
    ts_column: str,
    date_T: pd.Timestamp,
    safety_lag_minutes: int = DEFAULT_SAFETY_LAG_MINUTES,
    training: bool = True,
) -> pd.DataFrame:
    """Apply 15:30 ET cutoff to filter items for trading day T.

    Filters dataframe to items within the membership window (T-1 15:30, T 15:30] ET.
    Optionally applies safety lag to drop items near the cutoff boundary.

    Args:
        df: Input dataframe
        ts_column: Name of timestamp column (must be timezone-aware)
        date_T: Trading date
        safety_lag_minutes: Minutes before cutoff to drop items (for training)
        training: Whether this is for training (applies safety lag)

    Returns:
        Filtered dataframe with audit fields added

    Raises:
        ValueError: If timestamp column is not timezone-aware
    """
    if df.empty:
        # Return empty dataframe with expected columns
        result = df.copy()
        result['window_start_et'] = pd.NaT
        result['window_end_et'] = pd.NaT
        result['cutoff_applied_at'] = pd.NaT
        return result

    # Validate timestamp column
    if ts_column not in df.columns:
        raise ValueError(f"Timestamp column '{ts_column}' not found in dataframe")

    # Ensure timestamp column is timezone-aware
    if not pd.api.types.is_datetime64tz_dtype(df[ts_column]):
        raise ValueError(
            f"Timestamp column '{ts_column}' must be timezone-aware. "
            f"Use df['{ts_column}'] = pd.to_datetime(df['{ts_column}'], utc=True)"
        )

    # Get membership window
    start, end = membership_window(date_T)

    # Convert timestamps to ET for comparison
    ts_et = df[ts_column].dt.tz_convert(ET)

    # Apply window filter (T-1 15:30, T 15:30] - right-closed
    mask = (ts_et > start) & (ts_et <= end)

    # Apply safety lag if training
    dropped_late_count = 0
    if training and safety_lag_minutes > 0:
        safety_cutoff = end - pd.Timedelta(minutes=safety_lag_minutes)
        late_mask = ts_et > safety_cutoff
        dropped_late_count = late_mask.sum()
        mask &= ~late_mask

    # Filter dataframe
    result = df[mask].copy()

    # Add audit fields
    result['window_start_et'] = start
    result['window_end_et'] = end
    result['cutoff_applied_at'] = pd.Timestamp.now(tz=UTC)
    result['dropped_late_count'] = dropped_late_count

    return result


def validate_cutoff_compliance(
    df: pd.DataFrame,
    ts_column: str,
    date_T: pd.Timestamp,
) -> dict:
    """Validate that all items in dataframe comply with cutoff rules.

    Args:
        df: Dataframe to validate
        ts_column: Name of timestamp column
        date_T: Trading date

    Returns:
        Dict with validation results:
        - compliant: bool
        - total_items: int
        - out_of_window: int
        - window_start_et: Timestamp
        - window_end_et: Timestamp
    """
    if df.empty:
        return {
            "compliant": True,
            "total_items": 0,
            "out_of_window": 0,
            "window_start_et": None,
            "window_end_et": None,
        }

    start, end = membership_window(date_T)
    ts_et = df[ts_column].dt.tz_convert(ET)

    # Check compliance
    in_window = (ts_et > start) & (ts_et <= end)
    out_of_window = (~in_window).sum()

    return {
        "compliant": out_of_window == 0,
        "total_items": len(df),
        "out_of_window": int(out_of_window),
        "window_start_et": start,
        "window_end_et": end,
    }


def slice_date_range(
    df: pd.DataFrame,
    ts_column: str,
    start_date: str,
    end_date: str,
    safety_lag_minutes: int = DEFAULT_SAFETY_LAG_MINUTES,
    training: bool = True,
) -> dict:
    """Slice dataframe into daily buckets with cutoff enforcement.

    Args:
        df: Input dataframe
        ts_column: Name of timestamp column
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        safety_lag_minutes: Safety lag for training
        training: Whether this is for training

    Returns:
        Dict mapping date (as string YYYY-MM-DD) to filtered dataframe
    """
    date_range = pd.date_range(start_date, end_date, freq='D')

    result = {}
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        filtered = apply_cutoff(
            df,
            ts_column,
            date,
            safety_lag_minutes=safety_lag_minutes,
            training=training,
        )
        if not filtered.empty:
            result[date_str] = filtered

    return result
