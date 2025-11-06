# ORBIT — Identifiers & Mapping Rules

*Last edited: 2025-11-05*

## Purpose

Define **string/regex rules** to map social/news items to the **index universe** (SPY/VOO/S&P 500) and to suppress common false positives.

## Core universe

* **Tickers**: `SPY`, `VOO`
* **Index terms**: `S&P 500`, `S&P`, `the market`, `broad market`
* **Cashtags**: `$SPY`

## Normalization

* Case‑insensitive matching
* Token boundaries (word/whitespace/punctuation) to avoid substrings (e.g., `"spyglass"`)
* Unicode normalization (NFC) before matching

## Positive patterns (examples)

* `\bSPY\b` , `\bVOO\b` , `\bS&P\s*500\b`
* `\bS\&P\s*500\b` (escaped ampersand)
* Cashtag: `\$SPY\b`
* Phrases: `\b(the\s+market|broad\s+market)\b`

## Blacklist / false positives

* `spy camera`, `spy gadget`, `spy balloon` (non‑financial contexts)
* `voodoo` / `voo doo` / `v\.o\.o\.` (phonetic/abbrev confounds)
* `espionage`, `spying` (non‑ticker usage)

## Heuristics

* **Context gate**: require at least one financial token near the match within ±10 words: `{stocks, etf, index, rally, selloff, fed, rates, earnings}`
* **Subreddit gate**: weight r/stocks, r/investing higher; down‑weight off‑topic subs even if a match appears.
* **Source gate (news)**: prefer items with `symbols` including `SPY` or clear index phrasing.

## Mapping output schema

For each item, emit a mapping record:

* `item_id: str` (e.g., `reddit_<post_id>` or `news_<msg_id>`)
* `universe_tag: str` in {`INDEX`} (future: single‑names)
* `tickers: list[str]` (subset of {`SPY`, `VOO`})
* `confidence: float` in [0,1]
* `reasons: list[str]` (matched rules)

### Confidence scoring (example)

* +0.6 if regex hit on ticker/cashtag
* +0.2 if context gate hit
* +0.1 if source/subreddit in allowlist
* −0.3 if blacklist phrase present
* Clip to [0,1]

## Maintenance

* Keep rules in a single YAML (`mapping_rules.yaml`) or code map.
* Log **top false‑positives** weekly and propose rule updates.

## Acceptance checks

* ≥95% of sampled mapped items are relevant to the index.
* Blacklist eliminates obvious non‑financial matches without suppressing valid finance posts.
* Confidence distribution is bimodal (many highs, many lows) enabling clean thresholds.

---

## Related Files

* `06-preprocessing/mapping_rules_cashtags_keywords.md` — Mapping rule implementation
* `04-data-sources/alpaca_news_ws.md` — News symbol mapping
* `04-data-sources/reddit_api.md` — Social keyword matching
