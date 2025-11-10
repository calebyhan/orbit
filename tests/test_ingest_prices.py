"""Unit tests for orbit.ingest.prices module.

Tests Stooq price ingestion with mocked HTTP responses and real data validation.
"""

import io
from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from orbit.ingest import prices


class TestFetchStooqCSV:
    """Tests for fetch_stooq_csv function."""

    @patch("orbit.ingest.prices.requests.get")
    def test_fetch_success(self, mock_get):
        """Test successful CSV fetch from Stooq."""
        # Mock response
        mock_response = Mock()
        mock_response.content = b"Date,Open,High,Low,Close,Volume\n2024-11-05,450.0,452.0,449.0,451.0,85000000"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Fetch
        result = prices.fetch_stooq_csv("SPY.US", polite_delay_sec=0)

        # Verify
        assert result == mock_response.content
        mock_get.assert_called_once()
        assert "s=spy.us" in mock_get.call_args[0][0]

    @patch("orbit.ingest.prices.requests.get")
    def test_fetch_with_caret_symbol(self, mock_get):
        """Test URL encoding for symbols with special chars (^SPX)."""
        mock_response = Mock()
        mock_response.content = b"Date,Open,High,Low,Close,Volume\n"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        prices.fetch_stooq_csv("^SPX", polite_delay_sec=0)

        # Verify URL encoding
        called_url = mock_get.call_args[0][0]
        assert "%5espx" in called_url.lower() or "^spx" in called_url.lower()

    @patch("orbit.ingest.prices.requests.get")
    @patch("orbit.ingest.prices.time.sleep")
    def test_fetch_retry_on_error(self, mock_sleep, mock_get):
        """Test retry logic with exponential backoff."""
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            Mock(content=b"success", raise_for_status=Mock()),
        ]

        result = prices.fetch_stooq_csv("SPY.US", polite_delay_sec=0, retries=3)

        assert result == b"success"
        assert mock_get.call_count == 3
        # Verify exponential backoff (2^0=1, 2^1=2 seconds)
        assert mock_sleep.call_count == 2

    @patch("orbit.ingest.prices.requests.get")
    def test_fetch_all_retries_exhausted(self, mock_get):
        """Test that exception is raised when all retries fail."""
        mock_get.side_effect = Exception("Persistent network error")

        with pytest.raises(Exception, match="Persistent network error"):
            prices.fetch_stooq_csv("SPY.US", polite_delay_sec=0, retries=2)


class TestNormalizeStooqCSV:
    """Tests for normalize_stooq_csv function."""

    def test_normalize_basic(self):
        """Test basic CSV normalization."""
        csv_data = b"""Date,Open,High,Low,Close,Volume
2024-11-05,450.12,452.87,449.23,451.64,85234567
2024-11-06,451.70,453.10,450.90,452.35,87123456"""

        df = prices.normalize_stooq_csv(csv_data, symbol="SPY.US", run_id="test123")

        # Check schema
        assert "date" in df.columns
        assert "symbol" in df.columns
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns
        assert "source" in df.columns
        assert "run_id" in df.columns
        assert "ingested_at" in df.columns

        # Check values
        assert len(df) == 2
        assert df["symbol"].iloc[0] == "SPY.US"
        assert df["source"].iloc[0] == "stooq"
        assert df["run_id"].iloc[0] == "test123"
        assert df["close"].iloc[0] == 451.64

    def test_normalize_lowercase_columns(self):
        """Test that column names are lowercased."""
        csv_data = b"""Date,Open,High,Low,Close,Volume
2024-11-05,450.0,452.0,449.0,451.0,85000000"""

        df = prices.normalize_stooq_csv(csv_data, symbol="SPY.US", run_id="test")

        # All columns should be lowercase
        for col in df.columns:
            assert col == col.lower()

    def test_normalize_missing_volume(self):
        """Test handling of CSV without volume column (e.g., index data)."""
        csv_data = b"""Date,Open,High,Low,Close
2024-11-05,4500.0,4520.0,4490.0,4510.0"""

        df = prices.normalize_stooq_csv(csv_data, symbol="^SPX", run_id="test")

        # Volume should be NA
        assert "volume" in df.columns
        assert pd.isna(df["volume"].iloc[0])

    def test_normalize_invalid_prices(self):
        """Test handling of non-numeric price values."""
        csv_data = b"""Date,Open,High,Low,Close,Volume
2024-11-05,N/A,452.0,449.0,451.0,85000000"""

        df = prices.normalize_stooq_csv(csv_data, symbol="SPY.US", run_id="test")

        # Invalid values should become NaN
        assert pd.isna(df["open"].iloc[0])
        assert df["close"].iloc[0] == 451.0


