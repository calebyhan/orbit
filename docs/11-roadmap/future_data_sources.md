# ORBIT — Future Data Sources

*Last edited: 2025-11-05*

## Purpose

Catalog **potential data sources** to add after v1 (tri-modal index model) is stable. Each source includes rationale, complexity, cost, and priority.

---

## Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Signal strength** | 40% | Expected IC lift or Sharpe improvement |
| **Cost** | 25% | Free vs paid; API limits |
| **Implementation complexity** | 20% | Weeks of engineering effort |
| **Maintenance burden** | 15% | Ongoing operational overhead |

**Priority scale:** 🟢 High / 🟡 Medium / 🔴 Low

---

## 1. SEC Filings (10-K, 10-Q, 8-K)

### Rationale

* **10-K/10-Q:** Annual/quarterly reports contain forward guidance, risk factors, MD&A
* **8-K:** Material events (earnings, acquisitions, exec changes) filed within 4 days
* Text contains **specific, actionable info** not yet in headlines

### Signal Hypothesis

* Tone shift in MD&A predicts next-quarter returns
* Risk factor expansion signals downturn
* 8-K filings cause immediate price moves (capture with NLP)

### Data Source

* **SEC EDGAR API:** Free, rate-limited (10 requests/sec)
* **Alternatives:** Alpha Vantage (paid), Quandl (paid)

### Implementation

* **Ingestion:** Parse XML/XBRL → extract text sections
* **Features:** Sentiment change (Q-over-Q), readability metrics, keyword flags
* **Frequency:** Quarterly (10-K/Q) + event-driven (8-K)

### Complexity

* **Engineering:** 3 weeks (parser, dedup, storage)
* **Maintenance:** Low (stable API, infrequent updates)

### Cost

* Free (EDGAR API)

### Priority

🟢 **High** — High signal, zero cost, moderate complexity

### Next Steps

* Prototype 10-K sentiment extractor
* Test on S&P 100 (simpler than full 500)
* Measure IC lift on quarterly returns

---

## 2. Macroeconomic Indicators

### Rationale

* Fed rate decisions, CPI, unemployment drive broad market moves
* Index (SPY) more sensitive to macro than individual stocks

### Signal Hypothesis

* Surprise CPI → next-day SPY vol spike
* Fed hike → risk-off (lower SPY)
* Macro calendar events → gate text weight higher

### Data Source

* **FRED (Federal Reserve Economic Data):** Free API
* **BLS (Bureau of Labor Statistics):** Free
* **Fed calendar:** Scrape from federalreserve.gov

### Implementation

* **Ingestion:** Daily pull from FRED API
* **Features:** Surprise vs consensus, YoY change, event flags (Fed day)
* **Frequency:** Daily (for event flags); monthly (for econ releases)

### Complexity

* **Engineering:** 1 week (simple API, few endpoints)
* **Maintenance:** Very low

### Cost

* Free

### Priority

🟢 **High** — Easy win, zero cost, pairs well with index model

### Next Steps

* Add Fed calendar scraper to `orbit.ingest.macro`
* Create `is_fed_day`, `is_cpi_day` binary features
* Test gate up-weighting on event days

---

## 3. Options Flow (Unusual Activity)

### Rationale

* Large options trades signal informed bets
* Unusual call volume → bullish; unusual put volume → bearish

### Signal Hypothesis

* Spike in OTM call buying predicts next-week rally
* Dark pool prints correlate with near-term moves

### Data Source

* **Paid APIs:** Tradier, CBOE DataShop ($$$)
* **Free (limited):** Yahoo Finance options chain (delayed, incomplete)

### Implementation

* **Ingestion:** REST API → parse options chain
* **Features:** Put/call ratio, unusual volume flags, open interest change
* **Frequency:** Daily (end-of-day)

### Complexity

* **Engineering:** 2 weeks (API integration, feature calc)
* **Maintenance:** Medium (API changes, data quality issues)

### Cost

* **Free tier:** Limited to top 50 stocks, delayed
* **Paid:** $200-500/month for real-time full universe

### Priority

🟡 **Medium** — High signal potential, but expensive and complex

### Next Steps

* Pilot with free tier (Yahoo Finance) on S&P 50
* Measure IC lift on 1-5 day returns
* If positive, justify paid subscription

---

## 4. Short Interest

### Rationale

* High short interest → squeeze potential or justified pessimism
* Short interest changes predict volatility and reversals

### Signal Hypothesis

* Rising short interest + positive news → short squeeze
* Declining short interest after rally → trend exhaustion

### Data Source

* **FINRA (free, delayed 2 weeks):** Bi-monthly short interest reports
* **Paid:** S3 Partners, IHS Markit ($$$)

### Implementation

* **Ingestion:** Scrape FINRA or API
* **Features:** Short % of float, days-to-cover, change vs prior period
* **Frequency:** Bi-monthly (free) or daily (paid)

### Complexity

* **Engineering:** 1 week (free scraper) or 2 weeks (paid API)
* **Maintenance:** Low

### Cost

* **Free (FINRA):** Delayed, coarse
* **Paid:** $500-1000/month for real-time

### Priority

🟡 **Medium** — Interesting for single stocks, less useful for index

### Next Steps

* Start with free FINRA data (bi-monthly)
* Test on high-short-interest stocks (cross-sectional)
* If useful, upgrade to paid for daily updates

---

## 5. Insider Trading (Form 4 Filings)

### Rationale

