# ORBIT — Troubleshooting Flowchart

*Last edited: 2025-11-06*

## Purpose

Decision trees and diagnostic flowcharts for common ORBIT issues. Follow the flowcharts to quickly identify root causes and apply fixes.

---

## Flowchart 1: Pipeline Failure Diagnosis

```
Pipeline Failed?
│
├─> Check logs/orbit_main.log
    │
    ├─> Error: "No data ingested"
    │   │
    │   ├─> Which source?
    │   │   ├─> Prices → See Flowchart 2: Price Ingestion
    │   │   ├─> News → See Flowchart 3: News WebSocket
    │   │   └─> Social → See Flowchart 4: Reddit API
    │   │
    │   └─> Check data/raw/<source>/YYYY/MM/DD/
    │       ├─> Directory missing → Ingestion didn't run
    │       └─> Files empty → Source unavailable or auth failure
    │
    ├─> Error: "Feature computation failed"
    │   │
    │   └─> Check logs/features.log
    │       ├─> "High NaN rate" → Missing upstream data
    │       │   └─> Verify data/prices/, data/news/, data/social/ exist
    │       ├─> "Division by zero" → Zero variance in rolling window
    │       │   └─> Extend lookback window in config
    │       └─> "Memory error" → Dataset too large
    │           └─> Reduce date range or increase RAM
    │
    ├─> Error: "Model training failed"
    │   │
    │   └─> Check logs/train.log
    │       ├─> "Insufficient data" → Need ≥252 trading days
    │       ├─> "Convergence warning" → Try different hyperparams
    │       └─> "OOM (Out of Memory)" → Reduce batch size
    │
    └─> Error: "Backtest failed"
        │
        └─> Check logs/backtest.log
            ├─> "No scores found" → Scoring step didn't run
            ├─> "Invalid threshold" → Check config threshold value
            └─> "Negative equity" → Review cost model parameters
```

---

## Flowchart 2: Price Ingestion Issues

```
Price Ingestion Failed?
│
├─> Check network connectivity
    │
    ├─> Can reach stooq.com?
    │   ├─> NO → Network/firewall issue
    │   │   └─> Fix: Check internet, VPN, firewall rules
    │   └─> YES → Continue below
    │
    └─> Check logs/ingest_prices.log
        │
        ├─> "HTTP 429 Too Many Requests"
        │   └─> Fix: Stooq rate-limited you
        │       ├─> Wait 1 hour, retry
        │       └─> Add polite_delay_sec in config (increase to 2-3s)
        │
        ├─> "HTTP 404 Not Found"
        │   └─> Fix: Symbol not available on Stooq
        │       └─> Verify symbol format (SPY.US not SPY)
        │
        ├─> "CSV parse error"
        │   └─> Fix: Stooq changed format
        │       ├─> Manually download CSV, inspect columns
        │       └─> Update parser in orbit/ingest/prices.py
        │
        ├─> "Schema validation failed"
        │   └─> Fix: Data doesn't match expected schema
        │       └─> Check 12-schemas/prices.parquet.schema.md
        │           └─> Update validator or fix data
        │
        └─> "No new rows"
            └─> Diagnosis:
                ├─> Today not a trading day? → Expected, skip
                ├─> Data already ingested? → Check timestamp
                └─> Stooq data delayed? → Retry in 30 mins
```

---

## Flowchart 3: News WebSocket Issues

