# ORBIT — Scheduler & Jobs

*Last edited: 2025-11-05*

## Purpose

Define the **authoritative daily run order**, timing windows (ET), dependencies, and retry/idempotency rules so an LLM or human can orchestrate the entire pipeline deterministically for any target date *T*.

---

## Daily schedule (ET)

> All times are **guidelines**; actual runs are dependency‑driven. The **cutoff** is hard: only text with `published_at/created_utc ≤ 15:30 ET` on *T* is eligible.

* **09:30 → 16:00**

  * `ingest:news --date T --watch`  (continuous WS capture)
  * `ingest:social --date T --batches 2-6`  (poll Reddit a few times; denser near midday/close)
* **15:30**

  * **Cutoff applied** for text on day *T* (no items after this enter *T* features)
* **16:05**

  * `ingest:prices --date T`  (Stooq EOD fetch for SPY/VOO/^SPX)
* **16:15**

  * `preprocess:time_align --date T`  (normalize tz to ET; drop >15:30)
  * `preprocess:dedupe_text --date T`  (cluster near‑dups; compute novelty)
  * `preprocess:mapping --date T`  (apply identifiers rules)
* **16:25** *(optional)*

  * `llm_batching_gemini --date T`  (score uncertain/high‑impact items; merge results)
* **16:35**

  * `features:build --date T`  (assemble one daily feature row; standardize z‑scores)
* **16:40**

  * `train:fit --roll --date T`  (walk‑forward step using history ≤ *T*)
  * `score:daily --date T`  (produce `Score_T`)
* **16:55**

  * `backtest:run --through T`  (trade at next open/close per config; with costs)
  * `eval:ablations --through T`
  * `eval:regimes --through T`
* **17:10**

  * `reports:generate --through T`  (metrics, plots, QC summaries)

---

## Orchestration CLI

A single command should run the full DAG for a target date:

```sh
orchestrate:daily --date 2025-11-04 --run_id auto --strict
```

**Flags**

* `--date`  Target market date *T* (YYYY-MM-DD)
* `--run_id`  Auto or provided UUID; propagated to all jobs
* `--strict`  Fail fast on any upstream job failure; do not continue
* `--resume`  Skip completed stages for *T* if artifacts exist and pass QC

---

## DAG / dependencies

```
            ingest:news(T) ┐
            ingest:social(T) ┴──> preprocess:* (T) ──> [optional] llm_batching_gemini(T)
            ingest:prices(T) ┘                          │
                                                       ▼
                                                features:build(T)
                                                       ▼
                                         train:fit(≤T) & score:daily(T)
                                                       ▼
                                        backtest:run(≤T) → eval:* → reports
```

* `features:build(T)` requires curated text **and** prices for *T*.
* `train:fit` uses history up to *T* (walk‑forward windows from config).
* `backtest:run` simulates trades using scores/labels up to *T*.

---

## Idempotency & reruns

* Every job is **idempotent** for a given `(date, run_id)` and writes **append‑only** Parquet with anti‑joins on known keys.
* Re‑running *T* with a **new** `run_id` is allowed; downstream tasks must reference the chosen `run_id` explicitly to ensure reproducibility in `reports/`.
* `--resume` skips stages whose outputs already exist **and** pass QC checks.

---

## Retries & degraded modes

* **Network/API errors**: exponential backoff with jitter; bounded retries (default 3–5).
* **Alpaca WS outage**: proceed with `count=0` text aggregates; downstream **gates** will down‑weight text.
* **Reddit quota issues**: reduce batch frequency; mark partial day; still proceed.
* **LLM failure**: skip escalation; keep tier‑1 sentiment.
* **Missing prices**: mark market holiday/closed and skip *T*; process on next valid trading day.

---

## Monitoring & logs

* Each job writes to `logs/<job>/<date>/<run_id>.log` with: start/stop times, rows processed, cutoff enforcement stats, retry counts.
* Emit a compact **QC table** to `reports/qc/<date>.parquet` (row counts, late‑item drops, dup rates, novelty stats).

---

## Acceptance checklist

* A single command kicks off the full DAG for *T* and exits **non‑zero** on failure.
* All cutoff and lag rules are enforced at or before `preprocess:*`.
* Reruns of *T* are idempotent and selectable via `run_id` in reports.
* Degraded modes are defined and produce valid (if weaker) artifacts.
* Logs and QC artifacts are written for every stage.

---

## Related Files

* `02-architecture/modules_inventory.md` — Module dependencies
* `10-operations/runbook.md` — Daily operations
* `10-operations/failure_modes_playbook.md` — Job failure recovery
