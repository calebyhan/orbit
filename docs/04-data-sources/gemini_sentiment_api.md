# ORBIT — Gemini Sentiment API

*Last edited: 2025-11-06*

## Purpose

Define the **primary sentiment analysis pathway** using Google's Gemini 2.5 Flash-Lite (gemini-2.5-flash-lite) for all news and social media text. This doc standardizes prompt/response schemas, batching, multi-key rotation, and fallbacks.

## Model selection

**Primary model:** Gemini 2.5 Flash-Lite (gemini-2.5-flash-lite)
- **Free tier limits:** 30 RPM, 1M TPM, 200 RPD per API key
- **Cost (if upgraded):** ~$0.075 per 1M tokens
- **Performance:** Excellent financial domain understanding, JSON structured output
- **Latency:** Batch processing completes in <1 minute for typical daily volume

## Multi-key rotation (optional)

Support up to **5 API keys** (expandable if needed) for increased throughput:

**Benefits:**
- Combined quota: 5 keys × 200 RPD = **1,000 requests/day**
- Automatic failover if one key exhausted
- Round-robin or least-used distribution strategy

**Configuration:**
```yaml
sources:
  gemini:
    enabled: true
    model: "gemini-2.5-flash-lite"
    api_keys:
      - GEMINI_API_KEY_1
      - GEMINI_API_KEY_2
      - GEMINI_API_KEY_3
      - GEMINI_API_KEY_4
      - GEMINI_API_KEY_5
    rotation_strategy: "round_robin"  # or "least_used"
    batch_size: 200
```

**Key manager behavior:**
- Track daily usage per key
- Rotate to next key when current approaches quota (e.g., 190/200)
- Log key switches for audit trail
- Reset counters at midnight Pacific time (when RPD resets)

## Batch processing

* Group **N items per call** (`sources.gemini.batch_size`, default 200).
* Build **JSONL** payload (one object per line) with minimal fields.
* Track **attempt_no** and **run_id** for idempotency.
* All items processed in single daily batch (typical: 50-80 items/day).

## Input schema (per item)

```json
{
  "id": "reddit_<post_id>",
  "timestamp_utc": "2025-01-15T19:12:04Z",
  "channel": "reddit",
  "subreddit": "wallstreetbets",
  "ticker": "SPY",
  "text": "SPY gonna rip tomorrow after that Fed presser.",
  "context": {
    "title": "Fed softens language",
    "score": 124,
    "author_karma": 5400
  }
}
```

## Prompt contract (system instruction stub)

> **System**: You are a financial sentiment annotator. For each JSON line, read `text` (+ optional `context`). Output **one JSON object per line** with **only** the fields in the response schema. No prose, no extra keys.

## Response schema (per item)

```json
{
  "id": "reddit_<post_id>",
  "sent_llm": 0.62,             // float in [-1, 1]
  "stance": "bull",             // one of ["bull", "bear", "neutral"]
  "sarcasm": false,              // boolean
  "certainty": 0.76,             // [0,1]
  "toxicity": 0.03               // optional, [0,1]
}
```

## Transport & retries

* HTTP with exponential backoff; **bounded retries** (e.g., 3) on 429/5xx.
* On permanent failure: **skip** LLM and fall back to local scores; record in `data/rejects/gemini/`.

## Persistence

* Store raw request/response pairs for audit under `data/raw/gemini/` (partition by `date`).
* Merge LLM fields into **curated** social/news tables as optional columns.

## Post‑processing rules

* Clamp `sent_llm` to [-1,1], `certainty` and `toxicity` to [0,1].
* Use `sent_llm` as the primary sentiment score for all items.
* Compute **credibility‑weighted** aggregates (e.g., karma-weighted for social).
* On API failure: retry with backoff; if all retries fail, mark item with `sent_llm=0, certainty=0` and log to rejects.

## Privacy & compliance

* Never send PII or long user histories; include only the minimal text needed.
* Respect content policies; drop NSFW/removed content before LLM.
* Identify the client with a descriptive `User-Agent`.

## QC & acceptance checks

* Batch calls respect configured **batch_size** and per-key **rate limits**.
* Multi-key rotation distributes load evenly; no single key exceeds quota.
* Response lines **1:1** with request lines by matching `id`.
* All fields obey domains; missing responses are logged and defaulted to neutral (sent=0).
* Aggregates recompute without NaN propagation.
* Daily token usage logged for cost tracking (even on free tier).

---

## Related Files

* `05-ingestion/llm_batching_gemini.md` — Gemini batch processing
* `04-data-sources/rate_limits.md` — API rate limits
* `07-features/news_features.md` — News features using Gemini sentiment
* `07-features/social_features.md` — Social features using Gemini sentiment
