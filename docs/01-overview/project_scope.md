# ORBIT — Project Scope

*Last edited: 2025-11-05*

## Purpose

Define the boundaries, goals, deliverables, and non‑goals for **ORBIT v1** so an LLM or engineer can implement the system end‑to‑end without scope drift.

## v1 Objective (index‑first, tri‑modal)

* **Asset focus:** S&P 500 tracker (train on `SPY`, validate on `VOO`).
* **Horizon/frequency:** **daily**, next‑day prediction.
* **Modalities:** **Prices** (Stooq OHLCV), **News** (Alpaca news WebSocket), **Social** (Reddit API + optional Gemini escalation).
* **Signal:** one daily score (probability/expected return) produced by three heads + **gated fusion**.
* **Strategy for evaluation:** **long/flat** on SPY/VOO with realistic costs.

## In‑scope

* Free data pipelines: Stooq (CSV), Alpaca news WS (≤30 symbols), Reddit API.
* Point‑in‑time text handling: 15:30 ET cutoff, publish‑time lags.
* Feature sets for each modality + rolling standardization.
* Minimal models: small MLPs or tree models for heads; simple learned gates for fusion.
* Rolling **walk‑forward** training/validation/testing.
* Backtest framework with costs, thresholds, ablations, and regime analysis.
* Reports: metrics, plots, and run logs; Parquet artifacts.

## Out‑of‑scope (v1)

* Single‑stock cross‑sectional portfolios.
* Intraday microstructure (LOB), options data, paid alternative data.
* Live trading connectivity/orders (paper or real). Backtest only.
* Macro/filings ingestion (reserved for roadmap).

## Deliverables

* **Working pipeline** (CLI tasks) that runs: ingest → preprocess → features → train → backtest.
* **Reports** under `reports/` (metrics, ablations, regime slices).
* **Data lake** under `data/` (prices, news, social, features) as Parquet. The canonical data lake is hosted on a central Ubuntu machine and is accessible to the team via a secure Tailscale connection. Developers have per-user userspaces on the same host (personal workspaces) where they run pipeline tasks and mount or read the shared `data/` lake.
* **Docs** in `docs/` describing assumptions, constraints, and acceptance checks.

## Users

* LLM agents (Claude/ChatGPT) operating via `/CLAUDE.md`.
* Engineers/data scientists running on a laptop with Python 3.11+.

## Job graph (daily)

1. `ingest:prices` (Stooq → Parquet)
2. `ingest:news` (Alpaca WS → normalized rows)
3. `ingest:social` (Reddit pulls → normalized rows)
4. `preprocess:*` (time alignment, dedupe, mapping)
5. `features:build` (price/news/social + z‑scores)
6. `train:fit` (three heads + gated fusion, walk‑forward)
7. `backtest:run` (long/flat, costs)

## Acceptance of scope

* All interfaces and behaviors above must be implemented and documented.
* Any new file or dependency outside this scope must be justified in `docs/` first (see `/CLAUDE.md`).

---

## Related Files

* `01-overview/assumptions_constraints.md` — Project constraints
* `01-overview/success_criteria.md` — Success metrics
* `02-architecture/system_diagram.md` — System overview
* `11-roadmap/milestones.md` — Development roadmap
