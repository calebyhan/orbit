# ORBIT — Logging & Audit

*Last edited: 2025-11-05*

## Purpose

Define **what gets logged, where, and how** to ensure complete audit trail, debuggability, and compliance. Logs must enable reconstruction of any model decision and data lineage.

---

## Logging Philosophy

* **Immutable:** Never delete or modify logs; archive only
* **Structured:** JSON format for machine parsing
* **Timestamped:** All entries have ISO-8601 timestamp in ET
* **Contextual:** Include run_id, date, module, and relevant IDs
* **Privacy-safe:** No PII; comply with TOS (see `04-data-sources/tos_compliance.md`)

---

## Log Levels

| Level | Use Case | Examples |
|-------|----------|----------|
| **DEBUG** | Development only; verbose internals | "Parsing CSV row 1234", "Gate α = 0.32" |
| **INFO** | Normal operations; key milestones | "Ingestion complete: 1,523 rows", "Model loaded" |
| **WARNING** | Non-critical issues; degraded mode | "Missing 3 news items for today", "Feature NaN rate: 6%" |
| **ERROR** | Failures that can be recovered | "Reddit API 429; retrying in 60s" |
| **CRITICAL** | Failures requiring immediate attention | "Model file missing", "Schema validation failed" |

**Default level (live):** INFO  
**Development:** DEBUG

---

## Log Structure (JSON)

**Format:** One JSON object per line (JSONL)

**Required fields:**
```json
{
  "timestamp": "2024-11-05T16:35:12-05:00",
  "level": "INFO",
  "module": "orbit.ingest.prices",
  "run_id": "2024-q4-v1",
  "date": "2024-11-05",
  "message": "Ingestion complete",
  "details": {
    "symbols": ["SPY", "VOO", "^SPX"],
    "rows_written": 3,
    "elapsed_sec": 2.4
  }
}
```

**Optional fields:**
- `error_type`: Exception class name (for ERROR/CRITICAL)
- `traceback`: Stack trace (for ERROR/CRITICAL)
- `user`: Username or "system" (for audit)

---

## Log File Organization

### Directory Structure

```
logs/
├── ingest/
│   ├── prices_YYYY-MM-DD.jsonl
│   ├── news_YYYY-MM-DD.jsonl
│   └── social_YYYY-MM-DD.jsonl
├── preprocess/
│   └── preprocess_YYYY-MM-DD.jsonl
├── features/
│   └── features_YYYY-MM-DD.jsonl
├── train/
│   └── train_<run_id>.jsonl
├── score/
│   └── score_YYYY-MM-DD.jsonl
├── backtest/
│   └── backtest_<run_id>.jsonl
├── ops/
│   ├── drift_YYYY-MM-DD.jsonl
│   ├── health_check_YYYY-MM-DD.jsonl
│   └── emergency_YYYY-MM-DD.jsonl
└── daily.jsonl  # Consolidated daily log
```

---

## What Gets Logged (By Module)

### 1. Ingestion (Prices, News, Social)

**INFO events:**
- Start ingestion (timestamp, source, date range)
- Rows fetched, rows deduplicated, rows written
- End ingestion (elapsed time)

**WARNING events:**
- API rate limit hit (429)
- Missing data for expected symbol/day
- Outlier values detected (flagged but not blocked)

**ERROR events:**
- API failure after retries
- Schema validation failure
- Network timeout

**Example:**
```json
{
  "timestamp": "2024-11-05T16:10:15-05:00",
  "level": "INFO",
  "module": "orbit.ingest.news",
  "date": "2024-11-05",
  "message": "Alpaca WS ingestion complete",
  "details": {
    "items_fetched": 1847,
    "items_deduplicated": 312,
    "items_written": 1535,
    "elapsed_sec": 28.3,
    "cutoff_time": "15:30:00"
  }
}
```

---

### 2. Preprocessing

**INFO events:**
- Start preprocessing step (dedup, time alignment, mapping, quality filters)
- Items processed, items filtered out, items passed
- End preprocessing (elapsed time)

**WARNING events:**
- High duplicate rate (>50%)
- Low mapping rate (<70% of items matched to symbols)

**ERROR events:**
- Missing input files
- Unexpected data format

**Example:**
```json
{
  "timestamp": "2024-11-05T16:12:42-05:00",
  "level": "INFO",
  "module": "orbit.preprocess.dedup",
  "date": "2024-11-05",
  "message": "Deduplication complete",
  "details": {
    "input_rows": 1535,
    "clusters_found": 287,
    "output_rows": 1248,
    "dedup_rate": 0.187,
    "method": "simhash"
  }
}
```

---

### 3. Feature Engineering

