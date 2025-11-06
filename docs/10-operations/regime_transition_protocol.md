# ORBIT — Regime Transition Protocol

*Last edited: 2025-11-06*

## Purpose

Define **market regime classifications** and **operational responses** to regime transitions, ensuring the model adapts safely during volatility spikes, crisis periods, or prolonged calm while maintaining anti-leak discipline.

---

## Regime Definitions

Based on **VIX (CBOE Volatility Index)** as primary indicator, supplemented by realized volatility and drawdown metrics.

| Regime       | VIX Range | Characteristics                          | Expected Frequency |
| ------------ | --------- | ---------------------------------------- | ------------------ |
| **Low Vol**  | < 15      | Sustained calm, low intraday swings      | ~20% of days       |
| **Normal**   | 15–25     | Typical market conditions                | ~60% of days       |
| **Elevated** | 25–35     | Heightened uncertainty, event-driven     | ~15% of days       |
| **Crisis**   | > 35      | Extreme fear, circuit breakers, crash    | ~5% of days        |

**Supplementary Metrics (optional refinement):**
* **Realized Vol (20d):** Rolling standard deviation of daily SPY returns (annualized)
* **Max Drawdown (60d):** Peak-to-trough decline from recent high
* **Regime Persistence:** Number of consecutive days in current regime

---

## Detection & Monitoring

### Daily Regime Classification

**Primary Rule:**
```python
vix_close = fetch_vix_close(date=T)  # at 4:05 PM ET
if vix_close < 15:
    regime = "Low Vol"
elif 15 <= vix_close < 25:
    regime = "Normal"
elif 25 <= vix_close < 35:
    regime = "Elevated"
else:
    regime = "Crisis"
```

**Store in features:**
* Add `regime: str` column to `features_daily.parquet`
* Add `vix_close: float` as input feature for heads/fusion

### Transition Detection

A **regime transition** occurs when the regime classification changes from day *T−1* to day *T*.

**Transition Types:**
* **Upward escalation:** Low Vol → Normal → Elevated → Crisis
* **Downward de-escalation:** Crisis → Elevated → Normal → Low Vol
* **Jump transitions:** Normal → Crisis (rare but critical)

---

## Operational Responses by Regime

### 1. Low Vol Regime (VIX < 15)

**Model Behavior:**
* Price head typically dominates (stable trends)
* Text gates remain low (less burst activity)
* Standard walk-forward retraining schedule

**Monitoring Frequency:**
* Drift checks: **Weekly** (relaxed)
* IC metrics: Compute **Monday AM** only

**Position Sizing:**
* Standard sizing from `thresholds_position_sizing.md`
* Full Kelly fraction (if enabled)

**Retrain Triggers:**
* Standard: **Monthly** walk-forward
* No emergency retrains unless IC < threshold

**Risk Controls:**
* Standard stop-loss rules
* No additional hedging required

---

### 2. Normal Regime (VIX 15–25)

**Model Behavior:**
* Balanced modality weights
* Text gates active on burst/novel days
* Standard fusion parameters

**Monitoring Frequency:**
* Drift checks: **Every 3 days**
* IC metrics: Compute **Monday/Thursday AM**

**Position Sizing:**
* Standard sizing
* Full Kelly fraction

**Retrain Triggers:**
* Standard: **Monthly** walk-forward
* Emergency: If IC drops below −0.05 for 10 days

**Risk Controls:**
* Standard stop-loss and transaction cost modeling
* No additional constraints

---

### 3. Elevated Regime (VIX 25–35)

**Model Behavior:**
* Text modalities likely amplified (news/social burst during uncertainty)
* Fusion gates more reactive
* Increased feature variance

**Monitoring Frequency:**
* Drift checks: **Daily** (before 15:30 ET cutoff)
* IC metrics: Compute **every morning** (9:35 AM)
* Feature distribution monitoring: Check for outliers

**Position Sizing:**
* **Reduce Kelly fraction to 50%** of normal
* Cap maximum position size at 50% of normal

**Retrain Triggers:**
* **Bi-weekly** walk-forward (more frequent updates)
* Emergency: If IC < −0.10 for 5 days OR max drawdown > 15%

**Risk Controls:**
* Tighten stop-loss: **−3%** intraday (vs −5% normal)
* Increase slippage assumptions by **50%** (wider spreads)
* Consider holding cash on days with quality < 0.7 for both text modalities

**Alert Thresholds:**
* **Warning:** If VIX closes > 30 for 3 consecutive days → prepare for Crisis protocols
* **Action:** If VIX intraday spike > 40 → pause new positions until close

---

### 4. Crisis Regime (VIX > 35)

**Model Behavior:**
* Extreme text burst activity (potential noise)
* Price head may be unreliable (gaps, halts)
* High risk of model breakdown

