# ORBIT — Arctic Shift Photon Reddit API (Social)

*Last edited: 2025-11-15*

## Purpose

Document the **Arctic Shift Photon Reddit API** as an alternative to the official Reddit API for historical and recent Reddit data ingestion. This is a third-party archive service that provides historical Reddit posts via a simple REST API.

---

## Why Arctic Shift Instead of Official Reddit API?

**Advantages:**
- ✅ **No OAuth required** - Simple HTTP GET requests
- ✅ **Historical data** - Access to posts from 2020+ (tested back to Dec 2019)
- ✅ **Free tier** - No API key required (as of 2025-11-15)
- ✅ **Simple pagination** - Time-based queries using `after`/`before` parameters
- ✅ **No rate limit headers observed** - Appears to be more permissive than official API

**Disadvantages:**
- ❌ **Unofficial** - Not maintained by Reddit; may change or disappear
- ❌ **No real-time** - Archive-based, not suitable for streaming
- ❌ **Limited to 25-40 results per query** - Smaller pagination limit than official API
- ❌ **Single subreddit per query** - Cannot combine subreddits (400 error)
- ❌ **Removed content** - Many posts show `[removed]` for content moderation
- ❌ **Unknown SLA** - No official documentation or uptime guarantee

**Decision:** Use Arctic Shift for **historical backfill** (2015-present) and **official Reddit API** for real-time/daily ingestion once available.

---

## API Endpoint

```
https://arctic-shift.photon-reddit.com/api/posts/search
```

---

## Query Parameters

### Required

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `subreddit` | string | Single subreddit name (without r/) | `stocks` |

### Optional

| Parameter | Type | Description | Default | Notes |
|-----------|------|-------------|---------|-------|
| `after` | ISO 8601 | Start time (inclusive) | - | Format: `2024-01-01T00:00` |
| `before` | ISO 8601 | End time (exclusive) | - | Format: `2024-01-31T23:59` |
| `limit` | int | Max results per request | 25 | API caps at ~25-40 regardless of parameter |
| `sort` | string | Sort order | `desc` | `asc` or `desc` |
| `md2html` | bool | Convert markdown to HTML | `false` | Set to `true` for rendered HTML |
| `meta-app` | string | App identifier | - | Optional, e.g., `search-tool` |

### Testing Results

**Limit parameter:**
- Requested `limit=100` → returned 25 posts
- Requested `limit=50` → returned 25 posts
- Requested `limit=10` → returned 10 posts
- Requested `limit=5` → returned 5 posts
- **Conclusion**: API respects small limits (≤25) but caps at 25-40 for larger requests

**Date ranges:**
- `after=2020-01-01&before=2020-01-31` → Returns 40 posts from that range
- `after=2020-01-01` (no before) → Returns recent posts after that date
- Historical data confirmed back to **December 2019**

**Multiple subreddits:**
- `subreddit=stocks,investing,wallstreetbets` → **400 Bad Request**
- **Conclusion**: Must query one subreddit at a time

---

## Response Structure

### Top-Level Object

```json
{
  "data": [
    {
      "id": "abc123",
      "name": "t3_abc123",
      "created_utc": 1577836976,
      "retrieved_on": 1586941635,
      "author": "username",
      "subreddit": "stocks",
      "title": "Post title here",
      "selftext": "Post body here (or [removed])",
      "permalink": "/r/stocks/comments/abc123/post_title/",
      "url": "https://...",
      "score": 42,
      "ups": 42,
      "upvote_ratio": 0.89,
      "num_comments": 15,
      "link_flair_text": "Discussion",
      "removed_by_category": "moderator",
      "archived": false,
      "locked": false,
      "hide_score": false,
      "spoiler": false,
      "over_18": false,
      "is_video": false,
      "gilded": 0,
      "all_awardings": [],
      "total_awards_received": 0,
      "distinguished": null,
      "mod_reports": [],
      "user_reports": []
    }
  ]
}
```

### Key Fields for ORBIT

