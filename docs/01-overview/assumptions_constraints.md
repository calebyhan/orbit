# ORBIT — Assumptions & Constraints

*Last edited: 2025-11-05*

## Assumptions

* **Free data only** in v1: Stooq prices, Alpaca news WS (Basic), Reddit API; optional Gemini for social sentiment escalation within free quotas.
* **Daily model**: predict next session using only information available by **15:30 ET** on day *T*.
* **Execution assumption** (for backtests): trade at next session’s open (or close), with fixed costs per side.
* **Benchmarking**: use `^SPX` for excess‑return labels and sanity checks.
* **Environment**: Python 3.11+, local filesystem; no external DB required.
* **Storage**: Parquet files partitioned by date/dataset; append‑only.
* **Reproducibility**: fixed random seeds, deterministic preprocessing, logged configs.

## Data constraints

* **Stooq**: CSV downloads (no official JSON). Respect politeness (throttle, caching). Symbols: `SPY.US`, `VOO.US`, `^SPX`.
* **Alpaca News**: WebSocket on Basic plan; **≤30 symbols** subscribed concurrently. Expect occasional disconnects; implement backoff + resume.
* **Reddit API**: OAuth; rate limits apply (batch requests, exponential backoff). Filter bots/low‑cred authors.
* **Gemini (optional)**: batch escalated posts only; keep within free RPM/TPM/RPD. Fallback to local sentiment when unavailable.

## Modeling constraints

* **Anti‑leak rules**: 15:30 ET cutoff; apply publish‑time lags; no post‑cutoff edits included. No future prices or revised fundamentals.
* **Feature discipline**: declare formulas/windows in `docs/07-features/*`; cap outliers; define NA rules.
* **Model simplicity**: small heads (MLP/tree) and a learnable **gated blend**; avoid high‑capacity architectures in v1.
* **Walk‑forward**: strict rolling train/val/test; no random shuffles across time.

## Operational constraints

* **Error handling**: missing data for a day ⇒ compute price features only and **flatten** exposure in backtests.
* **Logging & audit**: persist raw ingests and feature rows with run IDs; maintain reproducible artifacts in `reports/`.
* **Compliance**: follow source TOS; no PII; set proper `User-Agent` headers; document key usage.

## Change control

* Any deviation from these constraints must be proposed by editing the relevant `docs/` spec (update the **Last edited** date) prior to implementation.

---

## Related Files

* `01-overview/project_scope.md` — Project scope
* `04-data-sources/rate_limits.md` — Rate limit constraints
* `03-config/cutoffs_timezones.md` — Time cutoff constraints