class TestValidatePricesDF:
    """Tests for validate_prices_df function."""

    def test_validate_valid_data(self):
        """Test validation passes for correct data."""
        df = pd.DataFrame({
            "date": ["2024-11-05", "2024-11-06"],
            "symbol": ["SPY.US", "SPY.US"],
            "open": [450.0, 451.0],
            "high": [452.0, 453.0],
            "low": [449.0, 450.0],
            "close": [451.0, 452.0],
            "volume": [85000000, 87000000],
        })

        errors = prices.validate_prices_df(df)
        assert errors == []

    def test_validate_empty_dataframe(self):
        """Test validation catches empty DataFrame."""
        df = pd.DataFrame()
        errors = prices.validate_prices_df(df)
        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    def test_validate_missing_columns(self):
        """Test validation catches missing required columns."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "close": [451.0],
        })

        errors = prices.validate_prices_df(df)
        assert len(errors) > 0
        assert "missing" in errors[0].lower()

    def test_validate_duplicate_dates(self):
        """Test validation catches duplicate dates."""
        df = pd.DataFrame({
            "date": ["2024-11-05", "2024-11-05"],  # Duplicate
            "symbol": ["SPY.US", "SPY.US"],
            "open": [450.0, 450.0],
            "high": [452.0, 452.0],
            "low": [449.0, 449.0],
            "close": [451.0, 451.0],
        })

        errors = prices.validate_prices_df(df)
        assert any("duplicate" in err.lower() for err in errors)

    def test_validate_non_positive_prices(self):
        """Test validation catches non-positive prices."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "symbol": ["SPY.US"],
            "open": [450.0],
            "high": [452.0],
            "low": [0.0],  # Invalid
            "close": [451.0],
        })

        errors = prices.validate_prices_df(df)
        assert any("non-positive" in err.lower() for err in errors)

    def test_validate_high_low_constraint(self):
        """Test validation catches high < low."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "symbol": ["SPY.US"],
            "open": [450.0],
            "high": [449.0],  # Lower than low
            "low": [452.0],
            "close": [451.0],
        })

        errors = prices.validate_prices_df(df)
        assert any("high < low" in err.lower() for err in errors)

    def test_validate_high_open_constraint(self):
        """Test validation catches high < open."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "symbol": ["SPY.US"],
            "open": [455.0],
            "high": [452.0],  # Lower than open
            "low": [449.0],
            "close": [451.0],
        })

        errors = prices.validate_prices_df(df)
        assert any("high < open" in err.lower() for err in errors)

    def test_validate_negative_volume(self):
        """Test validation catches negative volume."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "symbol": ["SPY.US"],
            "open": [450.0],
            "high": [452.0],
            "low": [449.0],
            "close": [451.0],
            "volume": [-1000],  # Negative
        })

        errors = prices.validate_prices_df(df)
        assert any("negative volume" in err.lower() for err in errors)


class TestIngestPrices:
    """Integration tests for full ingestion pipeline."""

    @patch("orbit.ingest.prices.fetch_stooq_csv")
    def test_ingest_single_symbol(self, mock_fetch, tmp_path, monkeypatch):
        """Test ingesting a single symbol end-to-end."""
        # Setup
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        # Mock CSV response
        csv_data = b"""Date,Open,High,Low,Close,Volume
2024-11-05,450.12,452.87,449.23,451.64,85234567
2024-11-06,451.70,453.10,450.90,452.35,87123456"""
        mock_fetch.return_value = csv_data

        # Run ingestion
        results = prices.ingest_prices(
            symbols=["SPY.US"],
            polite_delay_sec=0,
            run_id="test_run",
        )

        # Verify results
        assert "SPY.US" in results
        df = results["SPY.US"]
        assert len(df) == 2
        assert df["symbol"].iloc[0] == "SPY.US"
        assert df["close"].iloc[0] == 451.64

        # Verify files were written
        raw_files = list(tmp_path.glob("raw/prices/**/*.parquet"))
        curated_files = list(tmp_path.glob("curated/prices/**/*.parquet"))
        assert len(raw_files) > 0
        assert len(curated_files) > 0

    @patch("orbit.ingest.prices.fetch_stooq_csv")
    def test_ingest_multiple_symbols(self, mock_fetch, tmp_path, monkeypatch):
        """Test ingesting multiple symbols."""
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        # Mock different CSV for each symbol
        def mock_csv_by_symbol(symbol, **kwargs):
            base_csv = b"""Date,Open,High,Low,Close,Volume
