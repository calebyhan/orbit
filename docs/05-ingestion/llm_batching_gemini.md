# ORBIT — Ingestion: LLM Batching (Gemini Escalation)
_Last edited: 2025-11-05_

## Purpose
Batch and score **uncertain/high-impact** social (and optionally news) items with Gemini, merging results back into curated tables.

## Inputs
- **Config:** `sources.gemini.*`, `features.standardization.*`
- **Creds:** `GEMINI_API_KEY`
- **Candidates:** items flagged by social/news preprocess where `|VADER| < τ` or VADER vs FinBERT disagree, or `buzz_z > threshold`.

## Outputs
- **Raw requests/responses:** `data/raw/gemini/` (partitioned by `date`)
- **Merged fields:** appended to curated social/news (e.g., `sent_llm, stance, sarcasm, certainty, toxicity`)

## Steps
1) **Select candidates** from curated inputs for day *T* (≤15:30 ET).
2) **Build JSONL**: one object per line with minimal fields (`id, text, timestamp_utc, context`).
3) **Send batches** of size `batch_size` honoring RPM/TPM/RPD.
4) **Validate responses**: 1:1 id mapping; domains: `sent_llm∈[-1,1]`, `certainty∈[0,1]`.
5) **Persist** raw req/resp; **merge** fields back into curated tables.
6) **Fallback**: on errors, skip LLM and keep local sentiment.

## QC
- No orphaned lines; batch sizes and throughput within config.
- Aggregates recomputed; no NaN propagation.

## Acceptance checklist
- Candidates correctly selected; responses validated and merged.
- Rate limits respected; errors logged to `data/rejects/gemini/`.

---

## Related Files

* `04-data-sources/gemini_sentiment_api.md` — Gemini API spec
* `99-templates/TEMPLATE_prompt_gemini.jsonl.md` — Prompt template
* `07-features/news_features.md` — News sentiment features
* `07-features/social_features.md` — Social sentiment features
