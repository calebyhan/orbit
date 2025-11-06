# ORBIT — Environment Keys

*Last edited: 2025-11-05*

Set these as environment variables before running the pipeline. Never hardcode secrets into the repo.

## Alpaca News (WebSocket)

* `ALPACA_API_KEY_ID`
* `ALPACA_API_SECRET_KEY`

**Export examples** (PowerShell / bash):

```
$env:ALPACA_API_KEY_ID="..."; $env:ALPACA_API_SECRET_KEY="..."
export ALPACA_API_KEY_ID=... ALPACA_API_SECRET_KEY=...
```

## Reddit API (official OAuth)

* `REDDIT_CLIENT_ID`
* `REDDIT_CLIENT_SECRET`
* `REDDIT_USER_AGENT`  ← format: `ORBIT/1.0 by <email or site>`
* (optional for script flow) `REDDIT_USERNAME`, `REDDIT_PASSWORD`

**Notes**

* Prefer installed‑app OAuth with device or web flow. Use script creds only if required and within Reddit TOS.
* Throttle to avoid 429s. Respect subreddit rules.

## Gemini (sentiment analysis)

**Primary API key:**
* `GEMINI_API_KEY_1`

**Additional keys (optional, for multi-key rotation):**
* `GEMINI_API_KEY_2`
* `GEMINI_API_KEY_3`
* `GEMINI_API_KEY_4`
* `GEMINI_API_KEY_5`

**Usage:**
* Required for all sentiment analysis (news + social).
* Multi-key rotation enables higher throughput: up to 5 keys = 1,000 RPD (200 × 5).
* Configure rotation strategy in `orbit.yaml`: `sources.gemini.rotation_strategy: "round_robin"` or `"least_used"`.
* If only 1 key provided, system operates with single-key quota (200 RPD on free tier).

**Free tier limits (per key):**
* Model: Gemini 2.0 Flash-Lite
* 30 RPM, 1M TPM, 200 RPD
* Typical usage: ~50-80 items/day = 1-2 batch requests

**Export examples:**
```bash
export GEMINI_API_KEY_1="AIza..."
export GEMINI_API_KEY_2="AIza..."
export GEMINI_API_KEY_3="AIza..."
# Keys 4-5 optional
```

## General

* `ORBIT_USER_AGENT`  ← used for all HTTP requests when the source allows custom UA.
* (optional) `ORBIT_DATA_DIR` to override `paths.data_dir`.

## Acceptance checklist

* Secrets are set in the environment (not in git).
* User‑agent is descriptive and consistent with `docs/04-data-sources/tos_compliance.md`.
* Running `ingest:*` fails fast with a clear error if a required key is missing.

---

## Related Files

* `04-data-sources/alpaca_news_ws.md` — Alpaca API keys
* `04-data-sources/reddit_api.md` — Reddit OAuth
* `04-data-sources/gemini_sentiment_api.md` — Gemini API key
* `04-data-sources/tos_compliance.md` — User-Agent requirements
