# ORBIT — Operations Runbook

*Last edited: 2025-11-05*

## Purpose

Provide step-by-step instructions for running the ORBIT pipeline daily, both in development (backtesting) and production (live scoring). Includes error handling, recovery procedures, and monitoring.

---

## Prerequisites

* Python 3.11+ installed
* `requirements.txt` dependencies installed
* API keys configured (see `03-config/env_keys.md`)
* Config file ready: `orbit.yaml`
* Data directories initialized: `data/`, `models/`, `reports/`, `logs/`

---

## Development Mode (Backtesting)

### Full Pipeline (Historical Data)

Run all steps on historical data to train and evaluate model:

```bash
# 1. Ingest historical data (one-time or periodic refresh)
python -m orbit.ingest.prices --config orbit.yaml --backfill --start-date 2020-01-01 --end-date 2024-12-31
python -m orbit.ingest.news --config orbit.yaml --backfill --start-date 2020-01-01 --end-date 2024-12-31
python -m orbit.ingest.social --config orbit.yaml --backfill --start-date 2020-01-01 --end-date 2024-12-31

# 2. Preprocess
python -m orbit.preprocess.time_alignment --config orbit.yaml
python -m orbit.preprocess.dedup --config orbit.yaml
python -m orbit.preprocess.mapping --config orbit.yaml
python -m orbit.preprocess.quality_filters --config orbit.yaml

# 3. Build features
python -m orbit.features.build --config orbit.yaml

# 4. Train models (walk-forward)
python -m orbit.train --config orbit.yaml --mode walkforward

# 5. Score (generate fused scores)
python -m orbit.score --config orbit.yaml --run-id <run_id>

# 6. Backtest
python -m orbit.backtest --config orbit.yaml --run-id <run_id>

# 7. Generate reports
python -m orbit.evaluate.ablations --run-id <run_id>
python -m orbit.evaluate.regimes --run-id <run_id>
python -m orbit.evaluate.dashboard --run-id <run_id>
python -m orbit.evaluate.gates --run-id <run_id>
```

**Duration:** ~30-90 minutes (depending on date range)

---

## Production Mode (Daily Live Scoring)

### Daily Job Sequence

**Schedule:** Run after market close, before 18:00 ET

**Cron example:**
```cron
# Run daily at 16:30 ET (after market close)
30 16 * * 1-5 cd /path/to/orbit && /path/to/python -m orbit.daily --config orbit.yaml >> logs/daily.log 2>&1
```

---

### Step-by-Step Daily Workflow

#### 1. Ingest Today's Data (16:05 - 16:20 ET)

```bash
# Prices (Stooq)
python -m orbit.ingest.prices --config orbit.yaml --date today
# Output: data/prices/YYYY/MM/DD/spy.parquet, voo.parquet, spx.parquet

# News (Alpaca WS — should have been running continuously)
# Check if WS captured today's news; if not, backfill:
python -m orbit.ingest.news --config orbit.yaml --date today --mode check_and_backfill

# Social (Reddit)
python -m orbit.ingest.social --config orbit.yaml --date today
# Output: data/social/YYYY/MM/DD/reddit.parquet
```

**Check:** Verify row counts in logs:
```bash
tail -n 20 logs/ingest_prices.log
tail -n 20 logs/ingest_news.log
tail -n 20 logs/ingest_social.log
```

---

#### 2. Preprocess (16:20 - 16:25 ET)

```bash
python -m orbit.preprocess.all --config orbit.yaml --date today
# Runs: time_alignment, dedup, mapping, quality_filters
# Output: data/preprocessed/YYYY/MM/DD/*.parquet
```

**Check:** Review dedupe stats:
```bash
grep "Deduplicated" logs/preprocess.log | tail -n 5
```

---

#### 3. Build Features (16:25 - 16:30 ET)

```bash
python -m orbit.features.build --config orbit.yaml --date today
# Output: data/features/YYYY/MM/DD/features_daily.parquet (one row for today)
```

**Check:** Verify feature completeness:
```bash
python -m orbit.features.validate --date today
# Should print: "All features computed, 0 NaN"
```

---

#### 4. Score (16:30 - 16:35 ET)

```bash
python -m orbit.score --config orbit.yaml --date today --run-id <production_run_id>
# Output: data/scores/<run_id>/YYYY/MM/DD/scores.parquet
# Contains: price_head_score, news_head_score, social_head_score, fused_score
```

