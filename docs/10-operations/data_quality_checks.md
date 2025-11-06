
*Last edited: 2025-11-05*

## Purpose

Define **automated validation rules** for ingested data (prices, news, social) and engineered features. These checks run after each ingestion step to catch errors early and prevent bad data from poisoning models.

---

## Philosophy

* **Fail fast:** Catch errors at ingestion, not at training
* **Explicit thresholds:** No silent warnings; block pipeline if critical check fails
* **Audit trail:** Log all checks with pass/fail status
* **Automated:** No manual review required for routine checks

---

## Check Levels

### Level 0: Schema Validation (Critical)

**Must pass** before writing to Parquet:

* [ ] Column names match schema (see `12-schemas/*.md`)
* [ ] Column dtypes match schema (e.g., `date` is `date`, not `str`)
* [ ] Required columns present (no missing columns)
* [ ] No unexpected columns (warn if extra columns present)

**Enforcement:** **BLOCK** write if schema invalid; raise `SchemaValidationError`

---

### Level 1: Completeness (Critical)

**Must pass** before downstream processing:

#### Prices

* [ ] All configured symbols present (SPY, VOO, ^SPX)
* [ ] OHLCV columns have no NaN
* [ ] At least 1 row per trading day

**Threshold:** ≥95% of expected trading days in rolling 90-day window

**Enforcement:** **BLOCK** feature engineering if <95%; log gap days

---

#### News

* [ ] At least 1 news item on ≥80% of trading days
* [ ] `published_at` timestamp present for all rows
* [ ] `headline` field non-empty for all rows
* [ ] At least 1 symbol mapped (from `symbols[]` field)

**Threshold:** ≥80% coverage (some quiet days are expected)

**Enforcement:** **WARN** if <80% over 30 days; investigate Alpaca WS health

---

#### Social

* [ ] At least 1 post on ≥70% of trading days
* [ ] `created_utc` timestamp present for all rows
* [ ] `title` or `body` non-empty for all rows
* [ ] Author metadata captured (karma, age)

**Threshold:** ≥70% coverage (weekends/holidays expected to be quiet)

**Enforcement:** **WARN** if <70% over 30 days; check Reddit API limits

---

### Level 2: Freshness (Critical for Live)

**Check:** Most recent data row ≤ N trading days old

| Dataset | Max Age (Dev) | Max Age (Live) |
|---------|---------------|----------------|
| Prices | 7 days | 1 day |
| News | 7 days | 1 day |
| Social | 7 days | 1 day |
| Features | 7 days | 1 day |

**Enforcement (Live):** **FLATTEN** position if any source >1 day stale

**Enforcement (Dev):** **WARN** if >7 days stale; may need backfill

---

### Level 3: Value Range Validation

#### Prices

| Column | Min | Max | Notes |
|--------|-----|-----|-------|
| `open`, `high`, `low`, `close` | 0.01 | 10,000 | Reject if outside (likely error) |
| `volume` | 0 | 1e12 | Reject if negative |
| Daily return | -0.20 | +0.20 | Flag if abs(return) > 20% (flash crash?) |
| `high` ≥ `low` | True | True | **BLOCK** if violated |
| `high` ≥ `open`, `close` | True | True | **BLOCK** if violated |
| `low` ≤ `open`, `close` | True | True | **BLOCK** if violated |

**Enforcement:** **BLOCK** row if price constraints violated; log for manual review

---

#### News

| Column | Min | Max | Notes |
|--------|-----|-----|-------|
| `headline` length | 10 chars | 500 chars | Warn if outside |
| `published_at` | 2020-01-01 | tomorrow | **BLOCK** if outside |
| Sentiment score (if present) | -1.0 | +1.0 | Warn if outside |
| `symbols[]` count | 1 | 50 | Warn if >50 (likely spam) |

**Enforcement:** **WARN** on outliers; **BLOCK** on impossible timestamps

---

#### Social

| Column | Min | Max | Notes |
|--------|-----|-----|-------|
| `title` length | 5 chars | 300 chars | Warn if outside |
| `author_karma` | 0 | 10,000,000 | Warn if >10M (bot?) |
| `author_age_days` | 0 | 7,300 | Warn if >20 years (error?) |
| `created_utc` | 2020-01-01 | tomorrow | **BLOCK** if outside |
| Sentiment score | -1.0 | +1.0 | Warn if outside |

**Enforcement:** **WARN** on outliers; filter bots in preprocessing

---

### Level 4: Duplication Check

**Prices:**
* [ ] No duplicate (date, symbol) pairs
* **Enforcement:** **BLOCK** write; dedupe before saving

**News:**
* [ ] No duplicate (url) or (published_at, headline) within same day
* **Enforcement:** **WARN** (expected from syndication); dedupe in preprocessing

**Social:**
* [ ] No duplicate (permalink) within same day
* **Enforcement:** **WARN** (should be rare); dedupe in preprocessing

---

### Level 5: Feature Table Validation

After feature engineering:

* [ ] One row per trading day (no missing days in range)
* [ ] All required features present (see `07-features/*.md`)
* [ ] NaN percentage ≤ 5% per feature
* [ ] Feature values in expected range (z-scores between -5 and +5 after standardization)
* [ ] Label column present and valid (return or up/down)

**Enforcement:** **BLOCK** training if >10% NaN; **WARN** if 5-10% NaN

---

## Automated Check Scripts

### Ingestion Check (After Each Source)

