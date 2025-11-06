# ORBIT — Scoring (Daily)

*Last edited: 2025-11-05*

## Purpose

Produce the **single fused score** for day *T* using frozen head models and the gated fusion parameters, then persist it for backtesting and live use.

## Inputs

* `data/features/features_daily.parquet` (row for *T*)
* Models:

  * `models/heads/{price,news,social}/<run_id>/<window>/model.pkl` (+ optional `calibrator.pkl`)
  * `models/fusion/<run_id>/<window>/fusion_params.json` (+ optional `calibrator.pkl`)
* Config: `orbit.yaml` (`training.split`, `fusion.*`, `backtest.execution.trade_at`)

## Outputs

* `data/scores/<run_id>/scores.parquet` (append):

  * `date`
  * `price_head_score_t`, `news_head_score_t`, `social_head_score_t`
  * `fused_score_t` (probability for classification or expected bps for regression)
  * `window_id`, `run_id`

## Procedure

1. **Load features** for *T*; if missing, abort scoring for *T*.
2. **Select window artifacts** whose training window covers *T*.
3. **Score heads**:

   * Classification: `p_k = calibrator_k(model_k(x_k))` if calibrator exists, else raw probability.
   * Regression: `yhat_k = model_k(x_k)` (bps).
4. **Apply fusion** (see `08-modeling/fusion_gated_blend.md`) to get `fused_score_t`.
5. **Write** a single row for *T* into `data/scores/<run_id>/scores.parquet`.

## Pseudocode

```python
xT = load_features(T)
p_price = score_head('price', xT)
p_news  = score_head('news',  xT)
p_soc   = score_head('social',xT)
p_fuse  = fuse(p_price, p_news, p_soc, gates_from(xT))
append_scores(T, p_price, p_news, p_soc, p_fuse)
```

## Acceptance checklist

* Exactly **one** scored row per trading day *T*.
* Head scores use the correct window artifacts for *T*.
* Fusion parameters match the window and respect gate constraints.
* Scores are reproducible given the same `run_id` and config.

---

## Related Files

* `08-modeling/heads_price_news_social.md` — Scoring models
* `08-modeling/fusion_gated_blend.md` — Score fusion
* `09-evaluation/backtest_rules.md` — Backtest integration
