
*Last edited: 2025-11-05*

## Purpose

Document **common failure scenarios**, their symptoms, root causes, and step-by-step recovery procedures. This playbook enables fast diagnosis and remediation, minimizing downtime.

---

## Failure Mode Classification

| Severity | Definition | Response Time | Example |
|----------|------------|---------------|---------|
| **P0 (Critical)** | Production broken; cannot generate signals | <15 min | All data sources down |
| **P1 (High)** | Degraded; can generate signals but quality suspect | <1 hour | One modality missing |
| **P2 (Medium)** | Non-blocking; future runs affected | <4 hours | Feature drift detected |
| **P3 (Low)** | Cosmetic or long-term; no immediate impact | <1 day | Log compression failed |

---

## Failure Mode 1: Stooq Price Data Missing

### Symptoms

```
ERROR: No data for SPY.US on 2024-11-05
CRITICAL: Cannot compute price features
```

### Root Causes

* **A)** Stooq website down or blocked
* **B)** Market holiday (not a failure)
* **C)** Symbol delisted or renamed
* **D)** Network issue / firewall block

---

### Diagnosis

```bash
# Check if today is a trading day
python -m orbit.utils.calendar --date today

# Manual test (check if Stooq is responding)
curl -I https://stooq.com/q/d/?s=spy.us

# Check logs for HTTP error codes
grep "stooq" logs/ingest/prices_*.jsonl | grep ERROR | tail -n 5
```

---

### Recovery (Step-by-Step)

#### If market holiday:
```bash
# No action needed; pipeline should skip
python -m orbit.ops.skip_day --date today --reason "Market holiday"
```

#### If Stooq down:
```bash
# Option 1: Use backup source (Yahoo Finance, etc.)
python -m orbit.ingest.prices --config orbit.yaml --date today --source backup

# Option 2: Use yesterday's price (last resort)
python -m orbit.ingest.prices --config orbit.yaml --date today --fallback yesterday --flag stale

# Option 3: Flatten position (safest if price is critical)
python -m orbit.trade.flatten --reason "Price data unavailable"
```

#### If network issue:
```bash
# Check network connectivity
ping stooq.com

# Check firewall/proxy settings
curl -v https://stooq.com/q/d/?s=spy.us

# Retry with explicit proxy (if needed)
python -m orbit.ingest.prices --config orbit.yaml --date today --proxy http://proxy:8080
```

---

### Prevention

* Monitor Stooq uptime (external service like UptimeRobot)
* Configure backup data source in `orbit.yaml`
* Add calendar check before ingestion (skip holidays automatically)

---

## Failure Mode 2: Alpaca News WebSocket Disconnected

### Symptoms

```
WARNING: Alpaca WS disconnected at 14:23 ET
ERROR: Reconnect failed after 5 attempts
WARNING: News data incomplete for 2024-11-05 (only 234 items vs ~1500 expected)
```

### Root Causes

* **A)** Alpaca API outage
* **B)** Network disruption (local or ISP)
* **C)** Auth token expired
* **D)** Symbol limit exceeded (>30 on free tier)

---

### Diagnosis

```bash
# Check Alpaca status page
curl https://alpaca.markets/docs/api-status

# Test auth credentials
python -m orbit.ingest.news --config orbit.yaml --mode test_auth

# Check WS connection logs
grep "alpaca" logs/ingest/news_*.jsonl | grep "disconnect\|timeout" | tail -n 10

# Count subscribed symbols
grep "subscribed" logs/ingest/news_*.jsonl | tail -n 1
```

---

### Recovery (Step-by-Step)

#### If API outage:
```bash
# Check Alpaca status
open https://alpaca.markets/docs/api-status

# If outage confirmed, flatten or use price-only model
python -m orbit.trade.signal --config orbit.yaml --date today --fallback price_only
```

#### If network issue:
```bash
# Restart WS client
python -m orbit.ingest.news --config orbit.yaml --mode restart

# If restart fails, backfill from REST API (if available)
python -m orbit.ingest.news --config orbit.yaml --date today --mode backfill_rest
```

