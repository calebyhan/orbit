# ORBIT — Deduplication & Novelty (Text)

*Last edited: 2025-11-05*

## Purpose

Remove **duplicate/near-duplicate** news/posts and compute a **novelty score** per item/day so intensity metrics aren’t inflated by syndicated stories or reposts.

## Scope

Applies to **news** (Alpaca) and **social** (Reddit) text after time alignment and before daily aggregation.

## Inputs

* `data/raw/news/` or `data/raw/social/` for day *T* in the membership window `(T−1 15:30, T 15:30]` (ET).
* Text fields: `headline` (news), `title + body` (social).

## Outputs

* Curated tables (`data/curated/news/`, `data/curated/social/`) with:

  * `is_dupe: bool`  — flagged duplicates excluded from counts
  * `cluster_id: str` — identifier of dup cluster (leader is the earliest item)
  * `novelty: float`  — per-item novelty in **[0,1]** (higher = more novel)
  * Aggregates per day: average `novelty` used by features

---

## Text preparation

* Lowercase, strip URLs, normalize whitespace and punctuation.
* Remove boilerplate source footers (news) and common signatures (social) if present.
* Keep emojis/emphasis; they may signal sarcasm or tone.

## Near-duplicate detection

Two interchangeable methods (choose one in config):

### A) Simhash (fast, robust)

* Tokenize into 3-grams; compute simhash.
* **Duplicate rule:** items within **Hamming distance ≤ 3** are considered near-duplicates.

### B) Cosine similarity (TF–IDF)

* Vectorize with TF–IDF on unigrams + bigrams (min_df=2).
* **Duplicate rule:** pairs with **cosine ≥ 0.92** are near-duplicates.

**Clustering:**

* Build connected components from duplicate pairs per day; assign `cluster_id` as the earliest item’s id.
* Mark all but the **cluster leader** as `is_dupe=True`.

## Novelty scoring

For each (non-duplicate) item on day *T*:

1. Build a **reference corpus** = non-duplicate items from the **prior `novelty.window_days`** (default 7 days).
2. Compute max similarity **s** between the item and any document in the reference.
3. Define **novelty** = `1 − s` (clipped to [0,1]).

* For Simhash: use normalized Hamming distance → similarity `s = 1 − (ham/64)`.
* For Cosine: `s = cosine(item, corpus_doc)`.

**Daily novelty aggregate** = mean of per-item novelties for non-duplicates on day *T*.

## Performance tips

* Pre-hash texts to avoid reprocessing the same content across runs.
* Use **MinHash LSH** or blocking (prefix/suffix) when day volume spikes.
* Cap pairwise comparisons with ANN (e.g., FAISS) if needed.

## Pseudocode

```python
items = load_window(T)
texts = prepare(items.text)
if cfg.preprocessing.dedupe.method == 'simhash':
    sigs = simhash_batch(texts)
    dup_pairs = [(i,j) for i<j if hamming(sigs[i], sigs[j]) <= 3]
else:
    X = tfidf(texts)
    dup_pairs = [(i,j) for i<j if cosine(X[i], X[j]) >= 0.92]
clusters = connected_components(dup_pairs)
leader = earliest_in_cluster(clusters)
items['is_dupe'] = ~items.index.isin(leader)

# novelty vs prior N days
ref = load_prior_days(T, n=cfg.preprocessing.novelty.window_days)
ref_X = embed(ref.text)
cur_X = embed(items.loc[~items.is_dupe, 'text'])
s = max_similarity(cur_X, ref_X)
items.loc[~items.is_dupe, 'novelty'] = (1 - s).clip(0,1)
```

## QC & logging

* Log: total items, dup rate (%), number of clusters, avg cluster size.
* Distribution of per-item novelty and daily average (should be in [0,1]).
* Spot-check top **high-similarity** clusters; ensure they’re truly near-duplicates.

## Acceptance checklist

* Duplicates are clustered per day; only **leaders** contribute to daily counts.
* Novelty computed against the **prior N days** (not including *T*).
* Output fields `is_dupe`, `cluster_id`, `novelty` exist and are within expected domains.
* Daily aggregates update correctly and do not double-count stories.

---

## Related Files

* `05-ingestion/news_alpaca_ws_ingest.md` — News deduplication
* `05-ingestion/social_reddit_ingest.md` — Social deduplication
* `07-features/news_features.md` — Novelty features
* `07-features/social_features.md` — Novelty features
