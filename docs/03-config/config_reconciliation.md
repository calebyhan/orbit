# ORBIT — Configuration File Reconciliation

*Last edited: 2025-11-16*

> **⚠️ IMPORTANT: Current Status (M1)**
>
> As of M1, ORBIT uses **`.env` files only** for configuration (via python-dotenv).
> The `orbit.yaml` configuration system documented below is **planned for M2+** but not yet implemented.
>
> **Current configuration method:**
> - Copy `.env.example` to `.env`
> - Set API keys and `ORBIT_DATA_DIR` in `.env`
> - Run CLI commands (no YAML configuration needed)
>
> See [docs/03-config/env_keys.md](env_keys.md) for current setup instructions.

---

## Purpose

This document clarifies the **relationship**, **differences**, and **usage** of ORBIT's three configuration files (planned for future implementation):

1. **`config_schema.yaml`** — Reference schema with all options and comments
2. **`sample_config.yaml`** — Working minimal example (orbit.yaml)
3. **`TEMPLATE_config.yaml`** — Comprehensive starter template with structure

---

## File Roles

### `config_schema.yaml` — **Reference Documentation**

**Purpose:** Human-readable schema showing all available configuration options

**Key Characteristics:**
- **Comprehensive:** Documents every configuration key
- **Annotated:** Includes comments explaining each field
- **Optional markers:** Shows which fields are required vs. optional
- **Not executable:** Contains placeholder URLs and inline comments (not valid YAML)

**Usage:**
- Consult when adding new configuration options
- Reference for understanding what each field does
- Schema design document for code implementation

**Target Audience:** Developers, documentation writers, system architects

---

### `sample_config.yaml` — **Minimal Working Example**

**Purpose:** Ready-to-use configuration for SPY/VOO system

**Key Characteristics:**
- **Executable:** Valid YAML that can be loaded directly
- **Minimal:** Only includes necessary fields for basic operation
- **Tested:** Values known to work in practice
- **Production-ready:** Suitable for actual backtesting

**Usage:**
- Copy to `orbit.yaml` in your project root
- Modify symbols, paths, API keys as needed
- Run system immediately without extensive setup

**Target Audience:** End users, quick-start scenarios, CI/CD

---

### `TEMPLATE_config.yaml` — **Comprehensive Starter**

**Purpose:** Detailed template with all sections and validation instructions

**Key Characteristics:**
- **Structured:** Organized into logical sections with markdown headers
- **Complete:** Includes all major configuration categories
- **Instructive:** Shows environment variable placeholders (`${ALPACA_API_KEY}`)
- **Extensible:** Demonstrates advanced features (drift monitoring, alerts)
- **Documentation-focused:** Includes usage examples

**Usage:**
- Starting point for new ORBIT projects
- Shows best practices for configuration organization
- Reference for environment variable setup
- Guide for production deployment configuration

**Target Audience:** New users, production deployments, advanced configurations

---

## Key Differences

### Structure & Format

| Aspect | config_schema.yaml | sample_config.yaml | TEMPLATE_config.yaml |
|--------|-------------------|-------------------|---------------------|
| **Format** | YAML with inline comments | Pure YAML | Markdown + YAML |
| **Headers** | None | None | Markdown sections |
| **Comments** | Extensive inline | Minimal | Markdown prose |
| **Valid YAML** | No (has comments) | Yes | Partially (mixed format) |

### Content Scope