| Field | Type | ORBIT Usage |
|-------|------|-------------|
| `id` | string | Deduplication key |
| `created_utc` | int (Unix timestamp) | Post timestamp (convert to UTC) |
| `author` | string | Author username (for quality filtering) |
| `subreddit` | string | Source subreddit |
| `title` | string | Main text content (sentiment input) |
| `selftext` | string | Body content (or `[removed]`) |
| `score` | int | Upvotes (engagement metric) |
| `num_comments` | int | Comment count (engagement metric) |
| `permalink` | string | Reddit URL |
| `removed_by_category` | string/null | Filter removed posts (`"moderator"`, `"deleted"`, etc.) |

### Fields to Ignore/Drop

- `link_flair_background_color`, `all_awardings`, `total_awards_received` - UI/display metadata
- `mod_reports`, `user_reports` - Moderation data (not useful for sentiment)
- `retrieved_on` - Archive timestamp (not creation time)
- `url` - External link (if different from Reddit permalink)

---

## Pagination Strategy

### Problem: No Explicit Pagination Tokens

The API does not return:
- `next` or `after` tokens
- Total count
- Page indicators

### Solution: Time-Based Iteration

Use the **earliest `created_utc`** from current results as the `before` parameter for the next query:

```python
# Pseudo-code
current_after = "2024-01-01T00:00"
current_before = "2024-01-31T23:59"

while current_after < current_before:
    response = fetch(subreddit, after=current_after, before=current_before, limit=25)
    posts = response["data"]

    if not posts:
        break  # No more data

    # Process posts
    store_posts(posts)

    # Update after to earliest created_utc from this batch
    earliest_timestamp = min(post["created_utc"] for post in posts)
    current_after = datetime.fromtimestamp(earliest_timestamp, tz=UTC).isoformat()

    # Rate limiting (conservative)
    time.sleep(1)  # 1 second between requests
```

**Alternative: Day-by-Day Iteration**

More reliable for ensuring complete coverage:

```python
start_date = datetime(2015, 1, 1)
end_date = datetime.now()

for single_date in pd.date_range(start_date, end_date, freq="D"):
    after = single_date.strftime("%Y-%m-%dT00:00")
    before = (single_date + timedelta(days=1)).strftime("%Y-%m-%dT00:00")

    posts = []
    while True:
        response = fetch(subreddit, after=after, before=before, limit=25)
        batch = response["data"]

        if not batch:
            break

        posts.extend(batch)

        # Check if we got fewer than max (indicates end of data)
        if len(batch) < 25:
            break

        # Update after for pagination within the day
        earliest = min(post["created_utc"] for post in batch)
        after = datetime.fromtimestamp(earliest, tz=UTC).isoformat()

    # Save posts for this day
    save_to_parquet(posts, f"data/raw/social/date={single_date.date()}/social.parquet")

    time.sleep(1)  # Conservative rate limiting
```

---

## Rate Limits

### Empirical Testing Results (2025-11-15)

**Comprehensive rate limit testing performed** with the following results:

| Target Rate | Actual Rate | Requests | Errors | Status |
|-------------|-------------|----------|--------|--------|
| 1.0 req/s   | 0.83 req/s  | 30       | 0      | ✓ OK   |
| 2.0 req/s   | 1.46 req/s  | 60       | 0      | ✓ OK   |
| 5.0 req/s   | 2.64 req/s  | 150      | 0      | ✓ OK   |
| 10.0 req/s  | 3.61 req/s  | 300      | 0      | ✓ OK   |
| 20.0 req/s  | 4.42 req/s  | 400      | 0      | ✓ OK   |

**Key findings:**
- ✅ **No 429 errors** encountered across all test rates
- ✅ **No X-RateLimit headers** observed
- ✅ **Maximum tested rate**: 4.42 requests/second (sustained for 400 requests)
- ⚠️ **Network latency bottleneck**: Average response time ~170ms limits practical throughput to ~4.5 req/s

**Bottleneck analysis:**
- Target 20 req/s → Actual 4.42 req/s
- Limiting factor: Response time (~170ms/request)
- API appears **very permissive** with rate limits

**Recommended strategy:**
- **Default rate**: **3.5 requests/second** (80% of observed max for safety margin)
- **Exponential backoff** on any errors (429, 500, 503)
- **Monitor for 429 errors** - rate limits may be introduced in future
- **Configurable rate** - allow users to adjust based on observed performance

### Estimated Timeline for Historical Backfill