```
News WebSocket Not Working?
│
├─> Check WS status
    │
    ├─> Run: python -m orbit.ops.check_ws_status
    │   │
    │   ├─> "Not connected"
    │   │   └─> Start WS: python -m orbit.ingest.news --mode ws_daemon
    │   │
    │   └─> "Connected but no messages"
    │       └─> Check subscription
    │           └─> Verify symbols in config ≤ 30 (Basic tier limit)
    │
    └─> Check logs/ingest_news.log
        │
        ├─> "Auth failed"
        │   └─> Fix: Invalid API keys
        │       ├─> Verify ALPACA_API_KEY in .env (WebSocket)
        │       ├─> Verify ALPACA_API_SECRET in .env (WebSocket)
        │       ├─> Verify ALPACA_API_KEY_1 in .env (REST API backfill)
        │       └─> Test keys: curl -u $KEY:$SECRET https://data.alpaca.markets/v1beta1/news
        │
        ├─> "WebSocket closed unexpectedly"
        │   └─> Diagnosis:
        │       ├─> Alpaca service down? → Check status.alpaca.markets
        │       ├─> Network interruption? → Reconnect daemon auto-retries
        │       └─> Code bug? → Review stacktrace in logs
        │
        ├─> "Reconnect loop (>10x in 1 hour)"
        │   └─> Fix: Persistent connection issue
        │       ├─> Check backoff config (initial_ms, max_ms, factor)
        │       ├─> Verify network stability (ping test)
        │       └─> Consider switching to REST backfill mode
        │
        └─> "Messages received but 0 curated items"
            └─> Diagnosis:
                ├─> All items after cutoff? → Check cutoff time (15:30 ET)
                ├─> No SPY/VOO mentions? → Normal if quiet day
                └─> Dedup removed all? → Check novelty threshold
```

---

## Flowchart 4: Reddit API Issues

```
Reddit Ingestion Failed?
│
├─> Check API credentials
    │
    ├─> Test OAuth: python -m orbit.ops.test_reddit_auth
    │   │
    │   ├─> "Auth failed"
    │   │   └─> Fix: Check .env
    │   │       ├─> REDDIT_CLIENT_ID correct?
    │   │       ├─> REDDIT_CLIENT_SECRET correct?
    │   │       └─> User-Agent set? (required by Reddit TOS)
    │   │
    │   └─> "Auth success"
    │       └─> Continue below
    │
    └─> Check logs/ingest_social.log
        │
        ├─> "HTTP 429 Too Many Requests"
        │   └─> Fix: Reddit rate limit hit
        │       ├─> Default: 100 requests per minute
        │       ├─> Wait 1 minute, retry
        │       └─> Reduce query frequency or batch size
        │
        ├─> "HTTP 403 Forbidden"
        │   └─> Diagnosis:
        │       ├─> Banned/suspended account? → Create new Reddit app
        │       ├─> Violating TOS? → Review usage patterns
        │       └─> Missing User-Agent? → Add to config
        │
        ├─> "0 posts found"
        │   └─> Diagnosis:
        │       ├─> No SPY/VOO mentions today? → Normal if quiet
        │       ├─> Query terms too restrictive? → Broaden keywords
        │       └─> Quality filters too strict? → Lower karma/age thresholds
        │
        └─> "High duplicate rate (>80%)"
            └─> Fix: Dedup too aggressive or real bot spam
                ├─> Check simhash threshold (default 0.92)
                ├─> Review rejected posts in data/rejects/social/
                └─> Adjust blacklist if false positives
```

---

## Flowchart 5: Model Performance Degradation

```
Model IC/Sharpe Declining?
│
├─> Check monitoring dashboard
    │
    └─> Rolling 20d IC < 0.01 for 5+ days?
        │
        ├─> YES → Performance drift detected
        │   │
        │   └─> Diagnosis:
        │       │
        │       ├─> Market regime changed?
        │       │   └─> Run regime analysis: python -m orbit.evaluate.regimes
        │       │       ├─> Low performance in high-vol regime?
        │       │       │   └─> Retrain with more high-vol data
        │       │       └─> Low performance when news quiet?
        │       │           └─> Review gating logic (burst thresholds)
        │       │
        │       ├─> Data quality issues?
        │       │   └─> Check data_completeness in features
        │       │       ├─> completeness < 0.9 frequently?
        │       │       │   └─> Fix upstream data sources
        │       │       └─> High NaN rates?
        │       │           └─> Improve imputation or extend history
        │       │
        │       ├─> Feature drift?
        │       │   └─> Run drift check: python -m orbit.ops.check_drift
        │       │       ├─> PSI > 0.25 for key features?
        │       │       │   └─> Retrain model
        │       │       └─> Feature distributions shifted?
        │       │           └─> Update normalization windows
        │       │
        │       └─> Overfitting to recent data?
        │           └─> Review walk-forward splits
        │               └─> Extend training window
        │                   └─> Re-tune hyperparameters
        │
        └─> NO → Temporary fluctuation
            └─> Monitor for 5 more days
                └─> If persists → Trigger retraining
```

