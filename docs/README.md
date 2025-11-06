
*Last edited: 2025-11-06*

**Purpose:** Guide to navigating the ORBIT documentation tree. Read this first to understand how documentation is organized, then drill into specific modules as needed.

---

## Documentation Structure

```
docs/
├─ README.md                   ← You are here
├─ 00-glossary/
│  └─ glossary.md              Key terms (IC, AUC, gates, leakage, etc.)
├─ 01-overview/
│  ├─ project_scope.md         What v1 covers (SPY/VOO, daily, long/flat)
│  ├─ assumptions_constraints.md  Free data, cutoff, rate limits
│  └─ success_criteria.md      "Good vs Meh" thresholds (IC, Sharpe, stability)
├─ 02-architecture/
│  ├─ system_diagram.md        Text diagram: ingestion → features → fusion → backtest
│  ├─ dataflow.md              Per‑pipe inputs → transforms → outputs
│  ├─ modules_inventory.md     Table of modules, owners, dependencies
│  └─ llm_operator_guide.md    How an LLM reads config & respects anti‑leak rules
├─ 03-config/
│  ├─ config_schema.yaml       Canonical keys (paths, tickers, windows, gates)
│  ├─ sample_config.yaml       Filled example for SPY/VOO
│  ├─ config_reconciliation.md Relationship & differences between 3 config files
│  ├─ env_keys.md              API key storage, User‑Agent conventions
│  └─ cutoffs_timezones.md     Market calendar, ET normalization, cutoff rationale
├─ 04-data-sources/
│  ├─ stooq_prices.md          Symbol patterns, CSV columns, fetch cadence
│  ├─ alpaca_news_ws.md        WebSocket schema, 30‑symbol limit, reconnection
│  ├─ reddit_api.md            OAuth, query patterns, rate limits, subreddit list
│  ├─ gemini_sentiment_api.md  Batch JSONL, RPM/TPM/RPD budgeting
│  ├─ identifiers_mapping.md   Keyword/cashtag mapping for index terms
│  ├─ rate_limits.md           Consolidated table + backoff policy
│  └─ tos_compliance.md        Terms, attribution, retention, PII avoidance
├─ 05-ingestion/
│  ├─ prices_stooq_ingest.md   Job spec, retries, CSV→Parquet, schema validation
│  ├─ news_alpaca_ws_ingest.md WS client lifecycle, dedupe by content hash
│  ├─ social_reddit_ingest.md  Search windows, pagination, dedupe, author metadata
│  ├─ llm_batching_gemini.md   Pre‑filter, batch size, prompt I/O, cost guardrails
│  ├─ storage_layout_parquet.md  Folder hierarchy, partitioning, file naming
│  └─ scheduler_jobs.md        Cronish order, dependency graph
├─ 06-preprocessing/
│  ├─ time_alignment_cutoffs.md  15:30 ET cutoff, publish‑time lag rationale
│  ├─ deduplication_novelty.md   Simhash/cosine clustering, novelty score
│  ├─ mapping_rules_cashtags_keywords.md  Regex/keyword rules, blacklist
│  └─ quality_filters_social.md  Author age/karma, bot heuristics
├─ 07-features/
│  ├─ price_features.md        Momentum, reversal, vol, drawdown, ETF–index basis
│  ├─ news_features.md         Counts, sentiment, source weights, novelty, events
│  ├─ social_features.md       Post count, velocity, cred‑weighted sent, novelty
│  └─ standardization_scaling.md  Cross‑sectional vs rolling z, caps, NA handling
├─ 08-modeling/
│  ├─ targets_labels.md        Return vs excess; classification vs regression
│  ├─ heads_price_news_social.md  Minimal MLP/GBM specs, input tensors, regularization
│  ├─ fusion_gated_blend.md    Gate definitions, final score formula, learnable weights
│  ├─ training_walkforward.md  Train/val/test rolling windows, early stop, seeds
│  └─ hyperparams_tuning.md    Grids, ablation toggles, logging
├─ 09-evaluation/
│  ├─ metrics_definitions.md   IC, AUC, Brier, Sharpe, max DD, turnover
│  ├─ backtest_long_flat_spec.md  Trade at next open/close, cost model, thresholds
│  ├─ ablations_checklist.md   Price‑only vs +News vs +Social vs All
│  ├─ regime_analysis.md       By VIX deciles or realized‑vol terciles
│  ├─ dashboard_spec.md        Plots/tables to render post‑run
│  └─ acceptance_gates.md      Go/No‑Go bands to promote changes
├─ 10-operations/
│  ├─ runbook.md               One‑command daily run, failure recovery
│  ├─ monitoring_dashboards.md Grafana/Prometheus configs, alert rules
│  ├─ troubleshooting_flowchart.md  6 diagnostic flowcharts for common issues
│  ├─ data_quality_checks.md   Row counts, schema checks, freshness, outliers
│  ├─ drift_monitoring.md      Feature drift PSI, performance drift alarms
│  ├─ logging_audit.md         What gets logged, audit trail, sample records
│  └─ failure_modes_playbook.md  WS disconnects, API 429s, missing data day
├─ 11-roadmap/
│  ├─ milestones.md            M0 (price‑only) → M1 (news) → M2 (social) → M3 (calibration)
│  ├─ extend_to_single_stocks.md  Cross‑sectional shift: labels, evaluation
│  └─ future_data_sources.md   Filings, macro, options, short interest
├─ 12-schemas/
│  ├─ prices.parquet.schema.md      Price data schema with validation code
│  ├─ news.parquet.schema.md        News data schema with access patterns
│  ├─ social.parquet.schema.md      Social data schema with credibility weighting
│  └─ features_daily.parquet.schema.md  Feature matrix schema with ML prep examples
├─ 98-test-plans/
│  ├─ test_plan_prices_ingestion.md  Unit/integration tests for price ingestion
│  ├─ test_plan_features.md          Tests for feature computation (price/news/social)
│  └─ test_plan_modeling.md          Tests for model heads, fusion, training
└─ 99-templates/
   ├─ TEMPLATE_module_spec.md
   ├─ TEMPLATE_feature_spec.md
   ├─ TEMPLATE_job_checklist.md
   ├─ TEMPLATE_prompt_gemini.jsonl.md
   ├─ TEMPLATE_config.yaml
   └─ TEMPLATE_test_plan.md
```

