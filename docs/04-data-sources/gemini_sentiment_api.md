# ORBIT — Gemini Sentiment API (Optional Escalation)

*Last edited: 2025-11-05*

## Purpose

Define a **compact, batched** LLM scoring pathway for social/news text when local classifiers (VADER/FinBERT) are **uncertain** or **high‑impact**. This doc standardizes prompt/response schemas, batching, escalation criteria, and fallbacks.

## When to use (escalation rules)

Escalate only when ALL are true:

* Source enabled in config (`sources.gemini.enabled: true`).
* Item meets at least one trigger:

  * `|sent_vader| < vader_abs_lt` (config)
  * `disagreement == true` between VADER and FinBERT
  * `buzz_z > buzz_z_gt` for the day (high‑impact window)
* Token budget allows batch within configured limits.

## Request batching

* Group **N items per call** (`sources.gemini.batch_size`, default 200).
* Build **JSONL** payload (one object per line) with minimal fields.
* Track **attempt_no** and **run_id** for idempotency.

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
* Prefer `sent_llm` over local scores **only for escalated items**; otherwise keep tier‑1 values.
* Compute **credibility‑weighted** aggregates with the same caps used for local sentiment.

## Privacy & compliance

* Never send PII or long user histories; include only the minimal text needed.
* Respect content policies; drop NSFW/removed content before LLM.
* Identify the client with a descriptive `User-Agent`.

## QC & acceptance checks

* Batch calls do not exceed configured **batch_size** and **rate limits**.
* Response lines **1:1** with request lines by matching `id`.
* All fields obey domains; missing responses are logged and defaulted to local sentiment.
* Aggregates recompute without NaN propagation.

---

## Related Files

* `05-ingestion/llm_batching_gemini.md` — Gemini batch processing
* `04-data-sources/rate_limits.md` — API rate limits
* `07-features/news_features.md` — News features using Gemini sentiment
* `07-features/social_features.md` — Social features using Gemini sentiment