2024-11-05,450.0,452.0,449.0,451.0,85000000"""
            return base_csv

        mock_fetch.side_effect = mock_csv_by_symbol

        # Run ingestion for multiple symbols
        results = prices.ingest_prices(
            symbols=["SPY.US", "VOO.US"],
            polite_delay_sec=0,
        )

        # Verify both symbols ingested
        assert len(results) == 2
        assert "SPY.US" in results
        assert "VOO.US" in results

    @patch("orbit.ingest.prices.fetch_stooq_csv")
    def test_ingest_handles_invalid_data(self, mock_fetch, tmp_path, monkeypatch):
        """Test that invalid data is skipped with error message."""
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        # Mock CSV with invalid data (high < low)
        invalid_csv = b"""Date,Open,High,Low,Close,Volume
2024-11-05,450.0,449.0,452.0,451.0,85000000"""
        mock_fetch.return_value = invalid_csv

        # Run ingestion
        results = prices.ingest_prices(
            symbols=["BAD.SYMBOL"],
            polite_delay_sec=0,
        )

        # Invalid data should be skipped
        assert len(results) == 0

    @patch("orbit.ingest.prices.fetch_stooq_csv")
    def test_ingest_without_writing(self, mock_fetch):
        """Test ingestion without writing to disk."""
        csv_data = b"""Date,Open,High,Low,Close,Volume
2024-11-05,450.0,452.0,449.0,451.0,85000000"""
        mock_fetch.return_value = csv_data

        # Run without writing
        results = prices.ingest_prices(
            symbols=["SPY.US"],
            polite_delay_sec=0,
            write_raw=False,
            write_curated=False,
        )

        # Should still return results
        assert "SPY.US" in results
        assert len(results["SPY.US"]) == 1

    @patch("orbit.ingest.prices.fetch_stooq_csv")
    def test_ingest_default_symbols(self, mock_fetch, tmp_path, monkeypatch):
        """Test that default symbols are used when none specified."""
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        csv_data = b"""Date,Open,High,Low,Close,Volume
2024-11-05,450.0,452.0,449.0,451.0,85000000"""
        mock_fetch.return_value = csv_data

        # Run without specifying symbols
        results = prices.ingest_prices(polite_delay_sec=0)

        # Should use default symbols: SPY.US, VOO.US, ^SPX
        assert len(results) == 3
        assert "SPY.US" in results
        assert "VOO.US" in results
        assert "^SPX" in results


class TestIntegration:
    """End-to-end integration tests."""

    @patch("orbit.ingest.prices.fetch_stooq_csv")
    def test_full_pipeline_realistic_data(self, mock_fetch, tmp_path, monkeypatch):
        """Test full pipeline with realistic multi-day data."""
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        # Realistic multi-day CSV
        csv_data = b"""Date,Open,High,Low,Close,Volume
2024-11-01,448.25,450.80,447.90,450.12,82000000
2024-11-04,450.50,452.30,449.75,451.85,78500000
2024-11-05,451.90,453.40,451.20,452.95,85200000"""
        mock_fetch.return_value = csv_data

        # Run full ingestion
        results = prices.ingest_prices(
            symbols=["SPY.US"],
            polite_delay_sec=0,
            run_id="integration_test",
        )

        # Verify data quality
        df = results["SPY.US"]
        assert len(df) == 3
        assert df["date"].is_monotonic_increasing or list(df["date"]) == sorted(df["date"])
        assert (df["close"] > 0).all()
        assert (df["high"] >= df["low"]).all()
        assert (df["volume"] > 0).all()

        # Verify metadata
        assert (df["symbol"] == "SPY.US").all()
        assert (df["source"] == "stooq").all()
        assert (df["run_id"] == "integration_test").all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