**Check:** Verify score range:
```bash
python -m orbit.score.inspect --date today --run-id <production_run_id>
# Should print: "fused_score = 0.XXX (0.0-1.0 range for classification)"
```

---

#### 5. Generate Trade Signal (16:35 - 16:40 ET)

```bash
python -m orbit.trade.signal --config orbit.yaml --date today --run-id <production_run_id>
# Output: reports/signals/YYYY/MM/DD/signal.json
# Contains: { "date": "YYYY-MM-DD", "position": 0 or 1, "score": X.XX, "threshold": X.XX }
```

**Check:** Review signal:
```bash
cat reports/signals/$(date +%Y/%m/%d)/signal.json
```

---

#### 6. Log & Archive (16:40 - 16:45 ET)

```bash
# Archive today's run
python -m orbit.ops.archive --date today --run-id <production_run_id>

# Upload to cloud storage (optional)
# aws s3 sync data/ s3://orbit-data/
# aws s3 sync reports/ s3://orbit-reports/
```

---

### One-Command Daily Run

Alternatively, use the consolidated daily script:

```bash
python -m orbit.daily --config orbit.yaml --date today --run-id <production_run_id>
```

This script wraps steps 1-6 with error handling and automatic recovery.

---

## Error Handling

### Error 1: Missing Price Data

**Symptom:**
```
ERROR: No data for SPY.US on 2024-11-05
```

**Diagnosis:** Stooq is down, or market holiday

**Recovery:**
```bash
# Check if today is a trading day
python -m orbit.utils.calendar --date today
# If holiday, skip. If trading day:

# Manual download from backup source
python -m orbit.ingest.prices --config orbit.yaml --date today --source backup

# Or use yesterday's price as fallback (risky!)
python -m orbit.ingest.prices --config orbit.yaml --date today --fallback yesterday
```

**Action:** If missing, **flatten position** (signal = 0) for safety.

---

### Error 2: News WebSocket Disconnected

**Symptom:**
```
WARNING: Alpaca WS disconnected at 14:23 ET; attempting reconnect...
ERROR: Reconnect failed after 5 attempts
```

**Diagnosis:** Alpaca API issue or network problem

**Recovery:**
```bash
# Check WS status
python -m orbit.ingest.news --config orbit.yaml --mode status

# Restart WS client
python -m orbit.ingest.news --config orbit.yaml --mode restart

# Backfill missing hours
python -m orbit.ingest.news --config orbit.yaml --date today --backfill-from 14:00
```

**Action:** If backfill fails, **flatten position** or use price-only model.

---

### Error 3: Reddit API Rate Limit (429)

**Symptom:**
```
ERROR: Reddit API returned 429 (Too Many Requests)
```

**Diagnosis:** Exceeded 100 QPM limit

**Recovery:**
```bash
# Wait for rate limit reset (usually 1 minute)
sleep 60

# Retry with exponential backoff
python -m orbit.ingest.social --config orbit.yaml --date today --retry
```

**Action:** If persistent, skip social for today; use Price+News model.

---

### Error 4: Gemini Batch Timeout

**Symptom:**
```
ERROR: Gemini batch request timed out after 120s
```

**Diagnosis:** Too many posts in batch, or API slowdown

**Recovery:**
```bash
# Reduce batch size
python -m orbit.ingest.social --config orbit.yaml --date today --gemini-batch-size 50

# Or skip Gemini, use heuristic fallback scoring
python -m orbit.ingest.social --config orbit.yaml --date today --skip-llm
```

**Action:** Heuristic pre-scores or a very fast Gemini‑lite pass are sufficient for most days.

---

### Error 5: Feature NaN (Missing Data)

**Symptom:**
```
WARNING: 12 features have NaN for 2024-11-05
```

**Diagnosis:** Upstream ingestion incomplete

**Recovery:**
```bash
# Check which features are NaN
python -m orbit.features.diagnose --date today

# Re-run ingestion for missing source
python -m orbit.ingest.<source> --config orbit.yaml --date today

# Re-build features
python -m orbit.features.build --config orbit.yaml --date today
```

**Action:** If >10 features NaN, **flatten position** (too risky to trade).

---

### Error 6: Model File Missing

**Symptom:**
```
ERROR: Model file not found: models/heads/price/<run_id>/2024-q3/model.pkl
```