**INFO events:**
- Start feature build
- Features computed (count, names)
- NaN rate per feature
- End feature build (elapsed time)

**WARNING events:**
- NaN rate >5% for any feature
- Feature value outside expected range (after z-scoring)

**ERROR events:**
- Missing price data (cannot compute features)
- Division by zero in feature formula

**Example:**
```json
{
  "timestamp": "2024-11-05T16:15:03-05:00",
  "level": "INFO",
  "module": "orbit.features.build",
  "date": "2024-11-05",
  "message": "Features computed",
  "details": {
    "features_count": 68,
    "nan_rate": 0.029,
    "features_with_nan": ["social_novelty_7d", "post_count_z"],
    "elapsed_sec": 4.1
  }
}
```

---

### 4. Training

**INFO events:**
- Start training (run_id, config hash, train/val/test dates)
- Epoch progress (loss, val metrics)
- Early stop triggered
- Model saved (path, file size)
- End training (total epochs, best val AUC, elapsed time)

**WARNING events:**
- Validation loss not improving
- Gradient clipping triggered

**ERROR events:**
- NaN loss
- OOM (out of memory)
- Model file write failure

**Example:**
```json
{
  "timestamp": "2024-11-05T18:45:22-05:00",
  "level": "INFO",
  "module": "orbit.train",
  "run_id": "2024-q4-v1",
  "message": "Training complete",
  "details": {
    "window": "2024-q3",
    "train_dates": ["2024-01-01", "2024-09-30"],
    "val_dates": ["2024-10-01", "2024-10-31"],
    "epochs": 42,
    "best_val_auc": 0.558,
    "heads": ["price", "news", "social"],
    "fusion": "gated_blend",
    "model_paths": {
      "price": "models/heads/price/2024-q4-v1/2024-q3/model.pkl",
      "news": "models/heads/news/2024-q4-v1/2024-q3/model.pkl",
      "social": "models/heads/social/2024-q4-v1/2024-q3/model.pkl",
      "fusion": "models/fusion/2024-q4-v1/2024-q3/fusion_params.json"
    },
    "elapsed_sec": 892.4
  }
}
```

---

### 5. Scoring

**INFO events:**
- Start scoring (date, run_id)
- Head scores computed
- Fusion applied (final score)
- Score written to parquet
- End scoring (elapsed time)

**WARNING events:**
- Missing features (NaN) → fallback logic used
- Score outside expected range (e.g., probability >1.0)

**ERROR events:**
- Model file missing
- Feature table missing for date

**Example:**
```json
{
  "timestamp": "2024-11-05T16:32:18-05:00",
  "level": "INFO",
  "module": "orbit.score",
  "run_id": "2024-q4-v1",
  "date": "2024-11-05",
  "message": "Scoring complete",
  "details": {
    "price_head_score": 0.543,
    "news_head_score": 0.621,
    "social_head_score": 0.509,
    "news_gate": 0.68,
    "social_gate": 0.42,
    "fused_score": 0.591,
    "elapsed_sec": 0.8
  }
}
```

---

### 6. Trade Signal Generation

**INFO events:**
- Signal generated (date, position, score, threshold)
- Signal written to file

**WARNING events:**
- Score very close to threshold (ambiguous decision)

**CRITICAL events:**
- Emergency flatten triggered

**Example:**
```json
{
  "timestamp": "2024-11-05T16:35:00-05:00",
  "level": "INFO",
  "module": "orbit.trade.signal",
  "run_id": "2024-q4-v1",
  "date": "2024-11-05",
  "message": "Trade signal generated",
  "details": {
    "fused_score": 0.591,
    "threshold": 0.55,
    "position": 1.0,
    "decision": "LONG",
    "confidence": "medium"
  }
}
```

---

### 7. Backtest

**INFO events:**
- Backtest started (run_id, date range, variant)
- Equity curve computed
- Metrics computed (IC, Sharpe, max DD, etc.)
- Backtest complete (elapsed time)

**Example:**
```json
{
  "timestamp": "2024-11-05T20:12:45-05:00",
  "level": "INFO",
  "module": "orbit.backtest",
  "run_id": "2024-q4-v1",
  "message": "Backtest complete",
  "details": {
    "variant": "overnight",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "days": 252,
    "trades": 163,
    "ic": 0.023,
    "auc": 0.558,
    "sharpe": 0.42,
    "max_drawdown": -0.151,
    "hit_rate": 0.542,
    "coverage": 0.647,
    "total_return": 0.243,
    "elapsed_sec": 12.3
  }
}
```

---

### 8. Operations (Health Checks, Drift, Emergency)

**INFO events:**
- Health check passed
- Drift report generated
- Model promoted

