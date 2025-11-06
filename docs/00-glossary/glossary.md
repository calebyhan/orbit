# ORBIT Glossary

*Last edited: 2025-11-05*

**Modality** — A data type (prices, news, social). We use three.

**Feature** — A numeric descriptor computed from raw data (e.g., 5‑day momentum).

**Head** — A small model per modality that outputs a scalar score.

**Fusion** — Combining head scores into one signal (we use a **gated blend**).

**Gate** — A learned weight (0..1) that rises on “busy” days (e.g., high news_count_z).

**Cutoff** — Daily time boundary (15:30 ET) after which we **don’t** use text for that day’s decision.

**Point‑in‑time** — Only data available by the cutoff; prevents look‑ahead bias.

**Leakage** — Using future info. Fix with lags, cutoffs, and point‑in‑time tables.

**IC (Information Coefficient)** — Spearman correlation between scores and next returns; small but stable > 0 is good.

**AUC** — Probability the model ranks an up day above a down day (binary task).

**Brier score** — Mean squared error of predicted probabilities (lower better).

**Sharpe** — Mean excess return / std dev (annualized). Our main strategy metric.

**Max drawdown** — Worst peak‑to‑trough equity loss in backtest.

**Turnover** — % of portfolio traded per rebalance; drives costs.

**Excess return** — Asset return minus benchmark (here SPY − ^SPX).

**Walk‑forward** — Train on past months, validate next month, test next; then roll forward.

**Ablation** — Re‑run with one modality toggled off to measure its contribution.

**Novelty (text)** — Dissimilarity to prior 7‑day headlines/posts; discourages echo.

**Dedup** — Merge near‑identical items (same story across sources) before counting.

**Buzz z‑score** — Today’s post/article volume relative to 60‑day average.

**Credibility‑weighted sentiment** — Sentiment weighted by author reputation (capped).

**Coverage** — Fraction of days we take a position under the trading rule.

**Regime** — Market state bucket (e.g., low/med/high realized vol) used for analysis/gates.

---

## Related Files

* `09-evaluation/metrics_definitions.md` — Metric definitions
* `08-modeling/fusion_gated_blend.md` — Gating concepts
* `06-preprocessing/time_alignment_cutoffs.md` — Leakage prevention