---

## How to Use This Documentation

### For LLMs (Claude/ChatGPT)

1. Read `/CLAUDE.md` for **guardrails** and workflow.
2. Read `01-overview/*` for **scope and constraints**.
3. Read `02-architecture/*` for **system design**.
4. Before implementing, read the **specific module spec** under relevant section.
5. After changes, **update the doc's last_edited timestamp**.

### For Humans

1. Start here (docs/README.md).
2. Read `01-overview/project_scope.md` for the big picture.
3. Browse `02-architecture/system_diagram.md` for the pipeline flow.
4. Drill into module specs as needed for implementation details.
5. Use `99-templates/*` when adding new modules or features.

---

## Documentation Conventions

Every documentation file follows these standards:

* **Italic date format:** Every doc begins with an italic last edited date:
  ```markdown
  *Last edited: YYYY-MM-DD*
  ```

* **Related Files sections:** All docs include cross-references to related documentation:
  ```markdown
  ## Related Files
  
  * `path/to/related_doc.md` — Description
  ```

* **Clear structure:** Explicit sections with purpose, inputs, outputs, procedures
* **Point-in-time discipline:** Anti-leak constraints and cutoffs clearly stated
* **Acceptance criteria:** Each spec includes verifiable checks
* **Executable examples:** Schema files include validation code, test plans include pytest code

---

## Quick References

| Topic | File |
|-------|------|
| **Glossary** | `00-glossary/glossary.md` |
| **Project scope** | `01-overview/project_scope.md` |
| **Success criteria** | `01-overview/success_criteria.md` |
| **Assumptions & constraints** | `01-overview/assumptions_constraints.md` |
| **System architecture** | `02-architecture/system_diagram.md` |
| **Pipeline dataflow** | `02-architecture/dataflow.md` |
| **Config schema** | `03-config/config_schema.yaml` |
| **Config reconciliation** | `03-config/config_reconciliation.md` |
| **API rate limits** | `04-data-sources/rate_limits.md` |
| **Daily job scheduler** | `05-ingestion/scheduler_jobs.md` |
| **Cutoff rules** | `06-preprocessing/time_alignment_cutoffs.md` |
| **Feature definitions** | `07-features/*.md` |
| **Model architecture** | `08-modeling/heads_price_news_social.md`, `fusion_gated_blend.md` |
| **Evaluation metrics** | `09-evaluation/metrics_definitions.md` |
| **Backtest specification** | `09-evaluation/backtest_long_flat_spec.md` |
| **Operations runbook** | `10-operations/runbook.md` |
| **Monitoring & alerts** | `10-operations/monitoring_dashboards.md` |
| **Troubleshooting** | `10-operations/troubleshooting_flowchart.md` |
| **Roadmap & milestones** | `11-roadmap/milestones.md` |
| **Data schemas** | `12-schemas/*.md` |
| **Test plans** | `98-test-plans/*.md` |
| **Templates** | `99-templates/*.md` |

---

**Questions?** Check the glossary (`00-glossary/glossary.md`) for term definitions, or browse the docs tree for specific topics.

---

## Related Files

* `01-overview/project_scope.md` — Project overview and scope
* `02-architecture/system_diagram.md` — System architecture with Mermaid flowchart
* `03-config/config_reconciliation.md` — Configuration file relationships
* `10-operations/monitoring_dashboards.md` — Monitoring and alerting setup
* `10-operations/troubleshooting_flowchart.md` — Diagnostic flowcharts
* `98-test-plans/*.md` — Test plan suite (3 files)
* `99-templates/*.md` — Documentation templates