#### If auth expired:
```bash
# Refresh API keys
# 1. Generate new keys at alpaca.markets/dashboard
# 2. Update .env or secrets manager
export ALPACA_API_KEY="new_key"
export ALPACA_SECRET_KEY="new_secret"

# Restart WS client
python -m orbit.ingest.news --config orbit.yaml --mode restart
```

#### If symbol limit exceeded:
```bash
# Check subscription count
python -m orbit.ingest.news --config orbit.yaml --mode list_symbols

# Reduce to essential symbols (SPY, VOO, ^SPX keywords only)
python -m orbit.ingest.news --config orbit.yaml --mode resubscribe --symbols SPY,VOO
```

---

### Prevention

* Run WS client as a persistent daemon (restart on disconnect)
* Monitor connection health every 5 minutes
* Set up alerting for disconnect events
* Keep backup auth credentials ready

---

## Failure Mode 3: Reddit API Rate Limit (429)

### Symptoms

```
ERROR: Reddit API returned 429 (Too Many Requests)
WARNING: Only 512 posts ingested (expected ~1200)
```

### Root Causes

* **A)** Exceeded 100 QPM limit
* **B)** Burst of requests (no backoff)
* **C)** Reddit API degraded performance
* **D)** Incorrect OAuth scopes

---

### Diagnosis

```bash
# Check recent rate limit hits
grep "429" logs/ingest/social_*.jsonl | tail -n 10

# Check request rate
python -m orbit.ops.analyze_logs --module ingest.social --metric request_rate --minutes 5

# Test OAuth credentials
python -m orbit.ingest.social --config orbit.yaml --mode test_auth
```

---

### Recovery (Step-by-Step)

#### If rate limit hit:
```bash
# Wait for rate limit window to reset (usually 1 minute)
sleep 60

# Retry with exponential backoff
python -m orbit.ingest.social --config orbit.yaml --date today --retry --backoff exponential

# If still failing, reduce query frequency
python -m orbit.ingest.social --config orbit.yaml --date today --rate-limit 50  # 50 QPM instead of 100
```

#### If persistent:
```bash
# Skip social for today; use Price+News model
python -m orbit.trade.signal --config orbit.yaml --date today --fallback price_news_only

# Or use VADER/FinBERT only (skip Gemini escalation)
python -m orbit.ingest.social --config orbit.yaml --date today --skip-llm
```

---

### Prevention

* Implement token bucket rate limiter (enforce 100 QPM)
* Add exponential backoff on all Reddit API calls
* Batch requests when possible (use `subreddit.search()` with larger windows)
* Monitor Reddit API status: https://www.redditstatus.com/

---

## Failure Mode 4: Gemini Batch Request Timeout

### Symptoms

```
ERROR: Gemini batch request timed out after 120s
WARNING: Only 45% of posts scored with LLM (rest using VADER fallback)
```

### Root Causes

* **A)** Batch size too large (>100 posts)
* **B)** Gemini API slowdown / quota exceeded
* **C)** Network latency
* **D)** Malformed prompt in batch

---

### Diagnosis

```bash
# Check batch size
grep "gemini_batch_size" logs/ingest/social_*.jsonl | tail -n 5

# Check Gemini API quota
python -m orbit.ingest.social --config orbit.yaml --mode check_quota

# Test single post scoring
python -m orbit.ingest.social --config orbit.yaml --mode test_gemini --sample 1
```

---

### Recovery (Step-by-Step)

#### If timeout:
```bash
# Reduce batch size
python -m orbit.ingest.social --config orbit.yaml --date today --gemini-batch-size 50  # Down from 100

# Increase timeout
python -m orbit.ingest.social --config orbit.yaml --date today --gemini-timeout 180  # 3 minutes
```

#### If quota exceeded:
```bash
# Check quota status
python -m orbit.ingest.social --config orbit.yaml --mode check_quota

# If over limit, skip Gemini; use VADER/FinBERT only
python -m orbit.ingest.social --config orbit.yaml --date today --skip-llm
```