**Diagnosis:** Training incomplete or file deleted

**Recovery:**
```bash
# Check available model windows
ls -la models/heads/price/<run_id>/

# Re-train if necessary
python -m orbit.train --config orbit.yaml --mode retrain --window 2024-q3

# Or use fallback model from previous window
python -m orbit.score --config orbit.yaml --date today --fallback-window 2024-q2
```

**Action:** If no valid model, **flatten position** until retrained.

---

## Monitoring Checklist (Daily)

After each run, verify:

* [ ] **Ingestion:** All 3 sources (prices, news, social) have data for today
* [ ] **Preprocessing:** Dedupe reduced item count by 10-30% (typical)
* [ ] **Features:** ≤5% NaN in feature table
* [ ] **Scoring:** Fused score in valid range (0-1 for classification, realistic bps for regression)
* [ ] **Signal:** Position decision (0 or 1) logged with timestamp
* [ ] **Logs:** No ERROR or CRITICAL messages in logs/
* [ ] **Runtime:** Full pipeline completed in <15 minutes

**Automated check:**
```bash
python -m orbit.ops.health_check --date today --run-id <production_run_id>
# Prints: "✓ All checks passed" or "✗ N checks failed"
```

---

## Weekly Tasks

**Every Monday (after market close):**

* [ ] Review last week's performance metrics
* [ ] Check for data quality issues (missing days, outliers)
* [ ] Verify model drift (see `drift_monitoring.md`)
* [ ] Archive old logs (keep last 30 days)

**Command:**
```bash
python -m orbit.ops.weekly_review --week last
# Generates: reports/weekly/YYYY-WW/review.md
```

---

## Monthly Tasks

**First trading day of month:**

* [ ] Re-train models if performance drift detected (see `drift_monitoring.md`)
* [ ] Rotate model windows (drop oldest, add latest)
* [ ] Backup data/ and models/ to cloud storage
* [ ] Generate monthly performance report

**Command:**
```bash
python -m orbit.ops.monthly_tasks --month last
```

---

## Emergency Procedures

### Flatten All Positions (Immediately)

If critical error or market anomaly:

```bash
python -m orbit.trade.flatten --reason "Emergency: <description>"
# Generates signal = 0 for today
# Logs event to logs/emergency.log
```

---

### Rollback to Previous Model

If new model is performing poorly:

```bash
python -m orbit.ops.rollback --run-id <previous_run_id>
# Repoints production to previous model artifacts
# Logs rollback event
```

---

### Data Repair (Backfill)

If multiple days have missing data:

```bash
python -m orbit.ops.repair --start-date 2024-11-01 --end-date 2024-11-05
# Re-runs ingestion, preprocessing, features for date range
# Does NOT re-train (use existing models)
```

---

## Logs & Debugging

**Log locations:**
- `logs/ingest_prices.log`
- `logs/ingest_news.log`
- `logs/ingest_social.log`
- `logs/preprocess.log`
- `logs/features.log`
- `logs/score.log`
- `logs/daily.log` (consolidated)

**Useful grep commands:**
```bash
# Find errors
grep -i "error" logs/daily.log | tail -n 20

# Check runtime
grep "elapsed" logs/daily.log | tail -n 10

# Verify data counts
grep "rows written" logs/*.log
```

---

## Performance Tracking

**Live vs Backtest:**

Track realized performance (if executing trades) vs backtest predictions:

```bash
python -m orbit.ops.track_live --date today
# Compares predicted score vs actual return
# Updates live_performance.parquet
```

**Monthly IC:**

```bash
python -m orbit.evaluate.live_ic --month last
# Computes IC on live scoring data
# Should be close to backtest IC; if diverges >0.01, investigate drift
```

---

## Acceptance Checklist

* [ ] Daily pipeline completes in <15 minutes
* [ ] Zero CRITICAL or ERROR log messages under normal conditions
* [ ] Automated health checks pass daily
* [ ] Weekly and monthly tasks documented and scripted
* [ ] Emergency procedures tested (dry-run)
* [ ] All recovery scenarios have documented playbooks

---

## Related Files

* `data_quality_checks.md` — Ingestion validation rules
* `drift_monitoring.md` — Model performance tracking
* `logging_audit.md` — What gets logged and where
* `failure_modes_playbook.md` — Detailed error recovery

---

