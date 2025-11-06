# ORBIT — LLM Operator Guide (Architecture)

*Last edited: 2025-11-05*

This guide explains how an LLM should interact with the **architecture specs** in `docs/02-architecture/*` when building or editing ORBIT.

## Read order (before making changes)

1. `system_diagram.md` — big‑picture pipeline & timing.
2. `dataflow_prices_news_social.md` — exact modality flows and cutoff rules.
3. `modules_inventory.md` — which module to edit/create and its acceptance checks.
4. `/CLAUDE.md` — global guardrails.

## Change workflow

1. **Identify module** to modify from `modules_inventory.md`.
2. **Open the relevant spec** (ingestion, preprocessing, features, modeling, evaluation) and confirm:

   * Inputs/outputs field names
   * Time rules (cutoff, lags)
   * Acceptance checks
3. **Edit the spec** if ambiguity exists (update *Last edited*).
4. **Implement** minimal changes in code.
5. **Run acceptance checks** for that module and record results.
6. **Run ablations/backtest** if modeling changed.
7. **Update docs** with any behavioral changes and the date.

## Must‑enforce rules

* **Point‑in‑time**: never use records with `published_at/created_utc > 15:30 ET` for day T features.
* **Anti‑dup**: cluster and count each story/post only once per day for intensity metrics.
* **Z‑scoring**: follow `docs/07-features/standardization_scaling.md` window/caps and NA rules.
* **Gates**: keep gate outputs in `[0,1]`; up‑weight text only when intensity/novelty is elevated.
* **Reproducibility**: same inputs + seed ⇒ identical outputs within tolerance.

## When in doubt

* Prefer **editing docs** to inventing new files.
* Ask for **acceptance checks** you can verify automatically.
* Keep **diffs atomic** and aligned to one module at a time.

## Acceptance checklist

* You can point to the exact lines in 02‑architecture that define: (a) cutoff rule, (b) novelty computation, (c) gate inputs.
* You can name the inputs/outputs for the module you plan to change.
* You updated the relevant doc’s Last edited date before implementing.

---

## Related Files

* `03-config/config_schema.yaml` — Configuration structure
* `06-preprocessing/time_alignment_cutoffs.md` — Anti-leak rules
* `99-templates/*.md` — LLM-friendly templates
