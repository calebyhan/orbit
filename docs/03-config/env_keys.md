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

## Gemini (optional LLM escalation)

* `GEMINI_API_KEY`

**Usage**

* Only required if `sources.gemini.enabled: true` in config.

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