---

## Flowchart 6: Backtest Results Don't Match Expectations

```
Backtest Sharpe/Returns Too Low?
│
├─> Review backtest report
    │
    └─> Check metrics
        │
        ├─> IC is good but Sharpe low?
        │   └─> Issue: High transaction costs or poor thresholds
        │       ├─> Check cost_bps + slippage_bps in config
        │       │   └─> Default: 2 bps + 1 bps = 3 bps per trade
        │       │       └─> If trading frequently, costs dominate
        │       │           └─> Fix: Increase threshold to reduce turnover
        │       │
        │       └─> Run threshold sweep
        │           └─> python -m orbit.evaluate.threshold_sweep
        │               └─> Find optimal threshold for Sharpe
        │
        ├─> IC near zero?
        │   └─> Issue: Model not predictive
        │       ├─> Run ablations: python -m orbit.evaluate.ablations
        │       │   └─> Price-only better than All?
        │       │       └─> Text features not helpful
        │       │           └─> Check news/social burst gating
        │       │               └─> Are gates triggering correctly?
        │       │
        │       └─> Check label leakage
        │           └─> Verify cutoff enforcement in features
        │               └─> Review 06-preprocessing/time_alignment_cutoffs.md
        │
        └─> Hit rate ~50% (random)?
            └─> Issue: No signal or overfitting
                ├─> Check train/val/test IC separately
                │   ├─> Train IC high, test IC zero → Overfitting
                │   │   └─> Reduce model complexity (fewer layers, more regularization)
                │   └─> All IC near zero → No signal
                │       └─> Review feature engineering
                │
                └─> Check for data leakage
                    └─> Audit: python -m orbit.ops.audit_leakage
                        └─> Verifies cutoffs, lags, label alignment
```

---

## Quick Diagnostic Commands

```bash
# Check if pipeline is healthy
python -m orbit.ops.healthcheck

# Test all API connections
python -m orbit.ops.test_connections

# Validate today's data
python -m orbit.ops.validate_all --date today

# Check for data gaps
python -m orbit.ops.check_gaps --start 2024-01-01 --end 2024-12-31

# Monitor logs in real-time
tail -f logs/orbit_main.log

# Check disk usage
du -sh data/

# View latest metrics
cat logs/metrics/$(date +%Y-%m-%d).json | jq .
```

---

## Escalation Path

If issue persists after following flowcharts:

1. **Collect diagnostics:**
   ```bash
   python -m orbit.ops.collect_diagnostics --output diagnostics.zip
   ```

2. **Review generated report:**
   - System info, logs, config, recent metrics
   - Data sample snapshots

3. **Create GitHub issue** with:
   - Diagnostic bundle attached
   - Flowchart steps attempted
   - Expected vs actual behavior

4. **Emergency fallback:**
   - If model broken: Revert to last good run_id
   - If data missing: Skip day, use previous features
   - If pipeline critical: Failover to manual scoring

---

## Related Files

* `10-operations/failure_modes_playbook.md` — Detailed failure recovery
* `10-operations/runbook.md` — Daily operations guide
* `10-operations/monitoring_dashboards.md` — Monitoring setup
* `10-operations/data_quality_checks.md` — Data validation