| Section | config_schema | sample_config | TEMPLATE_config |
|---------|--------------|--------------|----------------|
| **Project metadata** | ✓ | ✓ | ✓ |
| **Paths** | ✓ | ✓ | ✓ |
| **Universe** | ✓ | ✓ | Renamed to `symbols` |
| **Schedule** | ✓ | ✓ | Simplified to `timezone` + `text_cutoff_time` |
| **Sources** | ✓ | ✓ | ✓ (env var syntax) |
| **Preprocessing** | ✓ | ✓ | ✗ (omitted) |
| **Features** | ✓ | ✓ | ✓ (expanded windows) |
| **Labels** | ✓ | ✓ | Renamed to `targets` |
| **Training** | ✓ | ✓ | ✓ (renamed to `model.training`) |
| **Fusion** | ✓ | ✓ | ✓ (under `model.fusion`) |
| **Backtest** | ✓ | ✓ | ✓ |
| **Evaluation** | ✓ | ✓ | ✓ (with acceptance criteria) |
| **Logging** | ✓ | ✓ | ✓ (expanded format/rotation) |
| **Monitoring** | ✗ | ✗ | ✓ (drift, alerts) |
| **Compliance** | ✓ | ✓ | ✗ |

---

## Specific Differences

### 1. Reddit Max Items

**config_schema.yaml:**
```yaml
reddit:
  max_items_per_run: 2000
```

**sample_config.yaml:**
```yaml
reddit:
  max_items_per_run: 1500
```

**Recommendation:** Use **1500** (sample value) for safety. 2000 may hit rate limits.

---

### 2. Timezone Key Structure

**config_schema.yaml & sample_config.yaml:**
```yaml
schedule:
  timezone: "America/New_York"
  cutoff_local: "15:30"
  publish_lag_minutes: 30
```

**TEMPLATE_config.yaml:**
```yaml
timezone: "America/New_York"
text_cutoff_time: "15:30:00"
```

**Issue:** TEMPLATE uses flat structure instead of nested `schedule` section.

**Recommendation:** **Standardize to nested structure** from schema/sample for consistency.

---

### 3. Symbols vs. Universe

**config_schema.yaml & sample_config.yaml:**
```yaml
universe:
  symbols: ["SPY.US", "VOO.US"]
  benchmark: "^SPX"
```

**TEMPLATE_config.yaml:**
```yaml
symbols:
  etf:
    - SPY
    - VOO
  index:
    - ^SPX
  vix:
    - ^VIX
```

**Issue:** TEMPLATE uses categorized structure, schema uses flat list.

**Recommendation:** Keep **flat list** from schema for simplicity. TEMPLATE's categorization is informative but unnecessary complexity.

---

### 4. Model Architecture

**config_schema.yaml & sample_config.yaml:**
```yaml
training:
  heads:
    price: { model: "gbm", params: { n_estimators: 200, max_depth: 3 } }
    news:  { model: "gbm", params: { n_estimators: 200, max_depth: 3 } }
    social:{ model: "gbm", params: { n_estimators: 200, max_depth: 3 } }
```

**TEMPLATE_config.yaml:**
```yaml
model:
  heads:
    price:
      type: "mlp"
      hidden_layers: [64, 32, 16]
      dropout: 0.2
```

**Issue:** TEMPLATE assumes neural network ("mlp"), schema uses GBMs.

**Recommendation:** 
- **Schema/sample are correct** for initial v1 (GBM heads)
- TEMPLATE shows *future* neural network architecture
- Document this discrepancy: TEMPLATE is aspirational, not current

---

### 5. Monitoring Section

**config_schema.yaml & sample_config.yaml:**
No monitoring section.

**TEMPLATE_config.yaml:**
```yaml
monitoring:
  drift:
    ic_window: 20
    ic_threshold: 0.01
    psi_threshold: 0.1
    calibration_bins: 10
  alerts:
    email: false
    slack: false
```

**Recommendation:** **Add monitoring section to schema** for completeness. This is a valuable production feature.

---

### 6. Environment Variables

**TEMPLATE_config.yaml** shows best practice:
```yaml
alpaca:
  api_key: "${ALPACA_API_KEY}"
  api_secret: "${ALPACA_API_SECRET}"
```

**config_schema.yaml & sample_config.yaml:**
Do not show env var syntax.

**Recommendation:** **Update schema to document env var syntax** as recommended approach for secrets.

---

## Alignment Plan

