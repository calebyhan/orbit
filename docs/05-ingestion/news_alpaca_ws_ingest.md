# ORBIT — Ingestion: Alpaca News WebSocket

*Last edited: 2025-11-11*

## Purpose

Stream **real-time news** from Alpaca’s Market Data **News WebSocket**, normalize events, enforce point-in-time rules, and persist rows for downstream curation and features.

## Inputs

* **Config:** `sources.alpaca_news.*`, `paths.*`, `schedule.*`
* **Creds:** `ALPACA_API_KEY`, `ALPACA_API_SECRET`
* **Symbols:** default `["SPY", "VOO"]` (≤30 free-tier cap)

## Outputs

* **Raw Parquet:** `data/raw/news/` partitioned by `date=YYYY-MM-DD`
* **Schema:**

  * `msg_id: string`
  * `published_at: timestamp[ns, UTC]`
  * `received_at: timestamp[ns, UTC]`
  * `symbols: list<string>`
  * `headline: string`
  * `summary: string|null`
  * `source: string`
  * `url: string|null`
  * `raw: json`
  * `run_id: string`

## Lifecycle

1. **Connect** WS → authenticate → subscribe to `symbols`.
2. **Read loop**: for each message, normalize → write to an in-memory buffer.
3. **Flush policy**: flush buffer to Parquet every `N` messages or every `T` seconds.
4. **Reconnect** with exponential backoff on errors; **resume** from last `published_at` if REST backfill is available.
5. **Shutdown** gracefully, flushing remaining buffer.

## Deduplication

* Primary key: provider `msg_id`; fallback to `sha1(headline + source + published_at)`.
* Keep the earliest `received_at` per `msg_id`.

## Point-in-time rule

* Curation step (separate job) must **exclude** items with `published_at (ET) > 15:30` for day *T*.
* During training, drop items within the last `publish_lag_minutes` before cutoff.

## QC

* Validate `published_at ≤ now()` and `received_at ≥ published_at - Δ` (tolerate small clock skew).
* Ensure `symbols` ∈ configured universe; log others.
* Track WS uptime, message rate, and flush counts.

## Pseudocode

```python
ws = connect(cfg.sources.alpaca_news.stream_url, creds)
subscribe(ws, cfg.sources.alpaca_news.symbols)
buf = []
while ws.open:
    msg = ws.recv()
    rec = normalize(msg)
    rec['received_at'] = utcnow()
    rec['run_id'] = run_id
    if not seen(rec['msg_id']):
        buf.append(rec)
    if len(buf) >= N or time_since_last_flush() > T:
        append_parquet(buf, base='data/raw/news/', partition='date')
        buf.clear()
```

## Errors & retries

* On WS close/500s: backoff with jitter, bounded retries; log reason.
* On malformed payload: write JSON to `data/rejects/news/` with error tag.

## Acceptance checklist

* ✅ Connects, subscribes, and persists normalized rows with `msg_id`, `published_at`, `received_at`.
* ✅ Dedup works across reconnects; no duplicate msg_ids in raw.
* ✅ Flushes occur on both size and time triggers.
* [ ] Curation enforces the **15:30 ET** cutoff downstream (pending preprocessing implementation).

## Implementation status (2025-11-11)

* **Module:** `src/orbit/ingest/news.py`
* **CLI:** `orbit ingest news [--symbols SPY VOO] [--duration N]`
* **Features implemented:**
  - WebSocket connection with authentication
  - Message normalization and validation
  - In-memory buffering with deduplication (by msg_id)
  - Flush policy: size-based (100 messages) and time-based (5 minutes)
  - Exponential backoff reconnection (up to 5 attempts)
  - Graceful shutdown with buffer flush on Ctrl+C
  - Multi-key support ready (reads ALPACA_API_KEY/SECRET from .env)
  - Statistics tracking (messages received/buffered/rejected, flushes)
* **Dependencies:** `websocket-client==1.8.0`
* **Data output:** `ORBIT_DATA_DIR/raw/news/date=YYYY-MM-DD/news.parquet`

---

## Related Files

* `04-data-sources/alpaca_news_ws.md` — Alpaca WebSocket spec
* `12-schemas/news.parquet.schema.md` — News data schema
* `06-preprocessing/deduplication_novelty.md` — Deduplication logic
* `10-operations/failure_modes_playbook.md` — WebSocket error handling