```bash
python -m orbit.ops.check_data --source prices --date today
# Runs schema, completeness, freshness, value range checks
# Outputs: PASS / WARN / FAIL with details
```

**Example output:**
```
✓ Schema validation: PASS
✓ Completeness: PASS (3/3 symbols, 252/252 days in window)
✓ Freshness: PASS (latest data: 2024-11-05)
✓ Value range: PASS (0 outliers)
✓ Duplication: PASS (0 duplicates)

Overall: PASS — Data ready for downstream processing
```

---

### Feature Table Check

```bash
python -m orbit.ops.check_features --date today
# Runs feature table validation
# Outputs: PASS / WARN / FAIL
```

**Example output:**
```
✓ Row count: PASS (1 row for 2024-11-05)
✓ Feature coverage: PASS (68/68 features present)
✗ NaN check: WARN (3 features have NaN: social_novelty_7d, post_count_z, comment_velocity)
✓ Value range: PASS (all z-scores in [-4.2, 4.8])
✓ Label: PASS (label_next_return = 0.0082)

Overall: WARN — Proceed with caution (social features missing; consider price+news only)
```

---

## Check Results Schema

All check results logged to: `logs/data_quality/<date>/checks.parquet`

**Schema:**
```
date: date
source: string  # prices, news, social, features
check_name: string  # e.g., "schema_validation", "completeness"
status: string  # PASS, WARN, FAIL
message: string  # Details
timestamp: timestamp
```

---

## Acceptance Thresholds by Environment

| Environment | PASS | WARN | FAIL | Action |
|-------------|------|------|------|--------|
| **Dev** | Proceed | Proceed + log | Block + investigate | Manual fix → retry |
| **Live** | Proceed | Proceed + alert | Flatten position + investigate | Page on-call engineer |

---

## Alerting Rules (Live Only)

### Critical (Page Immediately)

* Any **FAIL** status on schema, completeness, or freshness
* Feature NaN > 10%
* Price data >1 day stale

**Action:** Send alert to Slack/email; page on-call

---

### Warning (Log + Daily Digest)

* Feature NaN 5-10%
* News/social coverage <80%/70%
* Value range outliers (but not impossible)

**Action:** Include in daily digest email; review next business day

---

## Historical Check Analysis

**Monthly report:**

```bash
python -m orbit.ops.analyze_checks --month last
# Generates: reports/data_quality/YYYY-MM/quality_report.md
```

**Includes:**
- Pass/warn/fail rates by source
- Most common failure modes
- Trend over time (improving or degrading?)

**Example:**
```markdown
# Data Quality Report — October 2024

## Summary

| Source | Days | Pass | Warn | Fail | Pass Rate |
|--------|------|------|------|------|-----------|
| Prices | 21 | 21 | 0 | 0 | 100% |
| News | 21 | 18 | 3 | 0 | 85.7% |
| Social | 21 | 19 | 2 | 0 | 90.5% |
| Features | 21 | 20 | 1 | 0 | 95.2% |

## Issues

- **News coverage:** 3 days with <50 items (all Fridays after market close)
- **Social NaN:** 1 day with missing social_novelty_7d (Reddit API 429 error)

## Recommendations

- Investigate Alpaca WS reconnection on Fridays
- Add retry logic for Reddit API rate limits
```

---

## Data Quality Metrics (Tracked Over Time)

### Ingestion Reliability

* **Uptime:** % days with all 3 sources ingested successfully
* **Target:** ≥98%

### Feature Completeness

* **Coverage:** % days with ≤5% NaN in features
* **Target:** ≥95%

### Outlier Rate

* **Rate:** % rows flagged as outliers (but not blocked)
* **Target:** ≤1%

**Dashboard:** Track these metrics in `reports/data_quality/dashboard.html`

---

## Failure Examples & Recovery

### Example 1: Schema Mismatch

**Error:**
```
FAIL: Schema validation failed for prices
Expected dtype for 'close': float64, got: object
```

**Diagnosis:** Upstream data changed format (e.g., commas in numbers)

**Recovery:**
```bash
# Fix ingestion parser
vim orbit/ingest/prices.py  # Update CSV parsing

# Re-run ingestion
python -m orbit.ingest.prices --config orbit.yaml --date 2024-11-05 --force
```

---

### Example 2: Stale Data

**Error:**
```
FAIL: Freshness check failed for prices
Latest data: 2024-11-03 (2 days old)
```

**Diagnosis:** Ingestion job didn't run on 11-04 (holiday?) or failed silently

**Recovery:**
```bash
# Backfill missing days
python -m orbit.ingest.prices --config orbit.yaml --backfill --start-date 2024-11-04 --end-date 2024-11-05

# Re-run checks
python -m orbit.ops.check_data --source prices --date today
```

---

### Example 3: High NaN Rate

**Error:**
```
WARN: Feature NaN rate: 8.5% (above 5% threshold)
Affected features: social_novelty_7d, post_count_z, comment_velocity
```

**Diagnosis:** Reddit ingestion failed yesterday

**Recovery:**
```bash
# Re-run social ingestion for yesterday
python -m orbit.ingest.social --config orbit.yaml --date yesterday

# Re-build features
python -m orbit.features.build --config orbit.yaml --date today

# Re-run checks
python -m orbit.ops.check_features --date today
```

---

## Related Files

* `runbook.md` — Daily operations
* `drift_monitoring.md` — Model performance checks
* `logging_audit.md` — What gets logged
* `failure_modes_playbook.md` — Error recovery procedures
* `12-schemas/*.md` — Expected data schemas

---

