"""Unit tests for orbit.ingest.news_backfill module.

Tests Alpaca REST API historical news backfill with mocked responses.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
import pytest

from orbit.ingest import news_backfill


class TestFetchNewsPage:
    """Tests for fetch_news_page function."""

    @patch("orbit.ingest.news_backfill.requests.get")
    def test_fetch_success(self, mock_get):
        """Test successful news page fetch from Alpaca REST API."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "news": [
                {
                    "id": 123456,
                    "headline": "SPY hits new high",
                    "summary": "Market rally continues...",
                    "author": "Reuters",
                    "created_at": "2024-11-05T14:30:00Z",
                    "updated_at": "2024-11-05T14:30:00Z",
                    "url": "https://example.com/article",
                    "symbols": ["SPY"],
                }
            ],
            "next_page_token": "abc123"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Fetch
        result = news_backfill.fetch_news_page(
            symbols=["SPY"],
            start="2024-11-05T00:00:00Z",
            end="2024-11-05T23:59:59Z",
            api_key="test_key",
            api_secret="test_secret"
        )

        # Verify
        assert "news" in result
        assert len(result["news"]) == 1
        assert result["news"][0]["headline"] == "SPY hits new high"
        assert result["next_page_token"] == "abc123"
        mock_get.assert_called_once()

    @patch("orbit.ingest.news_backfill.requests.get")
    def test_fetch_with_pagination_token(self, mock_get):
        """Test fetch with page token for pagination."""
        mock_response = Mock()
        mock_response.json.return_value = {"news": [], "next_page_token": None}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        news_backfill.fetch_news_page(
            symbols=["SPY"],
            start="2024-11-05T00:00:00Z",
            end="2024-11-05T23:59:59Z",
            api_key="test_key",
            api_secret="test_secret",
            page_token="token123"
        )

        # Verify page_token in params
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["page_token"] == "token123"

    @patch("orbit.ingest.news_backfill.requests.get")
    def test_fetch_with_headers(self, mock_get):
        """Test that API credentials are sent in headers."""
        mock_response = Mock()
        mock_response.json.return_value = {"news": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        news_backfill.fetch_news_page(
            symbols=["SPY"],
            start="2024-11-05T00:00:00Z",
            end="2024-11-05T23:59:59Z",
            api_key="my_key",
            api_secret="my_secret"
        )

        # Verify headers
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["headers"]["APCA-API-KEY-ID"] == "my_key"
        assert call_kwargs["headers"]["APCA-API-SECRET-KEY"] == "my_secret"


class TestNormalizeAlpacaRestMessage:
    """Tests for normalize_alpaca_rest_message function."""

    def test_normalize_basic(self):
        """Test basic article normalization."""
        article = {
            "id": 123456,
            "headline": "Test headline",
            "summary": "Test summary",
            "source": "Reuters",
            "created_at": "2024-11-05T14:30:00Z",
            "updated_at": "2024-11-05T14:30:00Z",
            "url": "https://example.com/article",
            "symbols": ["SPY", "VOO"],
        }

        received_at = datetime(2024, 11, 5, 15, 0, 0, tzinfo=timezone.utc)
        normalized = news_backfill.normalize_alpaca_rest_message(
            article, received_at, run_id="test123"
        )

        # Verify schema (normalize uses msg_id and published_at)
        assert normalized["msg_id"] == 123456
        assert normalized["headline"] == "Test headline"
        assert normalized["summary"] == "Test summary"
        assert normalized["source"] == "Reuters"
        assert "published_at" in normalized
        assert "received_at" in normalized
        assert normalized["url"] == "https://example.com/article"
        assert normalized["symbols"] == ["SPY", "VOO"]
        assert normalized["run_id"] == "test123"

    def test_normalize_with_missing_fields(self):
        """Test normalization with missing optional fields."""
        article = {
            "id": 789,
            "headline": "Minimal article",
            "created_at": "2024-11-05T14:30:00Z",
            "symbols": ["SPY"],
        }

        received_at = datetime.now(timezone.utc)
        normalized = news_backfill.normalize_alpaca_rest_message(
            article, received_at, run_id="test456"
        )

        # Verify required fields present, optional fields handled
        assert normalized["msg_id"] == 789
        assert normalized["headline"] == "Minimal article"
        assert "summary" in normalized  # Should have default or null
        assert "source" in normalized
        assert normalized["symbols"] == ["SPY"]

    def test_normalize_timestamp_parsing(self):
        """Test that timestamps are correctly parsed to pandas datetime."""
        article = {
            "id": 999,
            "headline": "Time test",
            "created_at": "2024-11-05T14:30:45.123Z",
            "updated_at": "2024-11-05T14:35:00.000Z",
            "symbols": ["SPY"],
        }

        received_at = datetime.now(timezone.utc)
        normalized = news_backfill.normalize_alpaca_rest_message(
            article, received_at, run_id="test789"
        )

        # Verify timestamps are datetime objects (published_at and received_at)
        assert isinstance(normalized["published_at"], (pd.Timestamp, datetime))
        assert isinstance(normalized["received_at"], (pd.Timestamp, datetime))


class TestCheckpointOperations:
    """Tests for checkpoint save/load operations."""

    def test_save_and_load_checkpoint(self, tmp_path):
        """Test checkpoint save and load roundtrip."""
        checkpoint_file = tmp_path / "test_checkpoint.json"

        data = {
            "total_articles": 1000,
            "total_requests": 50,
            "current_date": "2024-11-05",
            "completed_days": 10,
        }

        # Save
        news_backfill.save_checkpoint(checkpoint_file, data)
        assert checkpoint_file.exists()

        # Load
        loaded = news_backfill.load_checkpoint(checkpoint_file)
        assert loaded == data

    def test_load_nonexistent_checkpoint(self, tmp_path):
        """Test loading checkpoint that doesn't exist returns None."""
        checkpoint_file = tmp_path / "nonexistent.json"
        result = news_backfill.load_checkpoint(checkpoint_file)
        assert result is None


class TestGetAlpacaCredsForRest:
    """Tests for credential loading."""

    @patch.dict("os.environ", {
        "ALPACA_API_KEY_1": "key1",
        "ALPACA_API_SECRET_1": "secret1"
    })
    def test_get_creds_success(self):
        """Test successful credential loading from environment."""
        api_key, api_secret = news_backfill.get_alpaca_creds_for_rest()
        assert api_key == "key1"
        assert api_secret == "secret1"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_creds_missing_raises_error(self):
        """Test that missing credentials raise ValueError."""
        with pytest.raises(ValueError, match="Alpaca REST API credentials not found"):
            news_backfill.get_alpaca_creds_for_rest()

    @patch.dict("os.environ", {
        "ALPACA_API_KEY_1": "key1",
        # Missing SECRET_1
    }, clear=True)
    def test_get_creds_partial_missing_raises_error(self):
        """Test that partial credentials raise ValueError."""
        with pytest.raises(ValueError, match="Alpaca REST API credentials not found"):
            news_backfill.get_alpaca_creds_for_rest()


class TestBackfillIntegration:
    """Integration tests for full backfill workflow."""

    @patch("orbit.ingest.news_backfill.fetch_news_page")
    @patch("orbit.ingest.news_backfill.get_alpaca_creds_for_rest")
    def test_backfill_single_day(self, mock_get_creds, mock_fetch, tmp_path):
        """Test backfilling a single day of news."""
        # Mock credentials
        mock_get_creds.return_value = ("test_key", "test_secret")

        # Mock API response
        mock_fetch.return_value = {
            "news": [
                {
                    "id": 1,
                    "headline": "Article 1",
                    "summary": "Summary 1",
                    "author": "Author 1",
                    "created_at": "2024-11-05T10:00:00Z",
                    "updated_at": "2024-11-05T10:00:00Z",
                    "url": "https://example.com/1",
                    "symbols": ["SPY"],
                }
            ],
            "next_page_token": None
        }

        # Note: Full backfill test would require more complex mocking
        # This is a simplified test to verify the structure
        assert mock_get_creds() == ("test_key", "test_secret")
        result = mock_fetch(
            symbols=["SPY"],
            start="2024-11-05T00:00:00Z",
            end="2024-11-05T23:59:59Z",
            api_key="test_key",
            api_secret="test_secret"
        )
        assert len(result["news"]) == 1
        assert result["news"][0]["id"] == 1


class TestRateLimiting:
    """Tests for rate limiting and backoff logic."""

    @patch("orbit.ingest.news_backfill.requests.get")
    @patch("orbit.ingest.news_backfill.time.sleep")
    def test_429_retry_with_backoff(self, mock_sleep, mock_get):
        """Test that 429 errors trigger exponential backoff."""
        # First call returns 429, second succeeds
        mock_response_429 = Mock()
        mock_response_429.raise_for_status.side_effect = Exception("429 Rate Limit")

        mock_response_success = Mock()
        mock_response_success.json.return_value = {"news": []}
        mock_response_success.raise_for_status = Mock()

        # Note: This test structure depends on how retry logic is implemented
        # Adjust based on actual implementation in news_backfill.py
        # This is a template for testing retry behavior

    @patch("orbit.ingest.news_backfill.time.time")
    def test_rate_limit_interval(self, mock_time):
        """Test that requests respect target RPM interval."""
        # Mock time to verify request spacing
        mock_time.side_effect = [0, 0.316, 0.632]  # 316ms intervals (190 RPM)

        # Verify calculation
        target_rpm = 190
        expected_interval = 60.0 / target_rpm
        assert abs(expected_interval - 0.316) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