**Assumptions:**
- 3 subreddits: `r/stocks`, `r/investing`, `r/wallstreetbets`
- 10 years of history: 2015-2025
- ~365 days/year × 10 years = 3,650 days
- ~3 requests/day/subreddit (pagination)
- Total requests: 3,650 days × 3 subreddits × 3 requests/day = **~32,850 requests**

**Timeline with 3.5 req/second** (recommended):
- 32,850 requests ÷ (3.5 × 3,600) requests/hour = **~2.6 hours**

**Timeline comparison:**
| Rate       | Total Time | Speedup |
|------------|------------|---------|
| 1.0 req/s  | 9.1 hours  | 1.0x    |
| 3.5 req/s  | 2.6 hours  | 3.5x    |
| 4.4 req/s  | 2.1 hours  | 4.3x    |

**Recommendation**: Use **3.5 req/s** as default for reliability with good performance (**2.6 hour backfill**).

---

## Data Quality Issues

### Removed Content

**Problem**: Many posts have `selftext: "[removed]"` with `removed_by_category: "moderator"`

**Impact:**
- Cannot extract sentiment from removed posts
- Only `title` remains for analysis

**Mitigation:**
1. **Filter removed posts** - Drop posts where `selftext == "[removed]"` AND `removed_by_category != null`
2. **Title-only sentiment** - Score sentiment using `title` alone for removed posts
3. **Log removal rate** - Track % of removed posts per subreddit/day

### Hide Score

**Problem**: Some posts have `hide_score: true`

**Impact:**
- `score` and `ups` may be 0 or incorrect during initial hours

**Mitigation:**
- Historical data should have final scores (hide_score is temporary)
- For recent data, re-query after 24h to get final scores

---

## Compliance & TOS

### Arctic Shift Terms

**Unknown** - Arctic Shift does not provide official TOS documentation (as of 2025-11-15).

**Best practices:**
- Attribute data source in documentation
- Do not redistribute raw data
- Use for research/personal projects only
- Monitor for any takedown requests

### Reddit Content Policy

Even though using a third-party archive:
- **Respect Reddit's Content Policy**: https://www.redditinc.com/policies/content-policy
- **No PII**: Do not store user emails, IP addresses, or personal data
- **Attribution**: Credit Reddit as content source
- **Deleted content**: Respect user deletions (filter `removed_by_category`)

---

## Integration Plan for ORBIT

### Phase 1: Historical Backfill (M1)

**Goal**: Fetch 10 years of Reddit posts from `r/stocks`, `r/investing`, `r/wallstreetbets`

**Implementation:**
1. Create `src/orbit/ingest/social_arctic.py`
   - Day-by-day iteration (2015-01-01 → present)
   - Conservative rate limiting (1 req/sec)
   - Checkpoint/resume system (similar to news backfill)
   - Progress bar with tqdm

2. CLI command: `orbit ingest social-backfill`
   ```bash
   orbit ingest social-backfill \
     --start 2015-01-01 \
     --end 2025-11-15 \
     --subreddits stocks investing wallstreetbets
   ```

3. Output: `data/raw/social/date=YYYY-MM-DD/social.parquet`

**Timeline**: ~9 hours for 10 years (single-threaded, 1 req/sec)

---

### Phase 2: Daily Updates (M1)

**Goal**: Fetch yesterday's posts daily

**Implementation:**
1. Extend `social_arctic.py` with daily mode
2. CLI command: `orbit ingest social --daily`
3. Cron job: Run after market close (e.g., 17:00 ET)

**Timeline**: ~30 seconds per subreddit per day

---

### Phase 3: Real-Time Ingestion (M2+)

**Goal**: Switch to official Reddit API for real-time posts

**Why:**
- Arctic Shift is archive-based (delays of hours/days)
- Official API has streaming capabilities
- Better for production use

**Implementation:**
- Create `src/orbit/ingest/social_reddit.py` (official API)
- OAuth2 authentication (see existing `reddit_api.md` spec)
- Streaming mode similar to Alpaca news WebSocket

---

## Schema Mapping (Arctic API → ORBIT)

