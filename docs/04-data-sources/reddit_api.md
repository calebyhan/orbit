# ORBIT — Reddit API (Social)

*Last edited: 2025-11-05*

## Purpose

Define how ORBIT queries the **official Reddit Data API** for market‑wide chatter (SPY/VOO/S&P 500), normalizes results, enforces rate limits, and prepares daily aggregates for features.

## Access & auth

* **OAuth:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` (see `docs/03-config/env_keys.md`).
* **Flows:** installed‑app/device or web auth preferred; script creds only when compliant with Reddit TOS.
* **User‑Agent:** required, descriptive (e.g., `ORBIT/1.0 by you@example.com`).

## Query scope

* **Subreddits:** `r/stocks`, `r/investing`, `r/wallstreetbets` (configurable).
* **Terms:** `"SPY"`, `"VOO"`, `"S&P 500"`, `"S&P"`, `"market"` (with blacklist rules for false positives like “spy camera”).
* **Window:** rolling 24h window ending at **15:30 ET** for day *T*.
* **Objects:** posts (submissions) + their top‑level comments (optional) for velocity metrics.

## Normalization → raw lake

Persist to `data/raw/social/` as Parquet (partitioned by `date=YYYY-MM-DD`). For each item:

* `post_id: str`
* `created_utc: timestamp[ns, UTC]`
* `received_at: timestamp[ns, UTC]`
* `subreddit: str`
* `author: str | null`
* `author_karma: int | null` (link + comment karma snapshot)
* `title: str`
* `body: str | null`
* `score: int` (upvotes)
* `num_comments: int`
* `permalink: str`
* `matched_terms: list[str]`
* `raw: json`
* `run_id: str`

**Comments (optional table):** `comment_id, post_id, created_utc, body, score`.

## Filters & quality

* **Bot/throwaway filter:** min account age (days) and min karma thresholds.
* **NSFW/removed:** drop or flag; never use deleted content blobs.
* **Language:** restrict to English where possible; keep others flagged.

## Rate limits & retries

* Batch paginated requests; respect published per‑client limits.
* Use **exponential backoff** on `429`/server errors; jitter to avoid sync storms.
* Log request counts, remaining quota, and backoffs per run.

## Cutoff & time rules

* Include only records with `created_utc (ET) ≤ 15:30` for day *T* (see `docs/03-config/cutoffs_timezones.md`).
* For training, optionally drop items inside the last **publish_lag_minutes** before cutoff.

## Dedup & mapping

* **Dedup key:** `post_id`; also drop near‑duplicates by `simhash(title+body)` within day *T*.
* **Mapping to index:** keyword rules map posts to **market‑wide** (SPY/VOO/S&P 500) vs **off‑topic**; maintain a blacklist.

## Sentiment pathway

1. **Tier‑1 (cheap):** VADER / FinBERT on `title + body` → `sent_vader`, `sent_finbert` in [−1,1].
2. **Uncertain cases:** flag when `|sent_vader| < τ` or classifiers disagree.
3. **LLM escalation (optional):** batch these rows to Gemini; store `sent_llm`, `stance`, `sarcasm`, `certainty` (see `gemini_sentiment_api.md`).

## Curated daily aggregates

Emit `data/curated/social/` per day with:

* `date: date`
* `post_count: int`
* `post_count_z: float` (vs 60‑day)
* `comment_velocity: float` (comments/hour near cutoff)
* `cred_weighted_sent: float` (sentiment weighted by log‑karma, capped)
* `sarcasm_rate: float` (LLM only)
* `novelty: float` (vs prior 7d n‑grams)
* `last_item_ts: timestamp[ns, UTC]`
* `run_id: str`

## Errors & rejects

* Write malformed items to `data/rejects/social/` with reason.
* If API unavailable → curated row with `post_count=0`; gates will reduce text weight.

## QC checks

* Row counts non‑decreasing vs similar weekdays; sudden zeros require log note.
* Dedup effectiveness reported; novelty ∈ [0,1].
* Cutoff properly enforced (no items after 15:30 ET).

## Acceptance checklist

* Can fetch, normalize, and store posts within quota and cutoff.
* Produces curated daily aggregates with the fields above.
* Integrates with optional LLM escalation and emits sentiment fields consistently.

---

## Related Files

* `05-ingestion/social_reddit_ingest.md` — Social media ingestion implementation
* `12-schemas/social.parquet.schema.md` — Social data schema
* `03-config/env_keys.md` — API credentials configuration
* `03-config/cutoffs_timezones.md` — Time cutoff rules
* `04-data-sources/gemini_sentiment_api.md` — LLM sentiment escalation
* `06-preprocessing/quality_filters_social.md` — Quality filters
* `07-features/social_features.md` — Social-based features
