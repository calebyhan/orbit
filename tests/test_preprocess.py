"""Unit tests for orbit.preprocess module.

Tests cutoff enforcement, deduplication, and novelty scoring.
"""

from datetime import datetime, timezone
import pandas as pd
import pytest

from orbit.preprocess import cutoffs, dedupe


class TestCutoffs:
    """Tests for cutoff enforcement."""

    def test_membership_window(self):
        """Test membership window calculation."""
        date_T = pd.Timestamp("2024-11-05")
        start, end = cutoffs.membership_window(date_T)

        # Window should be (T-1 15:30, T 15:30] in ET
        assert start.strftime("%Y-%m-%d %H:%M") == "2024-11-04 15:30"
        assert end.strftime("%Y-%m-%d %H:%M") == "2024-11-05 15:30"
        assert start.tz is not None  # Should be timezone-aware
        assert end.tz is not None

    def test_apply_cutoff_basic(self):
        """Test basic cutoff application."""
        # Create test data with timestamps in UTC
        df = pd.DataFrame({
            'id': ['a', 'b', 'c', 'd'],
            'published_at': pd.to_datetime([
                "2024-11-04 19:00:00",  # Before window (T-1 14:00 ET)
                "2024-11-04 21:00:00",  # In window (T-1 16:00 ET)
                "2024-11-05 20:00:00",  # In window (T 15:00 ET)
                "2024-11-05 21:00:00",  # After window (T 16:00 ET)
            ], utc=True),
        })

        result = cutoffs.apply_cutoff(
            df,
            ts_column='published_at',
            date_T=pd.Timestamp("2024-11-05"),
            safety_lag_minutes=0,
            training=False,
        )

        # Should only include items b and c
        assert len(result) == 2
        assert set(result['id']) == {'b', 'c'}

    def test_apply_cutoff_with_safety_lag(self):
        """Test cutoff with safety lag for training."""
        df = pd.DataFrame({
            'id': ['a', 'b', 'c'],
            'published_at': pd.to_datetime([
                "2024-11-04 21:00:00",  # In window, safe (16:00 ET)
                "2024-11-05 19:45:00",  # In window, safe (14:45 ET, before safety cutoff)
                "2024-11-05 20:15:00",  # In window, dropped by safety lag (15:15 ET, after safety cutoff)
            ], utc=True),
        })

        # Apply 30 min safety lag (cutoff 15:30 ET, safety cutoff 15:00 ET)
        result = cutoffs.apply_cutoff(
            df,
            ts_column='published_at',
            date_T=pd.Timestamp("2024-11-05"),
            safety_lag_minutes=30,
            training=True,
        )

        # Should include a and b (both before safety cutoff 15:00 ET)
        # Should exclude c (after safety cutoff)
        assert len(result) == 2
        assert set(result['id']) == {'a', 'b'}

    def test_apply_cutoff_empty(self):
        """Test cutoff on empty dataframe."""
        df = pd.DataFrame(columns=['id', 'published_at'])
        result = cutoffs.apply_cutoff(
            df,
            ts_column='published_at',
            date_T=pd.Timestamp("2024-11-05"),
        )
        assert len(result) == 0

    def test_validate_cutoff_compliance(self):
        """Test cutoff validation."""
        df = pd.DataFrame({
            'id': ['a', 'b'],
            'published_at': pd.to_datetime([
                "2024-11-04 21:00:00",
                "2024-11-05 20:00:00",
            ], utc=True),
        })

        validation = cutoffs.validate_cutoff_compliance(
            df,
            ts_column='published_at',
            date_T=pd.Timestamp("2024-11-05"),
        )

        assert validation['compliant'] == True
        assert validation['total_items'] == 2
        assert validation['out_of_window'] == 0