**Monitoring Frequency:**
* Drift checks: **Continuous** (real-time if possible)
* IC metrics: Compute **hourly** (9:35, 11:00, 13:00, 15:00)
* Manual review: **Required before any trade**

**Position Sizing:**
* **Reduce Kelly fraction to 25%** of normal
* Cap maximum position size at 25% of normal
* Consider **full cash** if VIX > 50

**Retrain Triggers:**
* **Weekly** walk-forward (prioritize recent data)
* Emergency: **Immediate** retrain if IC < −0.15 for 3 days
* **Pause predictions** if IC < −0.25 until manual review

**Risk Controls:**
* **Strict stop-loss:** −2% intraday
* **No overnight holds** during circuit breaker days
* Increase slippage assumptions by **200%** (illiquidity premium)
* Require **manual approval** for any position > $10K

**Alert Thresholds:**
* **Critical:** If VIX > 50 → **halt all automated trading**, manual override only
* **Escalation:** If max drawdown > 25% → trigger full system audit

**Data Quality Considerations:**
* Text data likely incomplete due to API overload (Reddit/Alpaca throttling)
* Expect `news_data_quality < 0.7` and `soc_data_quality < 0.5`
* Price data may have gaps or corrections (use `curated/` only, verify timestamps)

---

## Transition Protocols

### Escalation (Moving to Higher Volatility)

**Normal → Elevated:**
1. Log transition timestamp and VIX value
2. Switch to daily monitoring schedule
3. Reduce position sizing starting next day *T+1*
4. Alert: Email/Slack notification to operators

**Elevated → Crisis:**
1. **Immediate halt** on new positions (complete current day only)
2. Review open positions, apply crisis stop-loss
3. Enable hourly IC monitoring
4. Manual review required before resuming
5. Alert: **Critical notification** with SMS/page

**Jump Transition (Normal → Crisis):**
1. Treat as Elevated → Crisis
2. **Emergency retrain** using last 30 days only (prioritize recent regime)
3. Hold all positions flat until retrain completes
4. Operator must approve model reload

### De-escalation (Moving to Lower Volatility)

**Crisis → Elevated:**
1. Log transition, maintain elevated protocols for **5 days** (persistence check)
2. Gradually relax position sizing over 5 days (25% → 50%)
3. Continue daily monitoring until VIX < 30 for 3 days

**Elevated → Normal:**
1. Log transition, maintain elevated monitoring for **3 days**
2. Gradually return to standard Kelly fraction over 3 days
3. Resume standard retrain schedule after confirmation

**Normal → Low Vol:**
1. Standard transition, no special protocols
2. Switch to weekly monitoring schedule
3. Log for regime analysis in `regime_persistence` metrics

---

## Regime Persistence Tracking

Store in `features_daily.parquet`:
* `regime_current: str` — Current day regime
* `regime_prev: str` — Previous day regime
* `regime_days_count: int` — Consecutive days in current regime
* `regime_transition: bool` — 1 if regime changed today

Use for analysis:
* Model performance stratified by regime
* IC correlation with regime duration
* Feature importance shifts across regimes

---

## Integration with Existing Systems

**Drift Monitoring (`drift_monitoring.md`):**
* Regime included as stratification variable
* Separate drift thresholds per regime (tighter in Crisis)

**Backtest (`backtest_rules.md`):**
* Report metrics **per regime** (4-way split)
* Regime transition days excluded from Sharpe calculation (optional)

**Training (`training_walkforward.md`):**
* Optionally **oversample** Crisis days during training (if using classification)
* Consider regime-specific hyperparameters (separate tuning per regime)

**Risk Controls (`risk_controls.md`):**
* Regime determines stop-loss, position size caps, slippage assumptions
* Override rules if regime-specific thresholds violated

---

## Acceptance Checklist

* [ ] VIX data available daily by 4:05 PM ET for same-day regime classification
* [ ] Regime stored in `features_daily.parquet` with transition flags
* [ ] Monitoring frequency adapts automatically based on regime
* [ ] Position sizing respects regime-specific Kelly fractions
* [ ] Emergency retrain triggers defined per regime
* [ ] Operators receive alerts on regime transitions (Elevated/Crisis)
* [ ] Manual override process documented for Crisis halt scenarios

---

## Related Files

* `07-features/price_features.md` — VIX feature inclusion
* `08-modeling/training_walkforward.md` — Regime-aware retraining
* `09-scoring-backtest/thresholds_position_sizing.md` — Kelly fraction adjustments
* `09-scoring-backtest/risk_controls.md` — Regime-specific stop-loss
* `10-operations/drift_monitoring.md` — Regime stratification
* `10-operations/monitoring_dashboards.md` — Regime display on dashboard