#### If persistent:
```bash
# Skip social LLM escalation for today
python -m orbit.ingest.social --config orbit.yaml --date today --skip-llm

# Use Price+News model
python -m orbit.trade.signal --config orbit.yaml --date today --fallback price_news_only
```

---

### Prevention

* Keep batch size ≤50 posts (conservative)
* Monitor Gemini quota daily
* Pre-filter aggressively with VADER (only escalate ambiguous posts)
* Cache Gemini scores for common posts (dedupe)

---

## Failure Mode 5: Feature Table Has High NaN Rate

### Symptoms

```
WARNING: 12 features have NaN for 2024-11-05 (17.6% of features)
ERROR: Cannot score; too many missing features
```

### Root Causes

* **A)** Upstream ingestion incomplete (news/social missing)
* **B)** Lookback window too short (not enough history)
* **C)** Feature formula error (division by zero, etc.)
* **D)** Data type mismatch

---

### Diagnosis

```bash
# Check which features are NaN
python -m orbit.features.diagnose --date today

# Check ingestion completeness
python -m orbit.ops.check_data --all --date today

# Check feature logs for errors
grep "ERROR\|division by zero" logs/features/features_*.jsonl | tail -n 10
```

---

### Recovery (Step-by-Step)

#### If ingestion incomplete:
```bash
# Re-run missing ingestion
python -m orbit.ingest.news --config orbit.yaml --date today
python -m orbit.ingest.social --config orbit.yaml --date today

# Re-build features
python -m orbit.features.build --config orbit.yaml --date today

# Verify
python -m orbit.features.diagnose --date today
```

#### If lookback window issue:
```bash
# Check if we have enough historical data
python -m orbit.features.check_history --date today --window 60d

# If not, backfill
python -m orbit.ops.repair --start-date $(date -d '60 days ago' +%Y-%m-%d) --end-date yesterday
```

#### If >10% NaN (unsafe to trade):
```bash
# Flatten position
python -m orbit.trade.flatten --reason "Feature NaN rate >10%"

# Investigate and fix root cause
# (See logs for specific feature errors)
```

---

### Prevention

* Run data quality checks after ingestion (before features)
* Add unit tests for feature formulas (check for divide-by-zero)
* Monitor feature NaN rate daily

---

## Failure Mode 6: Model File Missing or Corrupted

### Symptoms

```
ERROR: Model file not found: models/heads/price/2024-q4-v1/2024-q3/model.pkl
CRITICAL: Cannot generate score
```

### Root Causes

* **A)** Training did not complete
* **B)** File deleted accidentally
* **C)** Disk corruption
* **D)** Wrong window selected (model not yet trained for this period)

---

### Diagnosis

```bash
# Check if model files exist
ls -lh models/heads/price/2024-q4-v1/2024-q3/

# Check training logs
grep "Model saved" logs/train/train_2024-q4-v1.jsonl | tail -n 5

# Verify file integrity (if file exists)
python -m orbit.ops.verify_model --path models/heads/price/2024-q4-v1/2024-q3/model.pkl
```

---

### Recovery (Step-by-Step)

#### If training incomplete:
```bash
# Re-run training for missing window
python -m orbit.train --config orbit.yaml --mode retrain --window 2024-q3
```

#### If file deleted:
```bash
# Restore from backup (if available)
aws s3 cp s3://orbit-models/heads/price/2024-q4-v1/2024-q3/model.pkl models/heads/price/2024-q4-v1/2024-q3/

# Or re-train from scratch
python -m orbit.train --config orbit.yaml --mode retrain --window 2024-q3
```

#### If wrong window:
```bash
# Use fallback to previous window
python -m orbit.score --config orbit.yaml --date today --fallback-window 2024-q2

# Or flatten until correct window trained
python -m orbit.trade.flatten --reason "Model window not yet available"
```

---

### Prevention

* Backup models to cloud after each training run
* Add checksum validation after training
* Test model loading in CI/CD pipeline

