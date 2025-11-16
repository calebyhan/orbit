# ORBIT — Rate Limits & Backoff

*Last edited: 2025-11-15*

## Purpose

Centralize rate‑limit guidance, batching strategies, and backoff policies for all external sources.

## Summary table (configure per `orbit.yaml`)

| Source                        | Primary limits                                    | Our strategy                                                                      |
| ----------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Stooq (CSV)**               | None published; be polite                         | Cache last ETag; 1s delay; single fetch per symbol after close                    |
| **Alpaca News WS**            | Free tier: ~≤30 subscribed symbols                | Keep watchlist small (SPY/VOO); reconnect with backoff; avoid resubscribing loops |
| **Alpaca News REST (backfill)** | 200 RPM per key; 50 articles/page               | Target 190 RPM; checkpoint every 100 requests; exponential backoff on 429         |
| **Reddit API**                | OAuth limits per client                           | Batch queries; jittered polling; exponential backoff on 429/5xx                   |
| **Gemini (optional)**         | Throughput caps (RPM/TPM/RPD)                     | Batch JSONL (e.g., 200 items/call); escalate only uncertain/high‑impact items     |

> Exact numeric limits may vary by account/plan. Always respect current provider docs and adjust config.

## Exponential backoff (standard)

```python
def backoff(attempt, base_ms=500, max_ms=10000, factor=2.0):
    return min(max_ms, base_ms * (factor ** attempt))
```

* Apply jitter: `sleep_ms = backoff(attempt) * (0.5 + rand())`
* **Bounded retries** (e.g., 3–5) then fail with actionable error.

## Alpaca Historical News API (REST) - Detailed

**Rate limits (per API key):**
- **200 requests per minute (RPM)** - hard limit enforced with 429 status code
- No published daily/hourly quotas
- Free tier same as paid for rate limits

**Pagination:**
- Maximum **50 articles per request** (fixed, cannot be increased)
- Use `page_token` for continuation (opaque token returned in response)
- Sort by `asc` for chronological backfill (recommended)

**Volume estimates for SPY/VOO:**
- 10 years (2015-2025): ~474,500 articles (~130/day average)
- Total requests: ~9,490 (474,500 ÷ 50)
- **Single key timeline**: 1-2 hours with overhead
- **Multi-key (5)**: 15-20 minutes (5x throughput: ~950 RPM combined)

**Recommended strategy (single key):**
1. **Target 190 RPM** (safety margin below 200 limit)
   - Request interval: 60/190 = ~316ms between requests
2. **Checkpoint every 100 requests** (`.backfill_checkpoint_{run_id}.json`)
   - Saves: last_date, articles_fetched, requests_made
   - Auto-resume on restart
3. **Exponential backoff on 429**:
   - 1st retry: 60s
   - 2nd retry: 120s (2x)
   - 3rd retry: 240s (4x)
   - Max 5 attempts, then skip day and log error
4. **Progress tracking**: Live updates with articles, requests, RPM, ETA

**Error handling:**
- **429 (rate limit)**: Backoff 60s → 120s → 240s (exponential), max 5 retries
- **500/502/503**: Backoff 30s, max 3 retries per request
- **4xx (not 429)**: Log and skip (bad request/auth issue)

**Implementation notes:**
- Chunk by date (daily) for natural resume boundaries
- Use tqdm progress bar for visibility during long runs
- Run in tmux/screen for multi-hour backfills
- See `src/orbit/ingest/news_backfill.py` for reference implementation

## Token & batch budgeting (LLM)

* Track **input tokens** per batch; keep under configured TPM.
* Prefer fewer, larger batches until latency becomes an issue.
* Ensure **1:1** line mapping between request and response.

## Scheduling guidelines

* **Prices:** one run after close.
* **News:** continuous, but throttle reconnect attempts.
* **Social:** 2–6 pulls across the session; denser near U.S. midday/close.
* **LLM:** run once near cutoff to score the escalated set.

## Monitoring

* Log requests/min, tokens/min, and retry counts by source.
* Emit alerts when drop/skip events occur due to rate limits.

## Acceptance checks

* No 429 storms (retries remain bounded and jittered).
* LLM batches meet size/throughput budgets; zero orphaned lines in responses.
* Overall run completes within SLO without exceeding provider constraints.

---

## Related Files

* `04-data-sources/alpaca_news_ws.md` — Alpaca WS reconnection
* `04-data-sources/reddit_api.md` — Reddit API quotas
* `04-data-sources/gemini_sentiment_api.md` — Gemini batch limits
* `10-operations/failure_modes_playbook.md` — Rate limit error recovery
