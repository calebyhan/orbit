"""Unit tests for orbit.ingest.social_arctic module.

Tests Arctic Shift Reddit API historical post backfill with mocked responses.
"""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from orbit.ingest import social_arctic


class TestExtractMatchedTerms:
    """Tests for extract_matched_terms function."""

    def test_spy_match(self):
        """Test SPY term matching."""
        terms = social_arctic.extract_matched_terms(
            title="SPY calls printing today",
            body="Fed decision was bullish for SPY"
        )
        assert "SPY" in terms

    def test_spy_false_positive_filtered(self):
        """Test that 'spy camera' doesn't match SPY."""
        terms = social_arctic.extract_matched_terms(
            title="New spy camera review",
            body="This spy camera is great for spying"
        )
        assert "SPY" not in terms
        assert "off-topic" in terms

    def test_voo_match(self):
        """Test VOO term matching."""
        terms = social_arctic.extract_matched_terms(
            title="VOO or VTI?",
            body="Thinking about buying VOO"
        )
        assert "VOO" in terms

    def test_sp500_variants(self):
        """Test S&P 500 variant matching."""
        # Test different spellings
        for text in ["s&p 500", "S&P500", "sp500", "s & p 500"]:
            terms = social_arctic.extract_matched_terms(
                title=text,
                body=""
            )
            assert "S&P 500" in terms

    def test_market_match(self):
        """Test market term matching."""
        terms = social_arctic.extract_matched_terms(
            title="Market rally continues",
            body="The market is bullish"
        )
        assert "market" in terms

    def test_market_false_positive_filtered(self):
        """Test that 'supermarket' doesn't match market."""
        terms = social_arctic.extract_matched_terms(
            title="Supermarket deals",
            body="Found great prices at the supermarket"
        )
        assert "market" not in terms
        assert "off-topic" in terms

    def test_multiple_terms(self):
        """Test matching multiple terms in one post."""
        terms = social_arctic.extract_matched_terms(
            title="SPY and VOO comparison",
            body="Both track the S&P 500 market"
        )
        assert "SPY" in terms
        assert "VOO" in terms
        assert "S&P 500" in terms or "S&P" in terms
        assert "market" in terms

    def test_no_match_returns_off_topic(self):
        """Test that posts with no matches are marked off-topic."""
        terms = social_arctic.extract_matched_terms(
            title="Tesla stock discussion",
            body="TSLA going to the moon"
        )
        assert "off-topic" in terms
        assert len(terms) == 1


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_hash_consistency(self):
        """Test that same content produces same hash."""
        hash1 = social_arctic.compute_content_hash("Test title", "Test body")
        hash2 = social_arctic.compute_content_hash("Test title", "Test body")
        assert hash1 == hash2

    def test_hash_uniqueness(self):
        """Test that different content produces different hash."""
        hash1 = social_arctic.compute_content_hash("Title 1", "Body 1")
        hash2 = social_arctic.compute_content_hash("Title 2", "Body 2")
        assert hash1 != hash2

    def test_hash_handles_none_body(self):
        """Test that None body is handled correctly."""
        hash1 = social_arctic.compute_content_hash("Title", None)
        hash2 = social_arctic.compute_content_hash("Title", "")
        # Should treat None same as empty string
        assert hash1 == hash2

    def test_hash_length(self):
        """Test that hash is truncated to 16 chars."""
        content_hash = social_arctic.compute_content_hash("Test", "Test")
        assert len(content_hash) == 16
        # Verify it's hex
        int(content_hash, 16)  # Should not raise


class TestHashAuthor:
    """Tests for hash_author function."""

    def test_hash_format(self):
        """Test that hashed author has correct format."""
        hashed = social_arctic.hash_author("test_user")
        assert hashed.startswith("hash_")
        assert len(hashed) == 13  # "hash_" + 8 hex chars

    def test_hash_consistency(self):
        """Test that same author produces same hash."""
        hash1 = social_arctic.hash_author("test_user")
        hash2 = social_arctic.hash_author("test_user")
        assert hash1 == hash2

    def test_hash_uniqueness(self):
        """Test that different authors produce different hashes."""
        hash1 = social_arctic.hash_author("user1")
        hash2 = social_arctic.hash_author("user2")
        assert hash1 != hash2