* CEO/CFO buys → bullish signal
* Mass insider selling → bearish

### Signal Hypothesis

* Cluster of insider buys in same stock → outperforms next quarter
* Insider selling after run-up → mean reversion

### Data Source

* **SEC Form 4:** Free (EDGAR API)
* **Aggregators:** OpenInsider (free web), Quandl (paid API)

### Implementation

* **Ingestion:** Parse XML Form 4 → extract buys/sells, amounts, roles
* **Features:** Net insider buying (last 30d), CEO buy flag, abnormal volume
* **Frequency:** Daily

### Complexity

* **Engineering:** 2 weeks (XML parsing, dedup, storage)
* **Maintenance:** Low

### Cost

* Free (EDGAR)

### Priority

🟡 **Medium** — Strong signal for single stocks, weaker for index

### Next Steps

* Build Form 4 parser
* Test on S&P 100
* Measure IC lift on monthly returns

---

## 6. Alternative Sentiment (StockTwits, Twitter/X)

### Rationale

* Real-time retail sentiment (faster than Reddit)
* Twitter/X has broader reach than Reddit

### Signal Hypothesis

* Spike in bullish StockTwits messages → next-day rally
* Elon tweets → TSLA moves (already known, but generalizable)

### Data Source

* **StockTwits API:** Free tier (limited), paid ($$$)
* **Twitter/X API:** Paid only (after 2023 changes)

### Implementation

* **Ingestion:** REST or WebSocket → dedupe, sentiment scoring
* **Features:** Bullish/bearish ratio, message volume, influencer sentiment
* **Frequency:** Real-time or hourly

### Complexity

* **Engineering:** 2 weeks (similar to Reddit pipeline)
* **Maintenance:** Medium (API changes frequent)

### Cost

* **StockTwits:** $200/month (paid tier)
* **Twitter/X:** $5,000/month (enterprise API)

### Priority

🔴 **Low** — Expensive, noisy, Reddit already covers retail sentiment

### Next Steps

* Skip for v1
* Re-evaluate if Reddit proves very valuable

---

## 7. Earnings Call Transcripts

### Rationale

* Management tone and Q&A reveal insights beyond earnings numbers
* "Uncertainty" language predicts volatility

### Signal Hypothesis

* Cautious language → next-quarter underperformance
* Confident tone + beat → continuation

### Data Source

* **Paid:** AlphaSense, Sentieo, FactSet ($$$)
* **Free (limited):** Seeking Alpha (web scrape, TOS risk)

### Implementation

* **Ingestion:** API or scrape → NLP sentiment + keyword extraction
* **Features:** Sentiment shift Q-over-Q, uncertainty score, guidance flags
* **Frequency:** Quarterly (earnings season)

### Complexity

* **Engineering:** 3 weeks (NLP pipeline, entity linking)
* **Maintenance:** Medium (scraper maintenance if free)

### Cost

* **Free (scrape):** High legal risk
* **Paid:** $1,000-5,000/month

### Priority

🔴 **Low** — High cost, quarterly frequency (low turnover)

### Next Steps

* Skip for v1
* Re-evaluate for single-stock model if budget allows

---

## 8. Satellite / Alternative Data

### Rationale

* Parking lot counts → retail sales (e.g., Target, Walmart)
* Shipping data → supply chain health

### Signal Hypothesis

* Rising parking lot traffic → earnings beat

### Data Source

* **Paid vendors:** Orbital Insight, RS Metrics, Descartes Labs ($$$$$)

### Implementation

* **Ingestion:** Vendor API → join to stock tickers
* **Features:** Traffic change YoY, inventory levels
* **Frequency:** Weekly or monthly

### Complexity

* **Engineering:** 1 week (API integration)
* **Maintenance:** Low

### Cost

* **$10,000-50,000/year** per dataset

### Priority

🔴 **Low** — Extremely expensive, unproven for daily alpha

### Next Steps

* Skip for v1 and likely v2
* Only consider if institutional capital deployed

---

## Priority Ranking

| Source | Priority | Cost | Complexity | Next Milestone |
|--------|----------|------|------------|----------------|
| **Macro indicators** | 🟢 High | Free | Low | M4 (after deployment) |
| **SEC filings** | 🟢 High | Free | Medium | M7 (single-stock) |
| **Options flow** | 🟡 Medium | $-$$$ | Medium | M8 (if budget) |
| **Short interest** | 🟡 Medium | Free-$$ | Low | M7 (single-stock) |
| **Insider trading** | 🟡 Medium | Free | Medium | M7 (single-stock) |
| **StockTwits/Twitter** | 🔴 Low | $$$$ | Medium | Skip |
| **Earnings calls** | 🔴 Low | $$$$ | High | Skip |
| **Satellite data** | 🔴 Low | $$$$$ | Low | Skip |

---

## Roadmap

**M4-M6 (Post-deployment, index model):**
* Add macro indicators (Fed calendar, CPI surprises)
* Test macro gates (up-weight text on Fed days)

**M7 (Single-stock extension):**
* Add SEC filings (10-K/Q sentiment)
* Add insider trading (Form 4)
* Pilot free-tier options flow

**M8+ (If positive results + budget):**
* Upgrade to paid options flow
* Add short interest (paid, daily)

**Never (unless institutional capital):**
* Earnings call transcripts (too expensive for signal/noise)
* Satellite data (research-stage only)

---

## Related Files

* `milestones.md` — Overall roadmap
* `extend_to_single_stocks.md` — Single-stock plan

---

