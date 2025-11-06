# ORBIT — TOS & Compliance

*Last edited: 2025-11-05*

## Principles

* **Respect provider terms**; build adapters to evolve with policy.
* **Minimize data**: ingest only fields required for features.
* **No PII**: never store sensitive personal data; strip usernames where not needed.
* **Attribution**: retain `source` and `url` where terms require it.
* **User‑Agent**: set a descriptive identifier for all outbound requests.

## Source‑specific guidance

### Stooq

* Public CSV endpoints; no auth. Be polite: cache responses and avoid frequent re‑downloads.
* Do not scrape interactive pages; use official CSV download pattern.

### Alpaca Market Data — News

* Use official **WS** with auth; adhere to symbol subscription caps.
* Store original message `msg_id` + minimal payload for audit.
* Do not redistribute raw content beyond project needs.

### Reddit API

* Use official **OAuth**; follow subreddit rules and robots.
* Avoid storing full author profiles; keep only minimal `author_karma` and `account_age` if needed.
* Honor removals/DMCA: if an item is flagged removed, drop from curated datasets on next run.

### Gemini (optional)

* Send only necessary text spans; avoid PII.
* Respect model usage policies; do not submit content prohibited by the provider.
* Do not treat outputs as facts; they are annotations for downstream features.

## Data retention

* Keep **raw** ingests as append‑only with run IDs for audit (duration configurable).
* Allow a retention policy (e.g., purge raw after N days, keep curated/features longer).

## Security

* Secrets in environment vars only; never commit keys.
* Enforce TLS for all HTTP/WS connections.
* Log access only at aggregate level; avoid sensitive payloads in logs.

## Acceptance checks

* Each connector sets a proper `User-Agent` and honors provider limits.
* Raw data includes source attribution fields where applicable.
* There is a documented retention window and a purge task to enforce it.

---

## Related Files

* `04-data-sources/stooq_prices.md` — Stooq usage terms
* `04-data-sources/alpaca_news_ws.md` — Alpaca terms
* `04-data-sources/reddit_api.md` — Reddit API terms
* `03-config/env_keys.md` — User-Agent requirements
