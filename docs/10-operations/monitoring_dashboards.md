# ORBIT — Monitoring Dashboard Configuration

*Last edited: 2025-11-06*

## Purpose

Define monitoring dashboards, alerting rules, and observability setup for ORBIT pipeline. Supports both Grafana and simple file-based monitoring for resource-constrained environments.

---

## Architecture

**Monitoring Stack Options:**

1. **Full Stack (Recommended for Production):**
   - Grafana: Visualization
   - Prometheus: Metrics collection
   - Loki: Log aggregation
   - AlertManager: Alert routing

2. **Minimal Stack (Development/Bootstrap):**
   - JSON metrics files: `logs/metrics/YYYY-MM-DD.json`
   - Simple Python dashboard: `python -m orbit.ops.dashboard`
   - Email/Slack webhooks: Direct from Python

---

## Metrics to Track

### 1. Data Ingestion Metrics

**Prices:**
- `orbit_prices_rows_ingested` (gauge): Rows ingested per day
- `orbit_prices_fetch_duration_seconds` (histogram): Stooq API response time
- `orbit_prices_errors_total` (counter): Fetch failures

**News:**
- `orbit_news_items_ingested` (gauge): News items per day
- `orbit_news_websocket_reconnects` (counter): Alpaca WS reconnections
- `orbit_news_cutoff_violations` (counter): Items after 15:30 ET

**Social:**
- `orbit_social_posts_ingested` (gauge): Reddit posts per day
- `orbit_social_api_rate_limits` (counter): 429 responses
- `orbit_social_quality_filtered` (counter): Posts filtered by quality rules

### 2. Feature Pipeline Metrics

- `orbit_features_nan_rate` (gauge by feature): NaN percentage per feature
- `orbit_features_compute_duration` (histogram): Feature computation time
- `orbit_features_z_score_outliers` (counter): Features with |z| > 5

### 3. Model Performance Metrics

- `orbit_model_ic` (gauge): Information Coefficient (rolling 20d)
- `orbit_model_sharpe` (gauge): Sharpe ratio (rolling 60d)
- `orbit_model_hit_rate` (gauge): Classification accuracy
- `orbit_model_calibration_error` (gauge): Brier score
- `orbit_backtest_max_drawdown` (gauge): Current max drawdown

### 4. System Health Metrics

- `orbit_pipeline_duration_seconds` (histogram): End-to-end job time
- `orbit_pipeline_last_success_timestamp` (gauge): Last successful run
- `orbit_disk_usage_bytes` (gauge): Data directory size
- `orbit_memory_peak_mb` (gauge): Peak memory usage

---

## Grafana Dashboard Configuration

### Dashboard: ORBIT - Daily Operations

**File:** `monitoring/grafana/orbit_dashboard.json`

```json
{
  "dashboard": {
    "title": "ORBIT - Daily Operations",
    "tags": ["orbit", "trading", "ml"],
    "timezone": "America/New_York",
    "panels": [
      {
        "title": "Data Ingestion Status",
        "type": "stat",
        "targets": [
          {
            "expr": "orbit_prices_rows_ingested",
            "legendFormat": "Prices"
          },
          {
            "expr": "orbit_news_items_ingested",
            "legendFormat": "News"
          },
          {
            "expr": "orbit_social_posts_ingested",
            "legendFormat": "Social"
          }
        ],
        "gridPos": {"x": 0, "y": 0, "w": 8, "h": 4}
      },
      {
        "title": "Model Performance (Rolling 20d IC)",
        "type": "graph",
        "targets": [
          {
            "expr": "orbit_model_ic",
            "legendFormat": "Information Coefficient"
          }
        ],
        "gridPos": {"x": 8, "y": 0, "w": 16, "h": 8},
        "yaxes": [
          {"min": -0.1, "max": 0.1, "label": "IC"}
        ]
      },
      {
        "title": "Feature NaN Rates",
        "type": "heatmap",
        "targets": [
          {
            "expr": "orbit_features_nan_rate",
            "legendFormat": "{{feature}}"
          }
        ],
        "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8}
      },
      {
        "title": "Pipeline Execution Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(orbit_pipeline_duration_seconds_sum[5m])/rate(orbit_pipeline_duration_seconds_count[5m])",
            "legendFormat": "Avg Duration"
          }
        ],
        "gridPos": {"x": 12, "y": 4, "w": 12, "h": 8}
      },
      {
        "title": "API Health",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(orbit_news_websocket_reconnects[1h])",
            "legendFormat": "WS Reconnects/hr"
          },
          {
            "expr": "rate(orbit_social_api_rate_limits[1h])",
            "legendFormat": "Reddit 429s/hr"
          }
        ],
        "gridPos": {"x": 0, "y": 12, "w": 8, "h": 4}
      },
      {
        "title": "Backtest Equity Curve",
        "type": "graph",
        "targets": [
          {
            "expr": "orbit_backtest_equity",
            "legendFormat": "Strategy"
          },
          {
            "expr": "orbit_backtest_benchmark_equity",
            "legendFormat": "Buy & Hold"
          }
        ],
        "gridPos": {"x": 8, "y": 12, "w": 16, "h": 8}
      }
    ]
  }
}
```

---

## Prometheus Scrape Configuration

**File:** `monitoring/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'orbit-production'

scrape_configs:
  - job_name: 'orbit-metrics'
    static_configs:
      - targets: ['localhost:9091']  # Pushgateway
    honor_labels: true

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
```

**Push metrics from Python:**

