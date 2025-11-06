
*Last edited: YYYY-MM-DDTHH:MM:SS-05:00*

**Frequency:** [Daily / Weekly / Monthly]  
**Estimated Duration:** [X minutes]  
**Operator:** [Human / Automated / Hybrid]

---

## Pre-Run Checks

- [ ] **Config valid:** `python -m orbit.ops.validate_config`
- [ ] **[Dependency 1] ready:** [Check command or condition]
- [ ] **[Dependency 2] ready:** [Check command or condition]
- [ ] **Disk space available:** [Minimum GB free]
- [ ] **[Custom check]:** [Description]

---

## Run Steps

### Step 1: [Action Name]

**Command:**
```bash
[Exact command to run]
```

**Expected output:**
```
[What success looks like]
```

**Duration:** ~[X] minutes

### Step 2: [Next Action]

[Repeat structure...]

---

## Post-Run Checks

- [ ] **Output files exist:**
  - `[path/to/output1.parquet]`
  - `[path/to/output2.parquet]`
- [ ] **Schema validation:** `python -m orbit.ops.validate_schema --source [name]`
- [ ] **NaN rate ≤ [X]%:** [Check command]
- [ ] **Row count matches expected:** [Check command]
- [ ] **Logs show no errors:** `tail -100 logs/[job_name].json`
- [ ] **[Custom validation]:** [Description]

---

## Success Criteria

✅ **Job succeeds if:**

- All pre-run checks pass
- All steps complete without errors
- All post-run checks pass
- Outputs meet acceptance criteria

---

## Failure Modes

| Symptom | Likely Cause | Recovery Action |
|---------|--------------|-----------------|
| [Error message / behavior] | [Root cause] | [Fix + rerun command] |
| [Error message / behavior] | [Root cause] | [Fix + rerun command] |

**Escalation:** If recovery fails after 2 attempts, see `docs/10-operations/failure_modes_playbook.md`

---

## Monitoring

**Key Metrics to Track:**

- [Metric 1]: [Expected range]
- [Metric 2]: [Expected range]
- [Metric 3]: [Expected range]

**Alert Thresholds:**

- 🔴 **Critical:** [Condition → page operator]
- 🟡 **Warning:** [Condition → log + review]

---

## Related Files

* `[path/to/module_spec.md]` — [Module documentation]
* `[path/to/runbook.md]` — [Operations runbook]
* `[path/to/failure_modes_playbook.md]` — [Detailed recovery procedures]

---

