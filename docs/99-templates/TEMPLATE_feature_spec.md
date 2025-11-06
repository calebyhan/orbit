
*Last edited: YYYY-MM-DDTHH:MM:SS-05:00*

## Definition

**Name:** `[feature_name]`  
**Type:** [Price / News / Social / Cross-modal]  
**Modality:** [Which model head uses this]

---

## Formula

```
[Mathematical formula or pseudocode]
```

**Example:**
```python
momentum_5d = (close_t / close_{t-5}) - 1
```

---

## Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `window` | [N days] | [Why this lookback period] |
| `lag` | [N days] | [Why this lag to prevent leakage] |
| `cap` | [min, max] | [Outlier handling] |

---

## Data Sources

- **Primary:** `[data/source/path.parquet]`
- **Secondary:** `[optional auxiliary data]`

---

## NA Rules

**When is this feature NaN?**

- [Condition 1]
- [Condition 2]

**Acceptable NaN rate:** ≤ [X]%

---

## Normalization

- [ ] **Standardized (z-score):** [If yes, over what window?]
- [ ] **Rank-transformed**
- [ ] **Raw values**
- [ ] **Other:** [Describe]

---

## Signal Hypothesis

**Why should this feature predict returns?**

[2-3 sentences explaining the economic/behavioral rationale]

---

## Validation

### Correlation with Label

**Expected IC:** [Range, e.g., 0.02-0.08]

### Stability

- **IC rolling 60d:** [Acceptable range]
- **Turnover:** [How often does it change rank]

### Ablation Impact

**Performance drop if removed:** [Estimated Sharpe/IC impact]

---

## Acceptance Checklist

- [ ] NaN rate ≤ [X]%
- [ ] Values within expected range [min, max]
- [ ] IC > [threshold] on validation set
- [ ] No lookahead bias (respect 15:30 ET cutoff)
- [ ] Stable IC over walk-forward splits

---

## Related Files

* `[path/to/feature_module.md]` — [Feature computation module]
* `[path/to/schema.md]` — [Schema definition]

---

