"""ORBIT Preprocessing - Deduplication & Novelty Scoring.

Implements near-duplicate detection and novelty scoring as documented in:
docs/06-preprocessing/deduplication_novelty.md

Uses simhash for fast near-duplicate detection and novelty scoring against
a 7-day reference corpus.
"""

import hashlib
import re
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np


def prepare_text(text: str) -> str:
    """Prepare text for deduplication by normalizing.

    Args:
        text: Raw text

    Returns:
        Normalized text (lowercase, no URLs, normalized whitespace)
    """
    if not text or not isinstance(text, str):
        return ""

    # Lowercase
    text = text.lower()

    # Remove URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text


def compute_simhash(text: str, num_bits: int = 64) -> int:
    """Compute simhash of text for near-duplicate detection.

    Uses 3-gram tokenization and SHA-256 hashing.

    Args:
        text: Prepared text
        num_bits: Hash size in bits (default: 64)

    Returns:
        Simhash as integer

    References:
        - Charikar, M. S. (2002). "Similarity estimation techniques from rounding algorithms"
        - https://en.wikipedia.org/wiki/SimHash
    """
    if not text:
        return 0

    # Create 3-grams
    tokens = []
    for i in range(len(text) - 2):
        tokens.append(text[i:i+3])

    if not tokens:
        # Fallback for very short text
        tokens = [text]

    # Initialize weight vector
    v = np.zeros(num_bits, dtype=np.int32)

    # For each token, hash it and update weights
    for token in tokens:
        # Use SHA-256 and take first num_bits bits
        token_hash = hashlib.sha256(token.encode('utf-8')).digest()

        # Convert to bits
        for i in range(min(num_bits, len(token_hash) * 8)):
            byte_idx = i // 8
            bit_idx = i % 8
            bit = (token_hash[byte_idx] >> bit_idx) & 1

            # Update weight vector
            if bit:
                v[i] += 1
            else:
                v[i] -= 1

    # Convert weights to binary hash
    simhash = 0
    for i in range(num_bits):
        if v[i] > 0:
            simhash |= (1 << i)

    return simhash


def hamming_distance(hash1: int, hash2: int) -> int:
    """Compute Hamming distance between two hashes.

    Args:
        hash1: First hash
        hash2: Second hash

    Returns:
        Hamming distance (number of differing bits)
    """
    return bin(hash1 ^ hash2).count('1')


def find_duplicates(
    texts: List[str],
    ids: List[str],
    threshold: int = 3
) -> List[Tuple[int, int]]:
    """Find near-duplicate pairs using simhash.

    Args:
        texts: List of prepared texts
        ids: List of corresponding IDs
        threshold: Maximum Hamming distance for duplicates (default: 3)

    Returns:
        List of (i, j) index pairs where i < j are duplicates
    """
    if len(texts) != len(ids):
        raise ValueError("texts and ids must have same length")

    # Compute simhashes
    hashes = [compute_simhash(text) for text in texts]

    # Find duplicate pairs
    pairs = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            if hamming_distance(hashes[i], hashes[j]) <= threshold:
                pairs.append((i, j))

    return pairs


def cluster_duplicates(
    pairs: List[Tuple[int, int]],
    n_items: int
) -> dict:
    """Build connected components from duplicate pairs.

    Args:
        pairs: List of (i, j) duplicate pairs
        n_items: Total number of items

    Returns:
        Dict mapping item index to cluster ID (leader index)
    """
    # Build adjacency list
    adj = {i: set() for i in range(n_items)}
    for i, j in pairs:
        adj[i].add(j)
        adj[j].add(i)

    # Find connected components using DFS
    visited = set()
    clusters = {}

    for start in range(n_items):
        if start in visited:
            continue

        # DFS to find component
        component = []
        stack = [start]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            stack.extend(adj[node])

        # Leader is earliest (lowest index) in component
        leader = min(component)
        for node in component:
            clusters[node] = leader

    return clusters


def add_dedup_fields(
    df: pd.DataFrame,
    text_column: str,
    id_column: str = 'id',
    threshold: int = 3,
) -> pd.DataFrame:
    """Add deduplication fields to dataframe.

    Adds columns:
    - is_dupe: bool (True if duplicate, False if leader)
    - cluster_id: str (ID of cluster leader)

    Args:
        df: Input dataframe
        text_column: Name of text column
        id_column: Name of ID column
        threshold: Hamming distance threshold for duplicates

    Returns:
        Dataframe with dedup fields added
    """
    if df.empty:
        df['is_dupe'] = pd.Series(dtype=bool)
        df['cluster_id'] = pd.Series(dtype=str)
        return df

    # Prepare texts
    texts = df[text_column].fillna('').apply(prepare_text).tolist()
    ids = df[id_column].astype(str).tolist()

    # Find duplicates
    pairs = find_duplicates(texts, ids, threshold=threshold)

    # Cluster
    clusters = cluster_duplicates(pairs, len(df))

    # Add fields
    df = df.copy()
    df['cluster_id'] = df.index.map(lambda i: ids[clusters.get(i, i)])
    df['is_dupe'] = df.index.map(lambda i: clusters.get(i, i) != i)

    return df