---

## Failure Mode 7: Out-of-Memory (OOM) During Training

### Symptoms

```
ERROR: MemoryError: Unable to allocate array
CRITICAL: Training crashed at epoch 23
```

### Root Causes

* **A)** Training data too large
* **B)** Batch size too large
* **C)** Model too complex (too many parameters)
* **D)** Memory leak in training loop

---

### Diagnosis

```bash
# Check available memory
free -h

# Check training batch size
grep "batch_size" orbit.yaml

# Check model parameter count
python -m orbit.train --config orbit.yaml --mode print_model_size
```

---

### Recovery (Step-by-Step)

#### If batch size too large:
```yaml
# Edit orbit.yaml
training:
  batch_size: 64  # Reduce from 128
```

```bash
# Re-run training
python -m orbit.train --config orbit.yaml --mode retrain
```

#### If model too complex:
```yaml
# Edit orbit.yaml
modeling:
  heads:
    hidden_layers: [32]  # Reduce from [64, 32]
```

```bash
# Re-train with simpler model
python -m orbit.train --config orbit.yaml --mode retrain
```

#### If persistent:
```bash
# Train on smaller window (e.g., 1 year instead of 3)
python -m orbit.train --config orbit.yaml --mode retrain --window 1y

# Or use incremental training (train per month, then ensemble)
python -m orbit.train --config orbit.yaml --mode incremental
```

---

### Prevention

* Monitor memory usage during training
* Set max memory limit for training process
* Use gradient checkpointing for large models

---

## Emergency Procedures

### Emergency Flatten (Immediate)

**When to use:**
- Multiple data sources down
- Model producing nonsensical scores
- Market anomaly (flash crash, circuit breaker)
- Critical bug discovered in production code

**Command:**
```bash
python -m orbit.trade.flatten --reason "Emergency: <description>" --user <your_name>

# Logs to logs/ops/emergency_YYYY-MM-DD.jsonl
# Sends alert to on-call
```

---

### Model Rollback (Within 1 hour)

**When to use:**
- New model performing significantly worse than backtest
- New model producing erratic signals
- Post-deployment drift detected

**Command:**
```bash
# List available previous models
python -m orbit.ops.list_models --environment production --history

# Rollback to previous model
python -m orbit.ops.rollback --run-id <previous_run_id> --reason "<description>"

# Verify rollback
python -m orbit.score --config orbit.yaml --date today
```

---

### Data Repair (Within 4 hours)

**When to use:**
- Multiple days have missing or corrupt data
- Discovered systematic ingestion error

**Command:**
```bash
# Repair specific date range
python -m orbit.ops.repair --start-date 2024-11-01 --end-date 2024-11-05 --sources prices,news,social

# Re-run full pipeline for affected dates
python -m orbit.ops.repair --start-date 2024-11-01 --end-date 2024-11-05 --full-pipeline

# Verify repair
python -m orbit.ops.check_data --all --date-range 2024-11-01:2024-11-05
```

---

## Escalation Path

| Issue Severity | First Responder | Escalate To | SLA |
|----------------|-----------------|-------------|-----|
| P0 (Critical) | On-call engineer | Tech lead | 15 min |
| P1 (High) | On-call engineer | Tech lead (if not resolved in 1h) | 1 hour |
| P2 (Medium) | Daily ops review | Tech lead (next business day) | 4 hours |
| P3 (Low) | Weekly review | None | 1 day |

---

## Acceptance Checklist

* [ ] All failure modes have documented symptoms + recovery
* [ ] Emergency procedures tested (dry-run monthly)
* [ ] Escalation path clear and contact info current
* [ ] Playbook accessible to on-call engineers (Wiki, Notion, etc.)
* [ ] Recovery scripts tested in staging environment

---

## Related Files

* `runbook.md` — Daily operations
* `data_quality_checks.md` — Detection of data failures
* `drift_monitoring.md` — Detection of performance failures
* `logging_audit.md` — Where to look for error details

---