class TestDedupe:
    """Tests for deduplication."""

    def test_prepare_text(self):
        """Test text preparation."""
        text = "This is a TEST with http://example.com URL"
        prepared = dedupe.prepare_text(text)

        assert prepared == "this is a test with url"
        assert "http://" not in prepared
        assert prepared.islower()

    def test_compute_simhash_consistency(self):
        """Test that simhash is consistent."""
        text = "test document for hashing"
        hash1 = dedupe.compute_simhash(text)
        hash2 = dedupe.compute_simhash(text)

        assert hash1 == hash2

    def test_compute_simhash_uniqueness(self):
        """Test that different texts produce different hashes."""
        text1 = "first document"
        text2 = "completely different document"

        hash1 = dedupe.compute_simhash(text1)
        hash2 = dedupe.compute_simhash(text2)

        assert hash1 != hash2

    def test_hamming_distance(self):
        """Test Hamming distance calculation."""
        hash1 = 0b1010
        hash2 = 0b1110

        distance = dedupe.hamming_distance(hash1, hash2)
        assert distance == 1  # Only one bit differs

    def test_find_duplicates(self):
        """Test duplicate detection."""
        texts = [
            "the quick brown fox",
            "the quick brown fox",  # Exact duplicate
            "completely different text"
        ]
        ids = ["a", "b", "c"]

        pairs = dedupe.find_duplicates(texts, ids, threshold=3)

        # Should find a-b as duplicates
        assert (0, 1) in pairs or (1, 0) in pairs
        # Should not match c with anything
        assert (0, 2) not in pairs
        assert (1, 2) not in pairs

    def test_cluster_duplicates(self):
        """Test clustering of duplicate pairs."""
        pairs = [(0, 1), (1, 2)]  # 0-1 and 1-2 are dupes
        clusters = dedupe.cluster_duplicates(pairs, n_items=3)

        # All should map to same leader (0)
        assert clusters[0] == 0
        assert clusters[1] == 0
        assert clusters[2] == 0

    def test_add_dedup_fields(self):
        """Test adding dedup fields to dataframe."""
        df = pd.DataFrame({
            'id': ['a', 'b', 'c'],
            'text': [
                "the quick brown fox",
                "the quick brown fox",  # Duplicate
                "completely different"
            ]
        })

        result = dedupe.add_dedup_fields(df, text_column='text')

        # Check fields added
        assert 'is_dupe' in result.columns
        assert 'cluster_id' in result.columns

        # Second item should be marked as duplicate
        assert result.loc[1, 'is_dupe'] == True
        assert result.loc[0, 'is_dupe'] == False

        # Both duplicates should have same cluster_id
        assert result.loc[0, 'cluster_id'] == result.loc[1, 'cluster_id']

    def test_compute_novelty_no_reference(self):
        """Test novelty when there's no reference corpus."""
        texts = ["new text", "another new text"]
        reference = []

        novelties = dedupe.compute_novelty(texts, reference)

        # All should be novel (1.0) when no reference
        assert len(novelties) == 2
        assert all(n == 1.0 for n in novelties)

    def test_compute_novelty_with_reference(self):
        """Test novelty scoring with reference corpus."""
        current = ["the quick brown fox"]
        reference = ["the quick brown fox"]  # Exact match

        novelties = dedupe.compute_novelty(current, reference)

        # Should have low novelty (high similarity)
        assert novelties[0] < 0.2

    def test_add_novelty_field(self):
        """Test adding novelty field to dataframe."""
        df = pd.DataFrame({
            'id': ['a', 'b'],
            'text': ["new text", "another text"],
            'is_dupe': [False, False]
        })

        result = dedupe.add_novelty_field(df, text_column='text')

        assert 'novelty' in result.columns
        # Should all be novel (no reference)
        assert all(result['novelty'] == 1.0)

    def test_dedupe_and_score_novelty(self):
        """Test combined dedup and novelty workflow."""
        df = pd.DataFrame({
            'id': ['a', 'b', 'c'],
            'text': [
                "the quick brown fox",
                "the quick brown fox",  # Duplicate
                "different text"
            ]
        })

        result = dedupe.dedupe_and_score_novelty(df, text_column='text')

        # Should have both dedup and novelty fields
        assert 'is_dupe' in result.columns
        assert 'cluster_id' in result.columns
        assert 'novelty' in result.columns

        # Duplicate should be marked
        assert result.loc[1, 'is_dupe'] == True

        # Non-duplicates should have novelty scores
        assert pd.notna(result.loc[0, 'novelty'])
        assert pd.notna(result.loc[2, 'novelty'])


class TestIntegration:
    """Integration tests for preprocessing pipeline."""

    def test_full_pipeline_workflow(self):
        """Test full preprocessing workflow."""
        # Create test data
        df = pd.DataFrame({
            'id': ['a', 'b', 'c', 'd'],
            'published_at': pd.to_datetime([
                "2024-11-04 21:00:00",
                "2024-11-05 19:00:00",
                "2024-11-05 19:30:00",
                "2024-11-05 20:15:00",
            ], utc=True),
            'text': [
                "market rally continues",
                "market rally continues",  # Duplicate
                "SPY hits new high",
                "completely different story"
            ]
        })

        # Apply cutoff
        df = cutoffs.apply_cutoff(
            df,
            ts_column='published_at',
            date_T=pd.Timestamp("2024-11-05"),
            training=True,
        )

        # Apply dedup and novelty
        result = dedupe.dedupe_and_score_novelty(
            df,
            text_column='text',
            id_column='id',
        )

        # Verify workflow completed
        assert len(result) > 0
        assert 'is_dupe' in result.columns
        assert 'novelty' in result.columns
        assert 'window_start_et' in result.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