def compute_novelty(
    current_texts: List[str],
    reference_texts: List[str],
    threshold: int = 64,  # Maximum Hamming distance
) -> np.ndarray:
    """Compute novelty scores for current texts vs reference corpus.

    Novelty = 1 - max_similarity, where similarity is based on normalized
    Hamming distance.

    Args:
        current_texts: List of prepared texts to score
        reference_texts: List of prepared reference texts (prior 7 days)
        threshold: Maximum Hamming distance to consider (default: 64)

    Returns:
        Array of novelty scores in [0, 1]
    """
    if not current_texts:
        return np.array([])

    if not reference_texts:
        # No reference corpus - all items are novel
        return np.ones(len(current_texts))

    # Compute simhashes
    current_hashes = [compute_simhash(text) for text in current_texts]
    reference_hashes = [compute_simhash(text) for text in reference_texts]

    # For each current item, find max similarity with reference
    novelties = []
    for cur_hash in current_hashes:
        # Find minimum Hamming distance to reference
        min_distance = threshold
        for ref_hash in reference_hashes:
            dist = hamming_distance(cur_hash, ref_hash)
            min_distance = min(min_distance, dist)

        # Convert to similarity (normalized Hamming distance)
        # similarity = 1 - (distance / 64)
        similarity = 1.0 - (min_distance / 64.0)

        # Novelty = 1 - similarity
        novelty = 1.0 - similarity

        # Clip to [0, 1]
        novelty = max(0.0, min(1.0, novelty))

        novelties.append(novelty)

    return np.array(novelties)


def add_novelty_field(
    df: pd.DataFrame,
    text_column: str,
    reference_df: Optional[pd.DataFrame] = None,
    window_days: int = 7,
) -> pd.DataFrame:
    """Add novelty scores to dataframe.

    Args:
        df: Input dataframe (current day)
        text_column: Name of text column
        reference_df: Reference dataframe (prior window_days), optional
        window_days: Number of days in reference window (for logging)

    Returns:
        Dataframe with novelty field added
    """
    if df.empty:
        df['novelty'] = pd.Series(dtype=float)
        return df

    # Only score non-duplicates
    if 'is_dupe' in df.columns:
        non_dupes = df[~df['is_dupe']].copy()
    else:
        non_dupes = df.copy()

    if non_dupes.empty:
        df['novelty'] = pd.Series(dtype=float)
        return df

    # Prepare current texts
    current_texts = non_dupes[text_column].fillna('').apply(prepare_text).tolist()

    # Prepare reference texts
    if reference_df is not None and not reference_df.empty:
        # Only use non-duplicates from reference
        if 'is_dupe' in reference_df.columns:
            reference_df = reference_df[~reference_df['is_dupe']]

        reference_texts = reference_df[text_column].fillna('').apply(prepare_text).tolist()
    else:
        reference_texts = []

    # Compute novelty
    novelties = compute_novelty(current_texts, reference_texts)

    # Add to dataframe
    df = df.copy()
    df['novelty'] = np.nan  # Default for duplicates

    # Set novelty for non-duplicates
    non_dupe_indices = non_dupes.index
    df.loc[non_dupe_indices, 'novelty'] = novelties

    return df


def dedupe_and_score_novelty(
    current_df: pd.DataFrame,
    text_column: str,
    id_column: str = 'id',
    reference_df: Optional[pd.DataFrame] = None,
    window_days: int = 7,
    hamming_threshold: int = 3,
) -> pd.DataFrame:
    """Apply deduplication and novelty scoring to dataframe.

    This is the main entrypoint that combines dedup and novelty.

    Args:
        current_df: Input dataframe for current day
        text_column: Name of text column
        id_column: Name of ID column
        reference_df: Reference dataframe (prior window_days)
        window_days: Number of days in reference window
        hamming_threshold: Hamming distance threshold for duplicates

    Returns:
        Dataframe with dedup and novelty fields added
    """
    # Apply deduplication
    df = add_dedup_fields(
        current_df,
        text_column=text_column,
        id_column=id_column,
        threshold=hamming_threshold,
    )

    # Apply novelty scoring
    df = add_novelty_field(
        df,
        text_column=text_column,
        reference_df=reference_df,
        window_days=window_days,
    )

    return df
