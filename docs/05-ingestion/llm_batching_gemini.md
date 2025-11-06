# ORBIT — Ingestion: LLM Batching (Gemini Sentiment)

*Last edited: 2025-11-06*

## Purpose

Batch and score **all** news and social items with Gemini 2.0 Flash-Lite API, merging results back into curated tables. This is the primary sentiment analysis pathway for ORBIT.

## Inputs

- **Config:** `sources.gemini.*` (model, api_keys, batch_size, rotation_strategy)
- **Creds:** `GEMINI_API_KEY_1` through `GEMINI_API_KEY_5` (up to 5 keys supported)
- **Text items:** All news headlines and social posts from day *T* (≤15:30 ET cutoff)

## Outputs

- **Raw requests/responses:** `data/raw/gemini/` (partitioned by `date`)
- **Merged fields:** appended to curated news/social (e.g., `sent_llm, stance, sarcasm, certainty, toxicity`)

## Steps

1) **Select all items** from curated inputs for day *T* (≤15:30 ET).
2) **Choose API key:** Round-robin or least-used across configured keys.
3) **Build JSONL:** One object per line with minimal fields (`id, text, timestamp_utc, context`).
4) **Send batch** of size `batch_size` (default 200) honoring per-key RPM/TPM/RPD.
5) **Validate responses:** 1:1 id mapping; domains: `sent_llm∈[-1,1]`, `certainty∈[0,1]`.
6) **Persist** raw req/resp; **merge** fields back into curated tables.
7) **Rotate key:** Move to next key for next batch (if multi-key enabled).
8) **Fallback:** On errors, retry with exponential backoff; if all retries fail, mark with neutral sentiment and log.

## Multi-key rotation

**Strategy options:**
- `round_robin`: Cycle through keys in order (key1 → key2 → ... → key5 → key1)
- `least_used`: Select key with lowest daily usage count

**Quota tracking:**
- Track requests per key per day
- Reset counters at midnight Pacific (when Gemini RPD resets)
- Log key switches: `[INFO] Rotated to GEMINI_API_KEY_3 (usage: 45/200)`

**Failover:**
- If current key exhausted (≥190/200), try next available key
- If all keys exhausted, defer to next day and log warning

## QC

- No orphaned lines; batch sizes and throughput within config per-key limits.
- Multi-key rotation working correctly; usage balanced across keys.
- Aggregates recomputed; no NaN propagation.
- Daily cost tracking logged (tokens used × rate, even if $0 on free tier).

## Acceptance checklist

- All text items processed through Gemini (no local fallback models).
- Responses validated and merged successfully.
- Multi-key rotation (if enabled) distributes load and respects per-key quotas.
- Rate limits respected; errors logged to `data/rejects/gemini/`.
- Total daily usage stays within combined key quotas (e.g., 1,000 RPD with 5 keys).

---

## Related Files

* `04-data-sources/gemini_sentiment_api.md` — Gemini API spec
* `99-templates/TEMPLATE_prompt_gemini.jsonl.md` — Prompt template
* `07-features/news_features.md` — News sentiment features
* `07-features/social_features.md` — Social sentiment features
