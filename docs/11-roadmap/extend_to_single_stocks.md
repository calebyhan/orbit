# ORBIT — Extend to Single Stocks

*Last edited: 2025-11-05*

## Purpose

Document the plan for extending ORBIT from **index-only** (SPY/VOO) to a **cross-sectional single-stock portfolio**. This is the natural next step after v1 proves successful on SPY.

---

## Why Wait Until After Index v1?

* **Simpler mapping:** Index = 1 symbol; stocks = 500+ symbols with ambiguous mentions
* **Faster iteration:** Index model trains faster (less data, simpler features)
* **Lower risk:** Prove the concept before scaling complexity
* **Data costs:** Free sources (Stooq, Alpaca, Reddit) work well for index; stocks may need paid data

---

## Key Differences: Index vs Single-Stock

| Aspect | Index (SPY/VOO) | Single-Stock |
|--------|-----------------|--------------|
| **Universe size** | 1-2 symbols | 50-500 symbols |
| **Labels** | Absolute or excess return | Relative return (vs S&P 500) |
| **Features** | Mostly macro/sentiment | Stock-specific + sector + macro |
| **Model** | Single score | Cross-sectional ranking |
| **Strategy** | Long/flat binary | Long/short portfolio (top/bottom deciles) |
| **Mapping complexity** | Trivial (SPY keywords) | High (ticker ambiguity, name variations) |
| **Data volume** | ~1-2k news items/day | ~10-50k news items/day |
| **Training time** | Minutes | Hours |

---

## Prerequisites (Must Complete First)

* [ ] **M3 complete:** Tri-modal index model passes all acceptance gates
* [ ] **1+ year OOS:** ≥252 days of held-out test showing stable IC ≥ 0.02
* [ ] **Reproducibility:** Independent validation replicates results
* [ ] **Operational maturity:** 90+ days of daily scoring with <2% failure rate

---

## Phase 1: Universe Selection (1 week)

**Goal:** Choose which stocks to model.

### Option A: S&P 500 Constituents

**Pros:** Liquid, well-covered by news, sector diversity  
**Cons:** 500 symbols; mapping complexity high

**Recommendation:** Start with **S&P 100** (OEX) or **S&P 50** (top 50 by market cap)

### Option B: Sector ETFs

**Pros:** Fewer symbols (11 sectors), less mapping noise  
**Cons:** Not single-stock; still broad

**Recommendation:** Use for pilot; then extend to single names

### Acceptance Criteria

* [ ] Universe list documented in `config/universe.yaml`
* [ ] Historical price data available for all symbols (Stooq or alternative)
* [ ] News/social mapping rules defined (see below)

---

## Phase 2: Identifier Mapping (2 weeks)

**Goal:** Map news headlines and social posts to specific stocks.

### Challenges

* **Ticker ambiguity:** "SNAP" = Snap Inc. or snapshot?
* **Company name variations:** "Apple" vs "AAPL" vs "Apple Inc."
* **Sector/industry keywords:** "tech stocks" → which ones?
* **False positives:** "Ford government" ≠ Ford Motor Co.

### Solution: Multi-Stage Mapper

1. **Exact ticker match:** `$AAPL`, `AAPL`, `NASDAQ:AAPL`
2. **Company name match:** "Apple Inc." → AAPL (with blacklist)
3. **Alias dictionary:** "JPM" → JPMorgan Chase, "FB" → Meta
4. **Disambiguation:** If ambiguous, skip or down-weight

**Tool:** Pre-built ticker→company mapping (see `04-data-sources/identifiers_mapping.md`)

### Acceptance Criteria

* [ ] Mapping achieves ≥85% precision, ≥70% recall on hand-labeled test set (100 headlines/posts)
* [ ] False positive rate <5%
* [ ] Ambiguous items flagged for manual review or skipped

---

## Phase 3: Cross-Sectional Labels (1 week)

**Goal:** Define prediction target for each stock.

### Label Options

#### Option 1: Relative Return (Recommended)

$$
y_i = r_{i, t+1} - r_{\text{SPX}, t+1}
$$

**Pros:** Market-neutral; captures stock-specific alpha  
**Cons:** Harder to predict (smaller signal)

#### Option 2: Sector-Relative Return

$$
y_i = r_{i, t+1} - r_{\text{sector}_i, t+1}
$$

**Pros:** Controls for sector trends  
**Cons:** Requires sector classification

#### Option 3: Quantile Labels (Classification)

Rank stocks by next-day return; predict quintile (Q1-Q5)

**Pros:** Robust to outliers  
**Cons:** Loses magnitude information

**Recommendation:** Start with **Option 1 (relative return)** for regression; Option 3 for classification.

---

## Phase 4: Feature Engineering (2 weeks)

**Goal:** Extend index features to per-stock + cross-sectional features.

### Per-Stock Features (Same as Index)

* **Price:** momentum, reversal, vol, drawdown
* **News:** stock-specific news_count_z, sentiment, novelty
* **Social:** stock-specific post_count_z, sentiment, credibility-weighted

### Cross-Sectional Features (New)

