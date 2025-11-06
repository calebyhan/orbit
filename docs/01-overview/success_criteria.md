# ORBIT — Success Criteria

*Last edited: 2025-11-05*

## What “good” looks like (daily, index‑first)

### Model layer (next‑day target)

* **Daily IC (Spearman)**: **0.01–0.02** good; **≥0.03** great.
* **AUC (up/down)**: **0.54–0.56** good; **≥0.57** great.
* **Calibration (Brier)**: lower than price‑only baseline; monotone reliability curve.

### Strategy layer (long/flat on SPY/VOO, after costs)

* **Hit‑rate (when in trade)**: **53–55%** good; **≥56%** great.
* **Annualized Sharpe**: **0.3–0.5** good; **≥0.6** great.
* **Max drawdown**: not worse than buy‑and‑hold over the same window; improves with gates.
* **Coverage**: 30–70% of days (depends on decision threshold).

### Stability

* **Rolling monthly IC**: median > 0 in **≥60%** of months (good), **≥70%** (great).
* **By regime**: positive contribution from text on high‑news/high‑buzz days; no collapse in quiet regimes.

## Required evaluations

1. **Ablations**: Price‑only vs +News vs +Social vs All; show lift on text‑burst days.
2. **Regime slices**: by realized‑vol terciles and news/social count‑z deciles.
3. **Cost sensitivity**: +/− 2× baseline bps; confirm robustness.
4. **Leak checks**: enforce 15:30 ET cutoff; publish‑time lags; verify no future joins.
5. **Reproducibility**: same seed + inputs ⇒ identical metrics within tolerance.

## Promotion criteria (to single‑stock phase)

* One full out‑of‑sample year where:

  * Rolling Sharpe median **≥0.4** after costs, and
  * Monthly IC > 0 in **≥60%** of months, and
  * Text‑gated days improve Sharpe vs price‑only.

## Operational SLOs (guidance)

* **Daily pipeline** completes on a laptop within a practical window.
* **Data freshness**: previous session’s artifacts available before next open.
* **Fault handling**: WS/API outage ⇒ record gap; default to price‑only; flatten exposure.

## Acceptance

A version is “Accepted for v1” when it meets **all Required evaluations** and at least the **Good** bands for Model + Strategy + Stability.

---

## Related Files

* `09-evaluation/metrics_definitions.md` — Evaluation metrics
* `09-evaluation/acceptance_gates.md` — Acceptance thresholds
* `01-overview/project_scope.md` — Project objectives
