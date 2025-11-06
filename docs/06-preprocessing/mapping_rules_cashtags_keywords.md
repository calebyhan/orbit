# ORBIT — Mapping Rules: Cashtags & Keywords

*Last edited: 2025-11-05*

## Purpose

Deterministically map **text items** (news headlines, Reddit posts) into the **index universe** (SPY/VOO/S&P 500) while suppressing false positives. Output a mapping record that downstream curation and features can consume.

## Scope

Applies to items inside the daily membership window `(T−1 15:30, T 15:30]` (ET). This module runs **after** time alignment and **before** daily aggregation.

## Inputs

* Text fields: `headline` (news) or `title + body` (social)
* Metadata: `symbols` (news provider tags), `subreddit` (social), `source`, `url`

## Normalization pipeline

1. Unicode **NFC** normalization.
2. Lowercase; collapse repeated whitespace and punctuation.
3. Replace fancy ampersands with `&`; standardize `S&P` variants.
4. Tokenize on word boundaries; keep `$` as a token for cashtags.

## Positive matches (regex)

* **Tickers**: `\bspy\b`, `\bvoo\b`
* **Cashtag**: `\$spy\b`
* **Index phrases**: `\bs&p\s*500\b`, `\bstandard\s*&\s*poor'?s\s*500\b`, `\bthe\s+market\b`, `\bbroad\s+market\b`
* **News symbols**: provider `symbols` contains `SPY` or `VOO`

> Implement regex with case‑insensitive flag and word/number boundaries. Maintain the patterns in a single rules file (e.g., `mapping_rules.yaml`).

## False‑positive blacklist (examples)

* `spy camera`, `spy gadget`, `spy balloon`, `spying`, `espionage`
* `voodoo`, `voo-doo`, `v\.o\.o\.`
* Entertainment or non‑finance sources (maintain allow/deny lists)

## Context gates (disambiguation)

Increase confidence only when **context tokens** appear within ±10 words of the match:

* Finance tokens: `stocks, stock, etf, index, indices, rally, selloff, drawdown, fed, rate, inflation, earnings, recession, portfolio`
* Venue tokens: `s&p, spx, nyse, nasdaq`
* For social: **subreddit weighting** — allowlist (`r/stocks`, `r/investing`) > neutral; down‑weight off‑topic subs.

## Co‑mentions heuristic

* If many **single‑name tickers** appear (≥3 distinct tickers excluding SPY/VOO), reduce **index** confidence unless index phrases present.

## Mapping algorithm (deterministic)

1. Initialize `confidence = 0` and `reasons = []`.
2. If provider `symbols` includes `SPY` or `VOO`: `confidence += 0.6`; add reason.
3. If regex match for **ticker/cashtag/index phrase**: `confidence += 0.4` (cap at 0.6 if phrase only); add reason.
4. If **context gate** hit: `confidence += 0.2`; add reason.
5. If **subreddit allowlist/source allowlist**: `confidence += 0.1`.
6. If **blacklist phrase** detected: `confidence -= 0.5`; add reason.
7. If **co‑mentions heuristic** triggers: `confidence -= 0.2`.
8. **Clip** `confidence` to `[0,1]`.
9. Emit mapping when `confidence ≥ θ_map` (default **0.5**). Otherwise mark `unmapped`.

## Output schema (mapping table)

For each item, append one row to `data/curated/mapping/` (or merge fields into curated text tables):

* `item_id: string` (e.g., `news_<msg_id>`, `reddit_<post_id>`)
* `universe_tag: string` ∈ {`INDEX`}
* `tickers: list[string]` ⊆ {`SPY`, `VOO`}
* `confidence: float` ∈ [0,1]
* `reasons: list[string]` (matched rules and gates)

## Tunables (config)

* `θ_map` (emit threshold): **0.5**
* `context_window`: **10** tokens
* `allowlist_subreddits`: `["stocks","investing","wallstreetbets"]`
* `allowlist_sources`: weight table for news providers
* `blacklist_phrases`: editable list (see `docs/04-data-sources/identifiers_mapping.md`)

## Examples

* **GOOD**: "$SPY rips after Fed hints at pause" → ticker + finance tokens → **map INDEX, confidence ≈ 0.9**
* **GOOD**: "S&P 500 breadth improves, VOO tracks higher" → index phrase + ETF mention → **map INDEX, ≈ 0.8**
* **REJECT**: "Best 4K spy camera deals" → blacklist hit → **confidence < 0**, unmapped
* **LOW**: "Market was wild today" (no finance tokens, off‑topic sub) → **confidence ≈ 0.3**, unmapped

## QC & monitoring

* **Precision sample**: randomly review 100 mapped items/week → precision ≥ **95%**.
* **Top reasons**: report reason counts; ensure blacklist works and allowlists dominate.
* **Drift**: track confidence histogram; watch for mode shift.

## Acceptance checklist

* Regex + gates produce mapping records with **≥95% precision** on a weekly sample.
* Confidence is clipped to [0,1] and thresholded at `θ_map`.
* Mapping fields (`item_id, universe_tag, tickers, confidence, reasons`) are present in curated outputs.

---

## Related Files

* `04-data-sources/identifiers_mapping.md` — Mapping specification
* `07-features/news_features.md` — News symbol filtering
* `07-features/social_features.md` — Social keyword matching