### Immediate Actions

1. **Update config_schema.yaml:**
   - Add `monitoring` section with drift and alert fields
   - Document environment variable syntax (`${VAR_NAME}`)
   - Standardize `reddit.max_items_per_run` to **1500**
   - Add note: "Neural network heads (mlp) planned for v2; current v1 uses GBM"

2. **Update sample_config.yaml:**
   - Already correct, no changes needed
   - Consider adding `.env` file example in comments

3. **Update TEMPLATE_config.yaml:**
   - Change flat `timezone` → nested `schedule.timezone`
   - Change flat `text_cutoff_time` → `schedule.cutoff_local`
   - Simplify `symbols` structure to match schema (remove categorization)
   - Add note: "This template shows v2 neural architecture; see sample_config.yaml for current v1 GBM"
   - Fix markdown structure: extract YAML into pure `.yaml` section

---

## Usage Guidelines

### For New Users

**Step 1:** Start with **`sample_config.yaml`**
```bash
cp docs/03-config/sample_config.yaml orbit.yaml
nano orbit.yaml  # Edit symbols, paths as needed
```

**Step 2:** Consult **`config_schema.yaml`** when customizing
- Check comments for field explanations
- Identify optional vs. required fields

**Step 3:** Reference **`TEMPLATE_config.yaml`** for advanced features
- Environment variable setup
- Monitoring and alerting
- Production deployment considerations

---

### For Developers

**Adding New Config Options:**

1. **Document in `config_schema.yaml`** first
   - Add field with inline comment explaining purpose
   - Mark as `(optional)` if not required
   - Provide example value

2. **Update `sample_config.yaml`** if critical
   - Only add if needed for minimal working example
   - Use sensible default value

3. **Update `TEMPLATE_config.yaml`** if relevant
   - Add to appropriate section
   - Include markdown explanation if complex

---

## Validation

### Automated Checks

Create `orbit/ops/validate_config.py`:

```python
import yaml
from schema import Schema, Optional, And

config_schema = Schema({
    'project': {
        'name': str,
        'version': int
    },
    'paths': {
        'data_dir': str,
        'models_dir': str,
        # ... all required paths
    },
    'universe': {
        'symbols': [str],
        'benchmark': str
    },
    # ... rest of schema
})

def validate_config(config_path):
    """Validate config file against schema."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    config_schema.validate(config)
    print(f"✓ {config_path} is valid")

if __name__ == "__main__":
    import sys
    validate_config(sys.argv[1])
```

**Usage:**
```bash
python -m orbit.ops.validate_config orbit.yaml
```

---

### Manual Checklist

Before committing changes to any config file:

- [ ] All three files documented in this reconciliation
- [ ] Key structural differences explained
- [ ] Inconsistencies identified and resolution planned
- [ ] `sample_config.yaml` remains valid YAML (no syntax errors)
- [ ] `config_schema.yaml` comments updated for new fields
- [ ] `TEMPLATE_config.yaml` markdown sections clear
- [ ] Environment variable syntax consistent (`${VAR_NAME}`)
- [ ] All API keys/secrets use env vars, never hardcoded

---

## Recommendation Summary

| File | Action | Priority |
|------|--------|----------|
| **config_schema.yaml** | Add monitoring section, env var syntax docs | High |
| **sample_config.yaml** | No changes (already correct) | N/A |
| **TEMPLATE_config.yaml** | Standardize structure to match schema | Medium |
| **All** | Standardize reddit.max_items_per_run=1500 | Low |
| **Documentation** | Create this reconciliation doc (done ✓) | High |

---

## Related Files

* `03-config/config_schema.yaml` — Reference schema
* `03-config/sample_config.yaml` — Working example
* `99-templates/TEMPLATE_config.yaml` — Comprehensive template
* `03-config/env_keys.md` — Environment variable setup guide
* `10-operations/monitoring_dashboards.md` — Monitoring implementation