```python
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

registry = CollectorRegistry()
g = Gauge('orbit_model_ic', 'Information Coefficient', registry=registry)
g.set(0.023)

push_to_gateway('localhost:9091', job='orbit_daily', registry=registry)
```

---

## Alert Rules

**File:** `monitoring/prometheus/alerts.yml`

```yaml
groups:
  - name: orbit_data_alerts
    interval: 5m
    rules:
      - alert: NoDataIngested
        expr: orbit_prices_rows_ingested == 0
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "No price data ingested today"
          description: "Price ingestion returned 0 rows for {{ $labels.symbol }}"

      - alert: HighNaNRate
        expr: orbit_features_nan_rate > 0.10
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High NaN rate in features"
          description: "Feature {{ $labels.feature }} has {{ $value }}% NaN rate"

      - alert: WebSocketReconnects
        expr: rate(orbit_news_websocket_reconnects[1h]) > 5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Frequent Alpaca WebSocket reconnections"
          description: "{{ $value }} reconnects per hour"

      - alert: ModelPerformanceDegradation
        expr: orbit_model_ic < 0.01
        for: 5d
        labels:
          severity: warning
        annotations:
          summary: "Model IC below threshold"
          description: "Rolling 20d IC is {{ $value }}, below 0.01 threshold"

      - alert: PipelineStale
        expr: (time() - orbit_pipeline_last_success_timestamp) > 86400
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "Pipeline hasn't run in 24+ hours"
          description: "Last successful run: {{ $value }}s ago"

  - name: orbit_system_alerts
    interval: 5m
    rules:
      - alert: HighDiskUsage
        expr: orbit_disk_usage_bytes > 100e9  # 100GB
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Data directory exceeds 100GB"
          description: "Current usage: {{ $value | humanize }}B"

      - alert: SlowPipeline
        expr: histogram_quantile(0.95, orbit_pipeline_duration_seconds) > 3600
        for: 3d
        labels:
          severity: warning
        annotations:
          summary: "Pipeline taking >1 hour (p95)"
          description: "p95 duration: {{ $value | humanizeDuration }}"
```

---

## Minimal Dashboard (Python-Based)

**For environments without Grafana:**

**File:** `orbit/ops/dashboard.py`

```python
#!/usr/bin/env python3
"""
Simple HTML dashboard for ORBIT monitoring.
Run: python -m orbit.ops.dashboard
Serves at http://localhost:8000
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def dashboard():
    # Load latest metrics
    today = datetime.now().strftime('%Y-%m-%d')
    metrics_file = Path(f'logs/metrics/{today}.json')
    
    if metrics_file.exists():
        with open(metrics_file) as f:
            metrics = json.load(f)
    else:
        metrics = {}
    
    # Load last 30 days IC
    ic_data = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        mfile = Path(f'logs/metrics/{date}.json')
        if mfile.exists():
            with open(mfile) as f:
                m = json.load(f)
                ic_data.append({'date': date, 'ic': m.get('model_ic', None)})
    
    df_ic = pd.DataFrame(ic_data).sort_values('date')
    
    return render_template('dashboard.html', 
                           metrics=metrics,
                           ic_series=df_ic.to_dict('records'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

**Template:** `orbit/ops/templates/dashboard.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>ORBIT Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <h1>ORBIT Monitoring Dashboard</h1>
    <h2>Today's Metrics ({{ metrics.date }})</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Prices Ingested</td><td>{{ metrics.prices_rows }}</td></tr>
        <tr><td>News Items</td><td>{{ metrics.news_count }}</td></tr>
        <tr><td>Social Posts</td><td>{{ metrics.social_posts }}</td></tr>
        <tr><td>Model IC (20d)</td><td>{{ "%.4f"|format(metrics.model_ic) }}</td></tr>
        <tr><td>Sharpe (60d)</td><td>{{ "%.2f"|format(metrics.sharpe_60d) }}</td></tr>
    </table>
    
    <h2>Information Coefficient (Last 30 Days)</h2>
    <div id="ic-chart"></div>
    
    <script>
        var ic_data = {{ ic_series | tojson }};
        var trace = {
            x: ic_data.map(d => d.date),
            y: ic_data.map(d => d.ic),
            type: 'scatter',
            mode: 'lines+markers'
        };
        Plotly.newPlot('ic-chart', [trace], {
            yaxis: {range: [-0.05, 0.10], title: 'IC'},
            xaxis: {title: 'Date'}
        });
    </script>
</body>
</html>
```

---

## Alert Notification Setup

### Email Alerts

```python
# orbit/ops/alerts.py
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, body, to_email='ops@example.com'):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'orbit@example.com'
    msg['To'] = to_email
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('orbit@example.com', 'password')
        server.send_message(msg)

# Usage
if pipeline_failed:
    send_alert(
        'ORBIT Pipeline Failure',
        f'Pipeline failed at step: {step}\nError: {error}'
    )
```

### Slack Alerts

```python
import requests

def send_slack_alert(message, webhook_url):
    payload = {
        'text': message,
        'username': 'ORBIT Bot',
        'icon_emoji': ':chart_with_upwards_trend:'
    }
    requests.post(webhook_url, json=payload)

# Usage
if model_ic < 0.01:
    send_slack_alert(
        f'⚠️ Model IC dropped to {model_ic:.4f} (below 0.01 threshold)',
        'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    )
```

---

## Related Files

* `10-operations/runbook.md` — Daily operations guide
* `10-operations/drift_monitoring.md` — Performance drift detection
* `10-operations/failure_modes_playbook.md` — Error recovery procedures
* `10-operations/data_quality_checks.md` — Data validation rules