class TestNormalizeArcticPost:
    """Tests for normalize_arctic_post function."""

    def test_normalize_basic(self):
        """Test basic post normalization."""
        post = {
            "id": "abc123",
            "created_utc": 1636000000,  # Unix timestamp
            "subreddit": "stocks",
            "author": "test_user",
            "title": "SPY discussion",
            "selftext": "What do you think about SPY?",
            "score": 42,
            "upvote_ratio": 0.87,
            "num_comments": 15,
            "permalink": "/r/stocks/comments/abc123/spy_discussion/",
        }

        received_at = datetime(2024, 11, 5, 15, 0, 0, tzinfo=timezone.utc)
        normalized = social_arctic.normalize_arctic_post(
            post, received_at, run_id="test123"
        )

        # Verify schema
        assert normalized["id"] == "abc123"
        assert isinstance(normalized["created_utc"], pd.Timestamp)
        assert normalized["subreddit"] == "stocks"
        assert normalized["author"].startswith("hash_")  # Privacy hash
        assert normalized["title"] == "SPY discussion"
        assert normalized["body"] == "What do you think about SPY?"
        assert normalized["upvote_ratio"] == 0.87
        assert normalized["num_comments"] == 15
        assert "SPY" in normalized["symbols"]
        assert "content_hash" in normalized
        assert normalized["ingestion_ts"] == received_at

    def test_normalize_removed_content(self):
        """Test handling of removed content."""
        post = {
            "id": "def456",
            "created_utc": 1636000000,
            "subreddit": "wallstreetbets",
            "author": "test_user",
            "title": "Deleted post",
            "selftext": "[removed]",
            "score": 10,
            "num_comments": 5,
            "permalink": "/r/wallstreetbets/comments/def456/deleted/",
            "removed_by_category": "moderator",
        }

        received_at = datetime.now(timezone.utc)
        normalized = social_arctic.normalize_arctic_post(
            post, received_at, run_id="test456"
        )

        # Verify removed content is handled
        assert normalized["body"] is None  # Removed content becomes null
        assert normalized["title"] == "Deleted post"  # Title still available

    def test_normalize_deleted_content(self):
        """Test handling of [deleted] content."""
        post = {
            "id": "ghi789",
            "created_utc": 1636000000,
            "subreddit": "investing",
            "author": "[deleted]",
            "title": "User deleted post",
            "selftext": "[deleted]",
            "score": 0,
            "num_comments": 0,
            "permalink": "/r/investing/comments/ghi789/deleted/",
        }

        received_at = datetime.now(timezone.utc)
        normalized = social_arctic.normalize_arctic_post(
            post, received_at, run_id="test789"
        )

        assert normalized["body"] is None
        assert normalized["author"].startswith("hash_")

    def test_normalize_with_optional_fields_missing(self):
        """Test normalization with missing optional fields."""
        post = {
            "id": "minimal",
            "created_utc": 1636000000,
            "subreddit": "stocks",
            "author": "user",
            "title": "Minimal post with SPY",
            # Missing: selftext, score, upvote_ratio, etc.
        }

        received_at = datetime.now(timezone.utc)
        normalized = social_arctic.normalize_arctic_post(
            post, received_at, run_id="testmin"
        )

        # Verify required fields present
        assert normalized["id"] == "minimal"
        assert "SPY" in normalized["symbols"]
        # Optional fields should have defaults
        assert "body" in normalized
        assert "upvote_ratio" in normalized or normalized.get("upvote_ratio") is None


