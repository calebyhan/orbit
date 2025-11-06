# ORBIT — Rate Limits & Backoff

*Last edited: 2025-11-05*

## Purpose

Centralize rate‑limit guidance, batching strategies, and backoff policies for all external sources.

## Summary table (configure per `orbit.yaml`)

| Source                | Primary limits                     | Our strategy                                                                      |
| --------------------- | ---------------------------------- | --------------------------------------------------------------------------------- |
| **Stooq (CSV)**       | None published; be polite          | Cache last ETag; 1s delay; single fetch per symbol after close                    |
| **Alpaca News WS**    | Free tier: ~≤30 subscribed symbols | Keep watchlist small (SPY/VOO); reconnect with backoff; avoid resubscribing loops |
| **Reddit API**        | OAuth limits per client            | Batch queries; jittered polling; exponential backoff on 429/5xx                   |
| **Gemini (optional)** | Throughput caps (RPM/TPM/RPD)      | Batch JSONL (e.g., 200 items/call); escalate only uncertain/high‑impact items     |

> Exact numeric limits may vary by account/plan. Always respect current provider docs and adjust config.

## Exponential backoff (standard)

```python
def backoff(attempt, base_ms=500, max_ms=10000, factor=2.0):
    return min(max_ms, base_ms * (factor ** attempt))
```

* Apply jitter: `sleep_ms = backoff(attempt) * (0.5 + rand())`
* **Bounded retries** (e.g., 3–5) then fail with actionable error.

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
