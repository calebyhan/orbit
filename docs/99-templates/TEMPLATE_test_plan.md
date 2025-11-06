
*Last edited: YYYY-MM-DDTHH:MM:SS-05:00*

## Overview

**Component:** [What is being tested]  
**Scope:** [Unit / Integration / End-to-end]  
**Priority:** [High / Medium / Low]

---

## 1. Unit Tests

### Test 1.1: [Test Name]

**Objective:** [What specific behavior is tested]

**Setup:**
```python
# Test fixtures or data setup
input_data = {...}
expected_output = {...}
```

**Execution:**
```python
result = function_under_test(input_data)
assert result == expected_output
```

**Assertions:**
- [ ] Output type matches expected
- [ ] Output values within tolerance
- [ ] No exceptions raised
- [ ] [Domain-specific assertion]

**Edge Cases:**
- Empty input
- NaN values
- Extreme values (min/max)
- [Custom edge case]

---

### Test 1.2: [Next Test]

[Repeat structure...]

---

## 2. Integration Tests

### Test 2.1: [Integration Test Name]

**Objective:** [How components interact]

**Components Involved:**
- [Module A]
- [Module B]
- [External service/API]

**Test Flow:**
1. [Step 1: Setup preconditions]
2. [Step 2: Execute workflow]
3. [Step 3: Verify outputs]

**Assertions:**
- [ ] Data flows correctly between modules
- [ ] File outputs created in expected location
- [ ] Schema validation passes
- [ ] No data leakage (timestamps respected)
- [ ] [Domain-specific check]

**Failure Modes Tested:**
- [ ] Missing input files
- [ ] API timeout/failure
- [ ] Schema violation
- [ ] [Custom failure mode]

---

## 3. Backtest Validation Tests

### Test 3.1: No Lookahead Bias

**Objective:** Ensure all features respect 15:30 ET cutoff

**Method:**
```python
# For each trading day t:
# - Verify max(timestamp) of news/social ≤ t @ 15:30 ET
# - Verify price features only use data through t-1 close
```

**Assertions:**
- [ ] No future data in features
- [ ] Labels computed with correct lag
- [ ] All timestamps ≤ cutoff

---

### Test 3.2: Walk-Forward Integrity

**Objective:** Ensure train/val/test splits are correct

**Method:**
```python
# Verify:
# - No overlap between train and test
# - Test period follows validation period
# - Model only trained on past data
```

**Assertions:**
- [ ] Splits are contiguous and non-overlapping
- [ ] Test dates always > validation dates > train dates
- [ ] No data from test set used in model training

---

### Test 3.3: Transaction Cost Realism

**Objective:** Verify costs are applied correctly

**Method:**
```python
# Execute backtest with known trades
# Verify: realized_return = raw_return - costs
```

**Assertions:**
- [ ] Cost = position_size × (cost_bps + slippage_bps)
- [ ] Costs deducted on both entry and exit
- [ ] Costs scale with position size

---

## 4. Performance Tests

### Test 4.1: Runtime

**Objective:** Module completes within expected time

**Target:** [X minutes for Y days of data]

**Method:**
```bash
time python -m orbit.module --start-date 2024-01-01 --end-date 2024-12-31
```

**Assertions:**
- [ ] Runtime < [threshold] minutes
- [ ] Memory usage < [threshold] GB
- [ ] No memory leaks

---

### Test 4.2: Scalability

**Objective:** Module handles increasing data volume

**Method:**
- Test with 1 year, 3 years, 5 years of data
- Monitor runtime and memory

**Assertions:**
- [ ] Runtime scales linearly (or better)
- [ ] Memory stays within limits

---

## 5. Data Quality Tests

### Test 5.1: Schema Conformance

**Objective:** Outputs match schema

**Method:**
```python
python -m orbit.ops.validate_schema --source [name] --date [test_date]
```

**Assertions:**
- [ ] All required columns present
- [ ] Column types correct
- [ ] No unexpected columns

---

### Test 5.2: NaN Rate

**Objective:** Missing data within acceptable limits

**Target:** NaN rate ≤ [X]% per column

**Assertions:**
- [ ] NaN rate per column < threshold
- [ ] Total completeness > [Y]%

---

### Test 5.3: Value Ranges

**Objective:** Data values are sensible

**Method:**
```python
# For each column, verify:
# - Min/max within expected range
# - No impossible values (e.g., negative volume)
```

**Assertions:**
- [ ] Prices > 0
- [ ] Sentiment in [-1, 1]
- [ ] Counts ≥ 0
- [ ] Z-scores typically in [-5, 5]

---

## 6. Acceptance Tests

### Test 6.1: [High-Level Requirement]

**Objective:** [User/business requirement met]

**Acceptance Criteria:**
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

**Validation Method:** [How to verify]

---

## 7. Regression Tests

**Objective:** Ensure changes don't break existing functionality

**Method:**
- Run full test suite on known-good data
- Compare outputs to baseline

**Baseline:**
- `tests/fixtures/baseline_[date].parquet`

**Assertions:**
- [ ] Outputs match baseline (within numerical tolerance)
- [ ] Performance metrics unchanged
- [ ] No new errors/warnings

---

## Test Execution

### Run All Tests

```bash
pytest tests/ -v --cov=orbit --cov-report=html
```

### Run Specific Test Suite

```bash
pytest tests/test_[module].py -v
```

### Generate Coverage Report

```bash
pytest --cov=orbit --cov-report=term-missing
```

---

## Acceptance Checklist

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No lookahead bias detected
- [ ] Walk-forward splits correct
- [ ] Transaction costs applied correctly
- [ ] Runtime within budget
- [ ] Schema validation passes
- [ ] NaN rate ≤ [X]%
- [ ] Acceptance criteria met
- [ ] Regression tests pass
- [ ] Code coverage ≥ [Y]%

---

## Related Files

* `[path/to/module_spec.md]` — Module documentation
* `[path/to/test_code.py]` — Test implementation

---