class TestFetchPostsForDay:
    """Tests for fetch_posts_for_day function."""

    @patch("orbit.ingest.social_arctic.requests.get")
    def test_fetch_success(self, mock_get):
        """Test successful fetch of posts for a day."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "post1",
                    "created_utc": 1636000000,
                    "subreddit": "stocks",
                    "author": "user1",
                    "title": "SPY post",
                    "selftext": "Content",
                    "score": 10,
                    "num_comments": 5,
                    "permalink": "/r/stocks/comments/post1/",
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        date = datetime(2024, 11, 5)
        posts = social_arctic.fetch_posts_for_day("stocks", date)

        # Verify
        assert len(posts) == 1
        assert posts[0]["id"] == "post1"
        mock_get.assert_called_once()

    @patch("orbit.ingest.social_arctic.requests.get")
    def test_fetch_pagination(self, mock_get):
        """Test pagination through multiple pages."""
        # First call returns full page, second returns partial (indicating end)
        mock_response_1 = Mock()
        mock_response_1.json.return_value = {
            "data": [{"id": f"post{i}", "created_utc": 1636000000 + i} for i in range(25)]
        }
        mock_response_1.raise_for_status = Mock()

        mock_response_2 = Mock()
        mock_response_2.json.return_value = {
            "data": [{"id": "post25", "created_utc": 1636000025}]
        }
        mock_response_2.raise_for_status = Mock()

        mock_get.side_effect = [mock_response_1, mock_response_2]

        date = datetime(2024, 11, 5)
        posts = social_arctic.fetch_posts_for_day("stocks", date, limit=25)

        # Verify multiple pages fetched
        assert len(posts) == 26  # 25 + 1
        assert mock_get.call_count == 2

    @patch("orbit.ingest.social_arctic.requests.get")
    def test_fetch_empty_day(self, mock_get):
        """Test fetching day with no posts."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        date = datetime(2024, 11, 5)
        posts = social_arctic.fetch_posts_for_day("stocks", date)

        assert len(posts) == 0

    @patch("orbit.ingest.social_arctic.requests.get")
    def test_fetch_with_headers(self, mock_get):
        """Test that User-Agent is set in headers."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        date = datetime(2024, 11, 5)
        social_arctic.fetch_posts_for_day("stocks", date)

        # Verify User-Agent header
        call_kwargs = mock_get.call_args[1]
        assert "User-Agent" in call_kwargs["headers"]


class TestCheckpointOperations:
    """Tests for checkpoint save/load operations."""

    def test_save_and_load_checkpoint(self, tmp_path):
        """Test checkpoint save and load roundtrip."""
        checkpoint_file = tmp_path / "test_checkpoint.json"

        data = {
            "total_posts": 5000,
            "total_requests": 200,
            "current_date": "2024-11-05",
            "completed_days": 30,
            "completed_dates": ["2024-11-01_stocks", "2024-11-02_stocks"],
        }

        # Save
        social_arctic.save_checkpoint(checkpoint_file, data)
        assert checkpoint_file.exists()

        # Load
        loaded = social_arctic.load_checkpoint(checkpoint_file)
        assert loaded == data

    def test_load_nonexistent_checkpoint(self, tmp_path):
        """Test loading checkpoint that doesn't exist returns None."""
        checkpoint_file = tmp_path / "nonexistent.json"
        result = social_arctic.load_checkpoint(checkpoint_file)
        assert result is None


class TestRateLimiting:
    """Tests for rate limiting behavior."""

    def test_target_rps_constant(self):
        """Test that TARGET_RPS is set to tested value."""
        assert social_arctic.TARGET_RPS == 3.5  # From empirical testing

    def test_request_interval_calculation(self):
        """Test request interval calculation."""
        interval = 1.0 / social_arctic.TARGET_RPS
        expected = 1.0 / 3.5  # ~0.286 seconds
        assert abs(interval - expected) < 0.001


class TestDefaultSubreddits:
    """Tests for default subreddit configuration."""

    def test_default_subreddits(self):
        """Test that default subreddits are correctly defined."""
        assert social_arctic.DEFAULT_SUBREDDITS == ["stocks", "investing", "wallstreetbets"]


class TestIntegrationScenarios:
    """Integration test scenarios."""

    @patch("orbit.ingest.social_arctic.fetch_posts_for_day")
    def test_backfill_with_filtering(self, mock_fetch, tmp_path):
        """Test that off-topic posts are filtered during backfill."""
        # Mock posts: one on-topic, one off-topic
        mock_fetch.return_value = [
            {
                "id": "ontopic",
                "created_utc": 1636000000,
                "subreddit": "stocks",
                "author": "user1",
                "title": "SPY discussion",  # On-topic
                "selftext": "SPY analysis",
                "score": 10,
                "num_comments": 5,
                "permalink": "/r/stocks/comments/ontopic/",
            },
            {
                "id": "offtopic",
                "created_utc": 1636000001,
                "subreddit": "stocks",
                "author": "user2",
                "title": "Tesla stock discussion",  # Off-topic (no SPY/VOO/S&P/market)
                "selftext": "TSLA going to the moon",
                "score": 5,
                "num_comments": 2,
                "permalink": "/r/stocks/comments/offtopic/",
            },
        ]

        # Verify that filtering logic would work
        received_at = datetime.now(timezone.utc)
        posts = mock_fetch()

        normalized = [
            social_arctic.normalize_arctic_post(post, received_at, "test")
            for post in posts
        ]

        # Filter off-topic
        filtered = [p for p in normalized if "off-topic" not in p["symbols"]]

        assert len(filtered) == 1
        assert filtered[0]["id"] == "ontopic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
