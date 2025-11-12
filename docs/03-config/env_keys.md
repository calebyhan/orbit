# ORBIT — Environment Keys

*Last edited: 2025-11-11*

## Easy Setup: Using .env File (Recommended)

**ORBIT automatically loads environment variables from a `.env` file** - no need to manually export!

```bash
# One-time setup
cp .env.example .env
# Edit .env with your keys
```

Your `.env` file:
```bash
# Alpaca WebSocket (real-time news)
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_API_SECRET=your_alpaca_api_secret

# Alpaca REST API (historical backfill)
ALPACA_API_KEY_1=your_alpaca_key_1
ALPACA_API_SECRET_1=your_alpaca_secret_1
# Optional: Add keys 2-5 for faster backfill

# Reddit
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=ORBIT/1.0 by you@example.com

# Gemini (up to 5 keys for rotation)
GEMINI_API_KEY_1=AIza...
GEMINI_API_KEY_2=AIza...  # optional
GEMINI_API_KEY_3=AIza...  # optional

# Data directory (IMPORTANT for production)
ORBIT_DATA_DIR=/srv/orbit/data
```

**That's it!** Just run ORBIT commands and the `.env` is automatically loaded.

---

## Alternative: Manual Export

If you prefer not to use `.env`, you can manually export environment variables:

Set these as environment variables before running the pipeline. Never hardcode secrets into the repo.

## Alpaca News (WebSocket and REST API)

**WebSocket (real-time streaming):**
* `ALPACA_API_KEY` — Used by `orbit ingest news`
* `ALPACA_API_SECRET`

**REST API (historical backfill):**
* `ALPACA_API_KEY_1` — Used by `orbit ingest news-backfill`
* `ALPACA_API_SECRET_1`
* `ALPACA_API_KEY_2` through `ALPACA_API_KEY_5` (optional, for multi-key rotation)
* `ALPACA_API_SECRET_2` through `ALPACA_API_SECRET_5`

**Separation rationale:**
- WebSocket connection is long-lived and uses a dedicated key
- REST API for historical data can use multiple keys for 5x throughput (~1,000 RPM combined)
- You can use the same key for both, or separate keys to isolate rate limits

**Export examples** (PowerShell / bash):

```
# WebSocket (required for real-time)
export ALPACA_API_KEY="..." ALPACA_API_SECRET="..."

# REST API (required for historical backfill)
export ALPACA_API_KEY_1="..." ALPACA_API_SECRET_1="..."

# Optional: Add more REST keys for faster backfill (5x throughput)
export ALPACA_API_KEY_2="..." ALPACA_API_SECRET_2="..."
export ALPACA_API_KEY_3="..." ALPACA_API_SECRET_3="..."
export ALPACA_API_KEY_4="..." ALPACA_API_SECRET_4="..."
export ALPACA_API_KEY_5="..." ALPACA_API_SECRET_5="..."
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
* Model: Gemini 2.5 Flash-Lite (gemini-2.5-flash-lite)
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
* `ORBIT_DATA_DIR` ← **IMPORTANT:** Path to production data (set to `/srv/orbit/data` for production)
* (optional) `ORBIT_CONFIG_PATH` to override config file location.
* (optional) `ORBIT_LOG_LEVEL` to set logging verbosity (default: INFO)

## Acceptance checklist

* Secrets are set in `.env` or environment (not in git).
* `.env` file is listed in `.gitignore` (already configured).
* `ORBIT_DATA_DIR=/srv/orbit/data` is set for production runs.
* User‑agent is descriptive and consistent with `docs/04-data-sources/tos_compliance.md`.
* Running `ingest:*` fails fast with a clear error if a required key is missing.

---

## Related Files

* `04-data-sources/alpaca_news_ws.md` — Alpaca API keys
* `04-data-sources/reddit_api.md` — Reddit OAuth
* `04-data-sources/gemini_sentiment_api.md` — Gemini API key
* `04-data-sources/tos_compliance.md` — User-Agent requirements