**WARNING events:**
- Data quality check WARN
- Drift threshold exceeded

**CRITICAL events:**
- Emergency flatten
- Model rollback
- Ingestion failure (all sources down)

**Example (emergency flatten):**
```json
{
  "timestamp": "2024-11-05T14:58:32-05:00",
  "level": "CRITICAL",
  "module": "orbit.ops.emergency",
  "date": "2024-11-05",
  "message": "Emergency flatten triggered",
  "details": {
    "reason": "Price data >1 day stale; news WS disconnected",
    "previous_position": 1.0,
    "new_position": 0.0,
    "user": "on-call-engineer"
  }
}
```

---

## Audit Trail (Decision Lineage)

For every trade signal, log the **complete decision path**:

**File:** `logs/audit/<run_id>/decisions_YYYY-MM-DD.jsonl`

**Schema:**
```json
{
  "timestamp": "2024-11-05T16:35:00-05:00",
  "date": "2024-11-05",
  "run_id": "2024-q4-v1",
  "decision": {
    "position": 1.0,
    "score": 0.591,
    "threshold": 0.55
  },
  "inputs": {
    "price_features": {"momentum_20d": 0.032, "rv_10d": 0.012, ...},
    "news_features": {"news_count_z": 1.8, "news_sentiment_mean": 0.12, ...},
    "social_features": {"post_count_z": 0.9, "social_sentiment_mean": 0.05, ...}
  },
  "head_scores": {
    "price": 0.543,
    "news": 0.621,
    "social": 0.509
  },
  "gates": {
    "news_gate": 0.68,
    "social_gate": 0.42
  },
  "fused_score": 0.591,
  "model_version": {
    "price_head": "models/heads/price/2024-q4-v1/2024-q3/model.pkl",
    "news_head": "models/heads/news/2024-q4-v1/2024-q3/model.pkl",
    "social_head": "models/heads/social/2024-q4-v1/2024-q3/model.pkl",
    "fusion": "models/fusion/2024-q4-v1/2024-q3/fusion_params.json"
  },
  "data_sources": {
    "prices": "data/prices/2024/11/05/spy.parquet",
    "news": "data/news/2024/11/05/alpaca.parquet",
    "social": "data/social/2024/11/05/reddit.parquet"
  }
}
```

**Purpose:** Enable recreation of any signal from raw data + model artifacts.

---

## Log Rotation & Retention

**Rotation:**
- Daily logs rotate at midnight ET
- Training logs kept per run_id (no rotation)

**Retention:**
- **Raw logs:** 90 days (then compress to .gz)
- **Audit logs:** 2 years (regulatory requirement)
- **Training logs:** Permanent (tied to model artifacts)

**Archival:**
```bash
# Weekly compression (run Sunday night)
python -m orbit.ops.compress_logs --older-than 7d

# Monthly backup to cloud
aws s3 sync logs/ s3://orbit-logs/ --exclude "*.jsonl" --include "*.jsonl.gz"
```

---

## Log Analysis Tools

### Search Logs

```bash
# Find all ERROR/CRITICAL in last 7 days
grep -h '"level": "ERROR\|CRITICAL"' logs/**/*$(date -d '7 days ago' +%Y-%m-%d)*.jsonl

# Find all ingestion failures
grep '"module": "orbit.ingest"' logs/ingest/*.jsonl | grep ERROR
```

### Parse & Aggregate

```bash
# Count log levels per day
python -m orbit.ops.analyze_logs --metric level_counts --days 30

# Track ingestion timing
python -m orbit.ops.analyze_logs --metric elapsed_time --module ingest --days 30
```

---

## Compliance & Privacy

**No PII:**
- Never log full Reddit usernames (only hashed IDs if needed)
- Never log full news article URLs with tracking params
- Never log internal IP addresses or auth tokens

**Audit requirements:**
- All model decisions must be reconstructable for 2 years
- All data quality failures must be logged
- All emergency actions must be logged with human attribution

**See:** `04-data-sources/tos_compliance.md` for data retention rules.

---

## Acceptance Checklist

* [ ] All modules log to structured JSONL
* [ ] Logs include timestamp, level, module, run_id, date
* [ ] Audit trail captures complete decision lineage
* [ ] Logs rotate daily and compress after 7 days
* [ ] Retention policy enforced (90d raw, 2yr audit)
* [ ] No PII in logs
* [ ] Log analysis tools tested
* [ ] Emergency logs have human attribution

---

## Related Files

* `runbook.md` — Daily operations
* `data_quality_checks.md` — What data checks get logged
* `drift_monitoring.md` — Performance drift logs
* `failure_modes_playbook.md` — Error recovery (uses logs)

---

