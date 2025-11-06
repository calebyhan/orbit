# ORBIT — Modules Inventory

*Last edited: 2025-11-05*

A reference table for every runnable module: purpose, inputs, outputs, dependencies, and acceptance checks.

| Module (CLI)             | Purpose                          | Inputs                                | Outputs                                | Depends on         | Acceptance checks                                      |
| ------------------------ | -------------------------------- | ------------------------------------- | -------------------------------------- | ------------------ | ------------------------------------------------------ |
| `ingest:prices`          | Fetch Stooq CSV → Parquet        | Stooq endpoints; `orbit.yaml` symbols | `data/raw/prices/`                     | calendar           | rows ≥ prev day; dates monotone; schema valid          |
| `ingest:news`            | Stream Alpaca News WS            | Alpaca WS creds; subscribe list       | `data/raw/news/`                       | net; backoff       | WS connects; upserts by `msg_id`; no dup hashes        |
| `ingest:social`          | Pull Reddit posts/comments       | Reddit OAuth; queries                 | `data/raw/social/`                     | rate‑limit handler | 429‑safe; dedup by `post_id`; bot filters applied      |
| `preprocess:time_align`  | Normalize tz; enforce cutoffs    | raw tables                            | `data/curated/*`                       | calendar           | only records ≤ 15:30 ET; tz = ET                       |
| `preprocess:dedupe_text` | Cluster duplicates; novelty      | raw/curated text                      | `curated/news`, `curated/social`       | simhash/cosine     | dup rate logged; novelty in [0,1]                      |
| `preprocess:mapping`     | Map keywords → index             | curated social/news                   | mapped tables                          | rules              | false‑positive rate < threshold                        |
| `features:build`         | Assemble daily row               | curated prices/news/social            | `data/features/features_daily.parquet` | preprocess*        | row per trading day; NA rules honored; z‑scores finite |
| `train:heads`            | Fit price/news/social heads      | features table                        | `models/heads/*`                       | features           | val loss improves vs baseline                          |
| `train:fusion`           | Fit gated blend                  | head preds + features                 | `models/fusion/*`                      | train:heads        | gates bounded [0,1]; fusion > avg(heads) on val        |
| `score:daily`            | Produce Score_t                  | models + features(T)                  | `data/scores/score.parquet`            | train:*            | reproducible with seed                                 |
| `backtest:run`           | Long/flat strategy               | scores + labels                       | `reports/backtest/*`                   | score:daily        | includes costs; threshold sweep; metrics computed      |
| `eval:ablations`         | Price vs +News vs +Social vs All | features                              | `reports/ablations/*`                  | train:*            | report shows deltas with CIs                           |
| `eval:regimes`           | Slice by vol/news/social         | features + labels                     | `reports/regimes/*`                    | backtest           | per‑slice stats logged                                 |
| `ops:checks`             | Data quality & freshness         | raw/curated/features                  | `reports/qc/*`                         | all ingest         | schema & freshness checks pass                         |

## Notes

* All modules accept a `--run_id` (uuid) and log to `logs/run_id/*.log`.
* Config defaults live in `docs/03-config/sample_config.yaml` and are overridden by `orbit.yaml` at repo root.

## Acceptance checklist

* Every module has purpose, inputs, outputs, dependencies, checks.
* All critical paths (ingest → preprocess → features → train → score → backtest) are represented.
* QC and evaluation modules are included.

---

## Related Files

* `02-architecture/system_diagram.md` — Architecture overview
* `05-ingestion/scheduler_jobs.md` — Module execution schedule
