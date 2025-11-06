# ORBIT — Dataflow: Prices, News, Social

*Last edited: 2025-11-06*

## Overview

Defines the end‑to‑end dataflow for each modality from **source → ingest → preprocess → curated → features** and the time rules that guarantee point‑in‑time correctness.

---

## 1) Prices (Stooq)

**Goal:** produce daily price features for SPY/VOO and benchmark (^SPX).

### Source

* **Stooq CSV** per symbol: `SPY.US`, `VOO.US`, `^SPX`.
* Columns: `Date, Open, High, Low, Close, Volume`.

### Ingest job: `ingest:prices`

* **When:** once after market close (T).
* **Action:** download CSV → normalize → append to `data/raw/prices/` as Parquet (`symbol=..., date=...`).
* **Fields:** `date (YYYY-MM-DD)`, `symbol (str)`, `open, high, low, close (float)`, `volume (int)`, `run_id (uuid)`, `ingested_at (ts)`.
* **Checks:** row count ≥ previous day; dates strictly increasing per symbol.

### Preprocess

**Price preprocessing is minimal** — no cutoff enforcement needed since EOD prices are naturally point-in-time safe:

* Align to **America/New_York** timezone; validate trading days via calendar.
* Compute returns: `ret_1d`, `ret_5d`, rolling measures (`rv_10d`, drawdown), ETF–index basis: `ret_spy - ret_spx`.
* Output table: `data/curated/prices/` (direct pass-through after validation and feature calculation).

**No cutoff filtering:** Unlike text modalities (news/social), price data at market close (4:00 PM ET) is **already** point-in-time safe — T's closing price cannot leak T+1 information. The cutoff discipline (15:30 ET) applies **only** to text data that may contain forward-looking signals if captured too late in the day.

### Features contribution

* Price feature set (see `docs/07-features/price_features.md`).

---

## 2) News (Alpaca News WebSocket)

**Goal:** quantify **intensity, novelty, sentiment** of index‑relevant headlines.

### Source

* **Alpaca Market Data — News WS**; subscribe to `SPY`, `VOO` (≤30 symbols on free tier).
* Message fields (normalized): `published_at (ts)`, `symbols [list]`, `headline (str)`, `summary/body (opt)`, `source (str)`, `url (str)`, `msg_id (str)`.

### Ingest job: `ingest:news`

* **When:** continuous during session on day T.
* **Action:** connect WS → upsert by `msg_id`; store to `data/raw/news/` (Parquet). Maintain `last_seen_ts` for resume.
* **Checks:** monotone `published_at`; dedupe by content hash.

### Preprocess

* **Cutoff:** include only items with `published_at ≤ 15:30 ET` on day T.
* **Lag rule (training):** optional +15–30 min publish lag window.
* **Dedup/novelty:** cluster near‑duplicates; compute novelty vs prior 7 days.
* **Sentiment:** VADER/FinBERT on `headline` (store `sent_mean`, `sent_max`).
* Output table: `data/curated/news/` with: `date, count, count_z, novelty, sent_mean, sent_max, source_weighted_mean`.

### Features contribution

* News feature set (see `docs/07-features/news_features.md`).

---

## 3) Social (Reddit API + optional Gemini escalation)

**Goal:** capture retail **buzz** and **stance** around the market (SPY/VOO/S&P 500).

### Source

* **Reddit API** queries across `r/stocks`, `r/investing`, `r/wallstreetbets` with keywords: `"SPY"`, `"VOO"`, `"S&P 500"`, `"market"` (with blacklist rules).

### Ingest job: `ingest:social`

* **When:** periodic batches during T (respect API rate limits).
* **Action:** fetch posts + comments → normalize to `data/raw/social/`.
* Fields: `created_utc (ts)`, `subreddit`, `author`, `author_karma (int)`, `title`, `body`, `permalink`, `post_id`, `matched_terms [list]`.
* **Checks:** dedupe by `post_id`/hash; filter bots/low‑cred authors.

### Preprocess

* **Cutoff:** include only posts with `created_utc ≤ 15:30 ET` on day T.
* **Sentiment tier‑1:** VADER/FinBERT for cheap scores; label **uncertain** cases (|score| < τ or classifier disagreement).
* **LLM escalation (optional):** batch only uncertain/high‑impact posts to Gemini; store JSON response (`sent_llm [-1..1]`, `stance {bull,bear,neutral}`, `sarcasm bool`, `certainty [0..1]`).
* **Aggregate:** counts, `post_count_z` vs 60‑day, `comment_velocity`, credibility‑weighted sentiment.
* Output table: `data/curated/social/` with daily aggregates.

### Features contribution

* Social feature set (see `docs/07-features/social_features.md`).

---

## 4) Feature row assembly

Job: `features:build` → join `curated/prices`, `curated/news`, `curated/social` by date to produce **one row per day**:

* Keys: `date`.
* Columns (examples): `mom_5d, mom_20d, rev_1d, rv_10d, drawdown, basis_etf_index, news_count_z, news_novelty, news_sent_mean, social_post_count_z, social_cred_sent, social_novelty, gates_inputs...`
* Standardize selected columns to rolling z‑scores (see `standardization_scaling.md`).
* Emit to: `data/features/features_daily.parquet`.

## 5) Labels

* **Classification:** `y_updown = 1{ret_{t+1} > 0}` (or excess).
* **Regression:** `y_ret = ret_{t+1}` (or excess vs ^SPX).
* Stored alongside features with clear suffixes: `label_updown`, `label_ret`.

## Acceptance checklist

* Each modality has: **source → ingest → preprocess → curated → features** defined.
* Cutoff ≤ **15:30 ET** and lag rules stated.
* Output schemas list required fields for joins.
* Feature assembly & labeling locations are unambiguous.

---

## Related Files

* `02-architecture/system_diagram.md` — System overview
* `05-ingestion/storage_layout_parquet.md` — Data storage structure
* `12-schemas/*.md` — Data schemas