* **Relative momentum:** Stock momentum vs sector median
* **Relative sentiment:** Stock sentiment vs market average
* **Attention divergence:** (Stock news count) / (Sector avg news count)
* **Sector dummies:** One-hot or embeddings for 11 sectors

### Interaction Features

* **Macro × stock:** VIX × stock_beta, Fed_day × stock_sensitivity

### Acceptance Criteria

* [ ] Feature table has shape `(n_stocks × n_days, n_features)`
* [ ] Cross-sectional features computed correctly (verified on 3 sample days)
* [ ] NaN rate ≤10% per feature

---

## Phase 5: Model Architecture (2 weeks)

**Goal:** Adapt tri-modal heads + fusion for cross-sectional prediction.

### Option A: Shared Heads (Simpler)

Train 3 heads (price, news, social) **shared across all stocks**:
- Input: per-stock features
- Output: per-stock score
- Fusion: per-stock gated blend

**Pros:** Fewer parameters, faster training  
**Cons:** Ignores stock-specific patterns

### Option B: Stock-Specific Heads (Complex)

Train separate heads per stock (or per sector):
- 500 stocks × 3 heads = 1500 models

**Pros:** Captures stock-specific dynamics  
**Cons:** Overfitting risk, slow training

### Recommendation: Hybrid

* **Shared backbone:** Learn common patterns across all stocks
* **Stock embeddings:** Add learnable stock ID embeddings to inputs
* **Sector-specific gates:** Gate weights vary by sector

---

## Phase 6: Portfolio Construction (1 week)

**Goal:** Convert per-stock scores to a long/short portfolio.

### Strategy: Quantile Long/Short

1. **Rank** all stocks by `fused_score_i` each day
2. **Long** top decile (10% highest scores)
3. **Short** bottom decile (10% lowest scores)
4. **Weight:** Equal-weight within each leg

**Position:**
$$
w_i = \begin{cases} 
+\frac{1}{n_{\text{long}}} & \text{if } \text{rank}_i \leq 10\% \\
-\frac{1}{n_{\text{short}}} & \text{if } \text{rank}_i \geq 90\% \\
0 & \text{otherwise}
\end{cases}
$$

### Alternative: Score-Weighted

Weight by score magnitude (higher confidence = larger position).

### Acceptance Criteria

* [ ] Portfolio is market-neutral (sum of weights ≈ 0)
* [ ] Sector-neutral (optional: constrain sector exposure)
* [ ] Turnover <50% daily (to control costs)

---

## Phase 7: Backtest & Evaluation (2 weeks)

**Goal:** Validate cross-sectional model with realistic costs.

### Metrics

* **Long-short IC:** Spearman corr(scores, next-day returns)
* **Sharpe ratio:** Annualized, after costs
* **Alpha vs SPY:** Jensen's alpha (regression on SPY return)
* **Turnover:** % of portfolio replaced daily
* **Hit rate:** % of longs that outperform shorts

### Costs

* **Stock trading:** 5-10 bps per side (higher than index)
* **Short borrow:** Estimate 1-3% annualized for short leg
* **Market impact:** Larger for small-cap; model explicitly

### Acceptance Gates (Stricter Than Index)

* **IC:** ≥0.03 (cross-sectional harder; need higher bar)
* **Sharpe:** ≥0.50 (after costs + short borrow)
* **Alpha:** ≥3% annualized (vs SPY)
* **Stability:** IC > 0 in ≥70% of months

---

## Risks & Mitigations

### Risk 1: Ticker Mapping Errors

**Impact:** News about "SNAP" (Supplemental Nutrition Assistance Program) attributed to Snap Inc.

**Mitigation:**
- Blacklist common false positives
- Require at least 2 mentions per article
- Manual spot-checks on high-importance days

### Risk 2: Survivorship Bias

**Impact:** Universe changes over time (delistings, IPOs); backtest unrealistic

**Mitigation:**
- Use point-in-time universe (historical S&P 500 constituents)
- Exclude stocks with <1 year of history

### Risk 3: Overfitting (500 Stocks)

**Impact:** Model memorizes stock-specific noise

**Mitigation:**
- Strong regularization (L2, dropout)
- Cross-stock validation (train on 80%, test on 20%)
- Sector-based splits (train on 8 sectors, test on 3)

### Risk 4: Data Volume (50k News Items/Day)

**Impact:** Ingestion slows down; hits API limits

**Mitigation:**
- Pre-filter news by source quality (only major wires)
- Sample social posts (not all Reddit mentions)
- Batch processing overnight

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Universe selection | 1 week | M3 complete |
| 2. Identifier mapping | 2 weeks | Phase 1 |
| 3. Labels | 1 week | Phase 1 |
| 4. Features | 2 weeks | Phase 2, 3 |
| 5. Model | 2 weeks | Phase 4 |
| 6. Portfolio | 1 week | Phase 5 |
| 7. Backtest | 2 weeks | Phase 6 |
| **Total** | **11 weeks** | — |

**Start:** After M3 complete + 1 month of stable index model operations  
**Target:** Q2 2025

---

## Related Files

* `milestones.md` — Overall roadmap
* `future_data_sources.md` — Data sources for single-stock (filings, etc.)
* `04-data-sources/identifiers_mapping.md` — Mapping rules

---

