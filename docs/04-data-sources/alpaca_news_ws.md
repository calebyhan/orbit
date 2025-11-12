# ORBIT — Alpaca News WebSocket

*Last edited: 2025-11-11*

## Purpose

Define how ORBIT consumes **real-time news** from Alpaca’s Market Data **News WebSocket** on the free Basic tier (≤30 subscribed symbols), normalizes messages, applies point-in-time cutoffs, and persists them for downstream features.

## Access & auth

* **Auth:** `ALPACA_API_KEY`, `ALPACA_API_SECRET` — WebSocket credentials (see `docs/03-config/env_keys.md`).
* **Note:** Historical backfill via REST API uses separate numbered keys (`ALPACA_API_KEY_1-5`) for rate limit isolation.
* **Endpoint:** `wss://stream.data.alpaca.markets/v1beta1/news` (subject to provider changes; keep configurable via `orbit.yaml`).
* **Symbols:** start with `["SPY", "VOO"]`. Basic tier cap ≈ **30** concurrent symbols; enforce via config.

## Subscription & lifecycle

1. **Connect** with auth headers → subscribe to configured symbols.
2. **Heartbeat**: monitor pings; if no messages for `X` seconds, send ping or reconnect.
3. **Reconnect policy**: exponential backoff (`initial_ms`, `factor`, `max_ms` per config) and **resume** from the last `published_at` seen (using REST backfill if available, else WS replay).
4. **Shutdown**: flush buffers and close gracefully on SIGINT/exception.

## Message normalization

Normalize each WS message into a row with fields (superset to cover minor schema changes):

* `msg_id: str` — provider’s unique id if present; else content hash
* `published_at: timestamp[ns, UTC]`
* `received_at: timestamp[ns, UTC]` — when our client got it
* `symbols: list[str]` — tickers the item is tagged with
* `headline: str`
* `summary: str | null`
* `source: str` — e.g., Benzinga, Dow Jones
* `url: str | null`
* `raw: json` — original payload for audit
* `run_id: str`

**Storage (raw lake):** append to `data/raw/news/` as partitioned Parquet (by `date=YYYY-MM-DD`).

## Dedup & integrity

* **Primary key**: `msg_id`; fallback to `sha1(headline + source + published_at)`.
* Drop duplicates; keep earliest `received_at`.
* Validate `published_at ≤ now()`; drop obvious clock-skew outliers.

## Cutoff & lags (point-in-time)

* For day *T*, **include only** items with `published_at (ET) ≤ 15:30` (see `docs/03-config/cutoffs_timezones.md`).
* During training, optionally drop items within **publish_lag_minutes** of the cutoff to avoid timestamp jitter.

## Preprocessing outputs (curated)

Emit one curated table per day at `data/curated/news/` with columns used by feature builders:

* `date: date`
* `count: int` — #unique news items by cutoff
* `count_z: float` — z-score vs 60-day history
* `novelty: float` — average cosine distance from prior 7d headlines (see `06-preprocessing/deduplication_novelty.md`)
* `sent_mean: float` — average headline sentiment (Gemini API)
* `sent_max: float` — maximum sentiment score
* `sent_weighted: float` — weighted by source reliability table
* `stance_bull_pct: float` — % of items with bull stance
* `stance_bear_pct: float` — % of items with bear stance
* `certainty_mean: float` — average certainty score
* `last_item_ts: timestamp[ns, UTC]` — latest `published_at` counted
* `run_id: str`

-**Sentiment processing:**
- All news items processed via **Gemini 2.5 Flash-Lite (gemini-2.5-flash-lite)** batch API
- Output: `sent_llm` in [-1, 1], `stance`, `certainty`
- Batch processing for cost efficiency (~30 items/day = 1-2 API calls)
- See `gemini_sentiment_api.md` for prompt/response schema

## Errors & retries

* 4xx/5xx or WS close → reconnect with backoff.
* Malformed payload → write to `data/rejects/news/` with error reason.
* If the WS is down for the day → curate with `count=0` and log outage; downstream gates will reduce text weight.

## QC checks

* Monotone, increasing `published_at` within a session after de-dupe.
* `count ≥ 0` and `count_z` finite; `novelty ∈ [0,1]`.
* No items beyond cutoff included in curated table.

## Acceptance checklist

* Connects and subscribes to configured symbols (≤30) and streams messages.
* Stores raw rows with `msg_id`, `published_at`, and `received_at`.
* Applies cutoff/lag and produces a curated daily aggregate with required fields.
* Handles reconnects and outages gracefully (logs + safe defaults).

---

## Related Files

* `05-ingestion/news_alpaca_ws_ingest.md` — News ingestion implementation
* `12-schemas/news.parquet.schema.md` — News data schema
* `03-config/env_keys.md` — API key configuration
* `03-config/cutoffs_timezones.md` — 15:30 ET cutoff rules
* `04-data-sources/rate_limits.md` — WebSocket reconnection policies
* `06-preprocessing/deduplication_novelty.md` — Novelty scoring
* `07-features/news_features.md` — News-based features
