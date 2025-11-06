# ORBIT — Quality Filters (Social)

*Last edited: 2025-11-05*

## Purpose

Screen Reddit posts/comments for **spam/bots/low‑quality** signals before aggregation and sentiment so intensity metrics and stance estimates are reliable.

## Scope

Applies to social items within the daily membership window `(T−1 15:30, T 15:30]` (ET) after time alignment and before mapping, dedup, and sentiment.

## Inputs

* `data/raw/social/` rows with: `created_utc, subreddit, author, author_karma, title, body, score, num_comments, permalink`.
* Config thresholds from `docs/03-config/sample_config.yaml` (mirrored in `orbit.yaml`).

## Outputs

* **Curated flags** appended to per‑item rows:

  * `is_bot: bool`
  * `is_low_cred: bool`
  * `is_nsfw_or_removed: bool`
  * `is_non_english: bool`
  * `is_url_spam: bool`
  * `is_near_duplicate: bool` *(from dedupe stage; echoed here for convenience)*
  * `quality_score: float` in [0,1]
  * `keep: bool` (true if passes filters)
* **Daily aggregates** (used later in features): post counts after filtering, credibility‑weighted sentiment components, comment velocity.

## Filters (deterministic)

### 1) Account credibility

* **Min karma:** `author_karma ≥ min_author_karma` (default **50**)
* **Min account age:** `account_age_days ≥ min_account_age_days` (default **30**)
* **AutoModerator & known bots:** `author in {AutoModerator}` or `username` matches `(bot|auto|newsfeed)` → `is_bot=True`

### 2) Content validity

* **Removed/deleted/NSFW:** drop if marked removed, deleted, or NSFW where indicated by API.
* **Language:** fast LID (e.g., fastText) → require `lang == 'en'` (set `is_non_english=True` otherwise).
* **Length:** require `len(title + body) ≥ 25` characters after URL stripping.
* **Repetition:** collapse repeated characters; flag if >20% of characters are a single repeating token.

### 3) URL spam & domains

* If `#urls ≥ 2` and domains not in allowlist (news/broker/reputable finance), set `is_url_spam=True` and **down‑weight** (do not auto‑drop unless also low‑cred).

### 4) Engagement anomalies (down‑weight; do not drop)

* If `score < 0` and `num_comments == 0`, reduce `quality_score` but keep item (prevents bias).

## Keep/drop rule

An item is **kept** if all are true:

* Not `is_bot`, not `is_nsfw_or_removed`, and `author` passes min karma/age **OR** item has strong organic engagement (`score ≥ 5` and `num_comments ≥ 3`).
* Not `is_non_english`.

Otherwise mark `keep=False` and exclude from counts and sentiment aggregates (still stored in raw with flags).

## Quality score (for weighting, not gating)

```
quality_score = base * cred * url * engage
where:
  base = 1 if keep else 0
  cred = min(1.0, log10(karma+1)/4 + account_age_days/365*0.1)
  url  = 0.7 if is_url_spam else 1.0
  engage = sqrt(max(score,0)+1) / sqrt(max_score_bucket)
clip to [0,1]
```

Use `quality_score` as a multiplier in **credibility‑weighted sentiment** and in **comment_velocity** weighting.

## Integration with downstream steps

* **Mapping**: run mapping after quality filtering; unmapped items are ignored for index features.
* **Dedup/novelty**: applied regardless; duplicates are removed from counts.
* **Sentiment**: compute tier‑1 sentiment only on `keep=True` items; `quality_score` is the weight when aggregating.

## Pseudocode

```python
row['is_bot'] = row.author in BOT_LIST or regex_bot(row.author)
row['is_low_cred'] = (row.author_karma or 0) < cfg.sources.reddit.min_author_karma or \
                     (row.account_age_days or 0) < cfg.sources.reddit.min_account_age_days
row['is_nsfw_or_removed'] = row.removed or row.deleted or row.nsfw
row['is_non_english'] = detect_lang(row.title + ' ' + (row.body or '')) != 'en'
row['is_url_spam'] = url_count(row.body) >= 2 and not domains_allowlisted(row.body)

keep = (not row['is_bot']) and (not row['is_nsfw_or_removed']) and \
       (not row['is_non_english']) and \
       ((not row['is_low_cred']) or (row.score >= 5 and row.num_comments >= 3))

row['keep'] = keep
row['quality_score'] = quality(row, cfg)
```

## QC & logging

* Record counts by flag type and overall keep‑rate per day.
* Track distribution of `quality_score`; alert if median drifts sharply week‑over‑week.
* Sample review top 50 kept/dropped borderline items weekly.

## Acceptance checklist

* Items failing explicit rules (bot, removed, NSFW, non‑English) are dropped from aggregates.
* `quality_score` is bounded [0,1] and used for **credibility‑weighted sentiment**.
* Daily reports include keep/drop counts and rationale tallies.

---

## Related Files

* `04-data-sources/reddit_api.md` — Quality criteria
* `05-ingestion/social_reddit_ingest.md` — Filter application
* `07-features/social_features.md` — Credibility weighting
