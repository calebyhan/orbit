"""Unit tests for orbit.io module.

Tests use the existing sample data in data/sample/ for fixture tests,
and temporary directories for read/write tests.
"""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from orbit import io


class TestGetDataDir:
    """Tests for get_data_dir function."""

    def test_default_data_dir(self, monkeypatch):
        """Test default data directory when ORBIT_DATA_DIR is not set."""
        monkeypatch.delenv("ORBIT_DATA_DIR", raising=False)
        data_dir = io.get_data_dir()
        assert data_dir == Path("data")

    def test_custom_data_dir(self, monkeypatch):
        """Test custom data directory from ORBIT_DATA_DIR env var."""
        custom_path = "/srv/orbit/data"
        monkeypatch.setenv("ORBIT_DATA_DIR", custom_path)
        data_dir = io.get_data_dir()
        assert data_dir == Path(custom_path)

    def test_data_dir_respects_env_changes(self, monkeypatch):
        """Test that get_data_dir picks up environment changes."""
        monkeypatch.setenv("ORBIT_DATA_DIR", "/path/one")
        assert io.get_data_dir() == Path("/path/one")

        monkeypatch.setenv("ORBIT_DATA_DIR", "/path/two")
        assert io.get_data_dir() == Path("/path/two")


class TestReadWriteParquet:
    """Tests for read_parquet and write_parquet functions."""

    def test_write_and_read_parquet(self, tmp_path, monkeypatch):
        """Test writing and reading a Parquet file."""
        # Set temp directory as data dir
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        # Create sample data
        df = pd.DataFrame({
            "date": ["2024-11-05", "2024-11-06"],
            "symbol": ["SPY", "SPY"],
            "close": [451.35, 452.10],
            "volume": [85000000, 87000000]
        })

        # Write parquet
        rel_path = "test/sample.parquet"
        io.write_parquet(df, rel_path)

        # Verify file was created
        full_path = tmp_path / rel_path
        assert full_path.exists()

        # Read back
        df_read = io.read_parquet(rel_path)

        # Verify data matches
        pd.testing.assert_frame_equal(df, df_read)

    def test_write_creates_parent_dirs(self, tmp_path, monkeypatch):
        """Test that write_parquet creates parent directories."""
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        rel_path = "nested/deep/path/file.parquet"

        io.write_parquet(df, rel_path)

        full_path = tmp_path / rel_path
        assert full_path.exists()
        assert full_path.parent.exists()

    def test_write_overwrite_protection(self, tmp_path, monkeypatch):
        """Test that overwrite=False prevents overwriting existing files."""
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        df = pd.DataFrame({"a": [1, 2]})
        rel_path = "test/file.parquet"

        # Write first time
        io.write_parquet(df, rel_path)

        # Try to write again with overwrite=False
        with pytest.raises(FileExistsError):
            io.write_parquet(df, rel_path, overwrite=False)

    def test_read_parquet_with_column_selection(self, tmp_path, monkeypatch):
        """Test reading only specific columns."""
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "symbol": ["SPY"],
            "open": [450.0],
            "close": [451.35],
            "volume": [85000000]
        })

        rel_path = "test/prices.parquet"
        io.write_parquet(df, rel_path)

        # Read only specific columns
        df_read = io.read_parquet(rel_path, columns=["date", "close"])

        assert list(df_read.columns) == ["date", "close"]
        assert len(df_read) == 1

    def test_read_write_with_absolute_path(self, tmp_path):
        """Test that absolute paths work without ORBIT_DATA_DIR prepending."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        abs_path = tmp_path / "absolute_test.parquet"

        # Write with absolute path
        io.write_parquet(df, abs_path)
        assert abs_path.exists()

        # Read with absolute path
        df_read = io.read_parquet(abs_path)
        pd.testing.assert_frame_equal(df, df_read)


class TestValidateSchema:
    """Tests for validate_schema function."""

    def test_valid_schema(self):
        """Test validation passes for correct schema."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "symbol": ["SPY"],
            "close": [451.35]
        })

        errors = io.validate_schema(df, ["date", "symbol", "close"])
        assert errors == []

    def test_missing_columns(self):
        """Test validation fails when required columns are missing."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "close": [451.35]
        })

        errors = io.validate_schema(df, ["date", "symbol", "close"])
        assert len(errors) == 1
        assert "symbol" in errors[0]

    def test_null_values_in_non_nullable_columns(self):
        """Test validation fails for nulls in non-nullable columns."""
        df = pd.DataFrame({
            "date": ["2024-11-05", None],
            "symbol": ["SPY", "VOO"],
            "close": [451.35, 410.20]
        })

        # date is not nullable
        errors = io.validate_schema(
            df,
            required_columns=["date", "symbol", "close"],
            nullable_columns={"symbol", "close"}
        )

        assert len(errors) == 1
        assert "date" in errors[0]
        assert "null" in errors[0].lower()

    def test_nulls_allowed_in_nullable_columns(self):
        """Test validation passes when nulls are in nullable columns."""
        df = pd.DataFrame({
            "date": ["2024-11-05"],
            "symbol": ["SPY"],
            "adjusted_close": [None]  # nullable
        })

        errors = io.validate_schema(
            df,
            required_columns=["date", "symbol", "adjusted_close"],
            nullable_columns={"adjusted_close"}
        )

        assert errors == []


class TestLoadFixtures:
    """Tests for load_fixtures function using actual sample data.

    These tests use the committed sample data in data/sample/ which is
    version controlled and always available (no external APIs needed).
    """

    def test_load_prices_fixture(self):
        """Test loading prices fixture from data/sample/."""
        df = io.load_fixtures("prices")

        # Verify basic structure matches schema
        required_cols = ["date", "symbol", "close", "open", "high", "low", "volume", "source"]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"

        # Verify we got SPY data
        assert df["symbol"].iloc[0] == "SPY"
        assert len(df) == 1  # Single row for SPY

    def test_load_news_fixture(self):
        """Test loading news fixture from data/sample/."""
        df = io.load_fixtures("news")

        # Verify schema compliance
        required_cols = ["id", "headline", "sentiment_gemini", "published_at", "source"]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"

        # Verify we have multiple news items
        assert len(df) >= 3, "Should have at least 3 sample news items"

        # Verify sentiment is in valid range
        assert df["sentiment_gemini"].between(-1, 1).all()

    def test_load_social_fixture(self):
        """Test loading social fixture from data/sample/."""
        df = io.load_fixtures("social")

        # Verify schema compliance
        required_cols = ["id", "title", "subreddit", "sentiment_gemini", "author_karma"]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"

        # Verify we have multiple social posts
        assert len(df) >= 3, "Should have at least 3 sample social posts"

        # Verify subreddit is one of expected values
        valid_subreddits = ["wallstreetbets", "investing", "stocks"]
        assert df["subreddit"].isin(valid_subreddits).all()

    def test_load_features_fixture(self):
        """Test loading features fixture from data/sample/."""
        df = io.load_fixtures("features")

        # Verify schema compliance
        required_cols = [
            "date", "symbol",
            "momentum_5d", "momentum_20d",
            "news_count_1d", "news_sentiment_mean",
            "post_count_1d", "social_sentiment_mean",
            "data_completeness"
        ]
        for col in required_cols:
            assert col in df.columns, f"Missing required column: {col}"

        # Verify single row for daily features
        assert len(df) == 1

        # Verify data completeness is valid
        assert 0 <= df["data_completeness"].iloc[0] <= 1

    def test_invalid_fixture_name(self):
        """Test that invalid fixture names raise ValueError."""
        with pytest.raises(ValueError, match="Unknown fixture"):
            io.load_fixtures("invalid_fixture_name")

    def test_fixtures_independent_of_orbit_data_dir(self, monkeypatch):
        """Test that fixtures always load from data/sample/ regardless of ORBIT_DATA_DIR."""
        # Set ORBIT_DATA_DIR to a different location
        monkeypatch.setenv("ORBIT_DATA_DIR", "/srv/orbit/data")

        # Fixtures should still load from local data/sample/
        df_prices = io.load_fixtures("prices")
        assert "symbol" in df_prices.columns
        assert len(df_prices) >= 1


class TestIntegration:
    """Integration tests using sample data for realistic scenarios."""

    def test_join_prices_and_features(self):
        """Test joining price and feature data from fixtures."""
        df_prices = io.load_fixtures("prices")
        df_features = io.load_fixtures("features")

        # Join on date and symbol
        merged = pd.merge(
            df_features,
            df_prices,
            on=["date", "symbol"],
            how="left"
        )

        # Verify join worked
        assert "close" in merged.columns
        assert "momentum_5d" in merged.columns
        assert len(merged) == len(df_features)

        # Verify no NaNs from failed join
        assert merged["close"].notna().all()

    def test_aggregate_news_by_date(self):
        """Test aggregating news data by date."""
        df_news = io.load_fixtures("news")

        # Aggregate sentiment by published date
        df_news["pub_date"] = pd.to_datetime(df_news["published_at"]).dt.date.astype(str)

        daily_sent = df_news.groupby("pub_date").agg({
            "sentiment_gemini": "mean",
            "id": "count"
        }).rename(columns={"id": "news_count"})

        assert "sentiment_gemini" in daily_sent.columns
        assert "news_count" in daily_sent.columns
        assert len(daily_sent) >= 1

    def test_compute_weighted_social_sentiment(self):
        """Test computing karma-weighted sentiment from social data."""
        df_social = io.load_fixtures("social")

        # Karma-weighted sentiment (capped at 10k)
        df_social["karma_capped"] = df_social["author_karma"].clip(upper=10000)
        df_social["weight"] = df_social["karma_capped"] + 1  # Avoid log(0)

        weighted_sent = (
            df_social["sentiment_gemini"] * df_social["weight"]
        ).sum() / df_social["weight"].sum()

        # Should be a valid sentiment score
        assert -1 <= weighted_sent <= 1

    def test_production_vs_sample_data_isolation(self, tmp_path, monkeypatch):
        """Test that production data (ORBIT_DATA_DIR) and sample data are isolated."""
        # Setup: Write production data to tmp_path
        monkeypatch.setenv("ORBIT_DATA_DIR", str(tmp_path))

        prod_df = pd.DataFrame({
            "date": ["2024-11-06"],
            "symbol": ["SPY"],
            "value": [999.99]
        })
        io.write_parquet(prod_df, "raw/prices/2024/11/06/SPY.parquet")

        # Verify production data was written
        prod_path = tmp_path / "raw/prices/2024/11/06/SPY.parquet"
        assert prod_path.exists()

        # Fixtures should still load from local data/sample/
        sample_df = io.load_fixtures("prices")

        # Sample data should be different from production data
        assert sample_df["date"].iloc[0] == "2024-11-05"  # Sample date
        assert "value" not in sample_df.columns  # Different schema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