| Arctic Field | ORBIT Field | Type | Transformation |
|--------------|-------------|------|----------------|
| `id` | `post_id` | string | Direct mapping |
| `created_utc` | `created_utc` | timestamp[ns, UTC] | `pd.to_datetime(x, unit='s', utc=True)` |
| - | `received_at` | timestamp[ns, UTC] | `pd.Timestamp.now(tz='UTC')` |
| `subreddit` | `subreddit` | string | Direct mapping |
| `author` | `author` | string/null | Direct mapping |
| - | `author_karma` | int/null | Not available from Arctic (set to null) |
| `title` | `title` | string | Direct mapping |
| `selftext` | `body` | string/null | Direct mapping (null if `[removed]`) |
| `score` | `score` | int | Direct mapping |
| `num_comments` | `num_comments` | int | Direct mapping |
| `permalink` | `permalink` | string | Direct mapping |
| - | `matched_terms` | list[string] | Extract from title+body (see below) |
| *entire object* | `raw` | json | `json.dumps(post)` |
| - | `run_id` | string | Generate: `f"{date}_{timestamp}_backfill"` |

### Term Matching Logic

Extract matched terms for SPY/VOO/S&P 500:

```python
def extract_matched_terms(title: str, body: str) -> list[str]:
    """Extract market-related terms from post text."""
    text = f"{title} {body}".lower()

    terms = []
    if "spy" in text and not any(x in text for x in ["spy camera", "spying", "i spy"]):
        terms.append("SPY")
    if "voo" in text:
        terms.append("VOO")
    if "s&p 500" in text or "s&p500" in text or "sp500" in text:
        terms.append("S&P 500")
    if "s&p" in text and not any(x in text for x in ["s&p global", "s&p ratings"]):
        terms.append("S&P")
    if "market" in text and not any(x in text for x in ["supermarket", "marketplace"]):
        terms.append("market")

    return terms if terms else ["off-topic"]
```

---

## Acceptance Checklist (Arctic API Integration)

**Deliverables:**
- [ ] `src/orbit/ingest/social_arctic.py` - Arctic API client with pagination
- [ ] `orbit ingest social-backfill` CLI command
- [ ] Checkpoint/resume system for interrupted backfills
- [ ] Rate limiting (1 req/sec, exponential backoff on errors)
- [ ] Progress bar and statistics (articles, requests, elapsed time)
- [ ] Output to `data/raw/social/date=YYYY-MM-DD/social.parquet`
- [ ] Schema validation against `docs/12-schemas/social.parquet.schema.md`
- [ ] Filter removed posts (log removal rate)
- [ ] Term matching for SPY/VOO/S&P 500
- [ ] Unit tests (mocked API responses)
- [ ] Integration test (fetch 1 day of data)

**Acceptance criteria:**
- [ ] Can fetch 10 years of historical data from 3 subreddits (~9 hours)
- [ ] Checkpoint system allows resume from interruption
- [ ] Parquet files validate against schema
- [ ] Removed posts filtered or flagged
- [ ] No rate limit errors (429) during backfill
- [ ] Logs show: total posts, removal rate, matched terms distribution

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Arctic API disappears | Medium | High | Switch to official Reddit API (already spec'd in `reddit_api.md`) |
| Rate limiting introduced | Medium | Medium | Checkpoint system allows pause/resume; slow down to 0.5 req/sec |
| High removal rate (>50%) | High | Medium | Use title-only sentiment; document limitations |
| API response schema changes | Low | Medium | Schema validation catches issues early; fallback to raw JSON |
| Historical data gaps | Low | Low | Log missing dates; acceptable for research use |

---

## Related Files

- `docs/04-data-sources/reddit_api.md` - Official Reddit API spec (future migration)
- `docs/05-ingestion/social_reddit_ingest.md` - Social ingestion implementation spec
- `docs/12-schemas/social.parquet.schema.md` - Social data schema
- `docs/03-config/env_keys.md` - API credentials (none needed for Arctic)
- `docs/04-data-sources/rate_limits.md` - Rate limit strategies
- `docs/06-preprocessing/quality_filters_social.md` - Quality filters
- `docs/11-roadmap/milestones.md` - M1 deliverables tracker

---

## References

**Arctic Shift Photon Reddit API:**
- Base URL: https://arctic-shift.photon-reddit.com/
- Endpoint: `/api/posts/search`
- Documentation: None (unofficial API, reverse-engineered)
- Status: Operational as of 2025-11-15

**Reddit Official API** (for future migration):
- Documentation: https://www.reddit.com/dev/api/
- Rate limits: 60 requests/minute (OAuth2)
- Real-time: Yes (streaming via WebSocket)
