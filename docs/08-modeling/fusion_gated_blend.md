# ORBIT — Fusion: Gated Blend

*Last edited: 2025-11-05*

## Purpose

Combine the three per‑modality head scores into a **single daily signal** using **learned base weights** and **data‑driven gates** that up‑weight text on busy/novel days while remaining stable otherwise.

---

## Inputs

Per day *T* (already point‑in‑time safe):

* Head scores: `price_head_score_t`, `news_head_score_t`, `social_head_score_t` (probabilities for classification or expected bps for regression).
* Gate features (from 07‑features):

  * News gates: `gate_news_intensity`, `gate_news_novelty`
  * Social gates: `gate_soc_intensity`, `gate_soc_novelty`
* Optional: additional regime covariates (e.g., `rv_10d_spx`).

## Output

* **Classification:** `p_up_fused_t ∈ [0,1]`
* **Regression:** `ret_fused_t` (bps)

---

## Formulation (classification)

Let base weights ( w = (w_p, w_n, w_s) ) with ( w_k ≥ 0, \sum w_k = 1 ).

Define **gate activations** (0..1) via a sigmoid over linear terms:
[
g_n = \sigma(\alpha_{n0} + \alpha_{n1} \cdot \text{gate_news_intensity} + \alpha_{n2} \cdot \text{gate_news_novelty})
]
[
g_s = \sigma(\alpha_{s0} + \alpha_{s1} \cdot \text{gate_soc_intensity} + \alpha_{s2} \cdot \text{gate_soc_novelty})
]

Blend weights with a **convex re‑normalization**:
[
\tilde{w}_p = w_p \cdot (1 - \beta_n g_n) \cdot (1 - \beta_s g_s),\quad
\tilde{w}_n = w_n \cdot (1 + \beta_n g_n),\quad
\tilde{w}_s = w_s \cdot (1 + \beta_s g_s)
]
Normalize: ( \bar{w}_k = \tilde{w}_k / \sum_j \tilde{w}_j ).

Final probability:
[
p^{fuse}_t = \bar{w}_p p^{price}_t + \bar{w}_n p^{news}_t + \bar{w}_s p^{social}_t
]

Parameters to learn: ( w, \alpha_{n*}, \alpha_{s*}, \beta_n, \beta_s ).

### Regression variant

Replace probabilities with expected returns and minimize squared error on `label_ret_bps`. Clip extreme returns in training (e.g., ±300 bps) if enabled.

---

## Training

* **Objective:**

  * Classification: minimize **logloss** of ( p^{fuse}_t ) vs `label_updown` on **validation** slices within each walk‑forward window.
  * Regression: minimize **RMSE** vs `label_ret_bps`.
* **Procedure (per window):**

  1. Freeze head models; compute head scores on train/val.
  2. Optimize ( w, \alpha, \beta ) on **validation** via small gradient‑based optimizer or grid search.
  3. Enforce constraints: ( w_k ≥ 0 ), sum to 1; ( \beta_* ≥ 0 ); regularize ( |\alpha|_2 ) to avoid over‑reactive gates.
* **Initialization:** from config `fusion.weights_init` (e.g., `w_p=0.6, w_n=0.2, w_s=0.2`); ( \alpha=0, \beta=1 ).

### Regularization & stability

* **L2** on (\alpha), small **L1** on ((\beta_n, \beta_s)) to keep gates conservative.
* Cap gate outputs: optionally clip ( g_* \in [0, 0.95] ) in training.

---

## Scoring (daily)

Given day *T* head scores and gate inputs:

```python
p_price, p_news, p_social = head_scores[T]
# gates
z_n = a_n0 + a_n1*gate_news_intensity[T] + a_n2*gate_news_novelty[T]
z_s = a_s0 + a_s1*gate_soc_intensity[T]  + a_s2*gate_soc_novelty[T]
g_n = sigmoid(z_n)
 g_s = sigmoid(z_s)
# reweight
w_tilde = {
  'p': w_p * (1 - beta_n*g_n) * (1 - beta_s*g_s),
  'n': w_n * (1 + beta_n*g_n),
  's': w_s * (1 + beta_s*g_s),
}
sum_w = sum(w_tilde.values())
w_bar = {k: v/sum_w for k,v in w_tilde.items()}
# fused score
p_fuse = w_bar['p']*p_price + w_bar['n']*p_news + w_bar['s']*p_social
```

---

## Calibration (classification)

* Optionally **calibrate** `p_fuse` via isotonic/Platt on the validation month (per window). Save `calibrator.pkl` under `models/fusion/`.

## Artifacts

* Save to `models/fusion/<run_id>/window_<k>/`: `fusion_params.json`, `calibrator.pkl` (if any), and `metadata.json` (feature list, window dates, metrics).

## Diagnostics

* Log **effective weights** (\bar{w}_k) time series and correlations with gate inputs.
* Report **lift** vs simple equal‑weight average on validation.

## Anti‑leak & constraints

* Gates consume **only** features available at day *T* (no t+1 info).
* Fusion parameters are fit **inside each walk‑forward window** using the **validation** slice only.

## Acceptance checklist

* Fused scores are reproducible for a given window/params and improve validation loss vs average of heads.
* Effective weights remain convex (non‑negative, sum to 1).
* Gate activations rise on text‑burst/novel days and are bounded in [0,1].

---

## Related Files

* `08-modeling/heads_price_news_social.md` — Head models
* `07-features/news_features.md` — News burst features
* `07-features/social_features.md` — Social burst features
* `09-evaluation/ablations_checklist.md` — Fusion ablations
