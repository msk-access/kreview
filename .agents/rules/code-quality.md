---
description: Code quality standards for kreview
alwaysApply: true
---

# Code Quality Standards

## ⚠️ Step Review Discipline (MANDATORY)

**BEFORE implementing each step:**
- [ ] Review existing code for reuse — do NOT re-implement what already exists
- [ ] Identify shared patterns that should be extracted to helpers
- [ ] Check for functions that can be generalized instead of duplicated

**AFTER implementing each step:**
- [ ] Audit for code duplication — extract shared logic to `kreview.core`
- [ ] Audit for unused code — delete dead functions, imports, variables
- [ ] Audit for silent failures — every `except` must log or re-raise
- [ ] Update commenting — all new functions have docstrings, complex logic has "why" comments
- [ ] Update logging — all significant operations have structured log entries
- [ ] Update monitoring — timing/counts for data operations, progress for long loops

**AFTER implementing, compare code against implementation plan:**
- [ ] Re-read the relevant plan section(s) for the phase just completed
- [ ] Diff what was implemented vs. what the plan specified
- [ ] If there are **gaps** (plan items not yet implemented):
  - Classify each as **intentional** (deferred, out-of-scope, design changed) or **unintentional** (missed)
  - **Notify the user** with a summary: what was skipped, why, and whether it needs follow-up
  - Update the plan with a note if the gap is intentional (e.g., "deferred to Phase N")
- [ ] If the implementation **diverged** from the plan (different approach, extra code):
  - Update the plan to reflect reality — the plan must always match the code
  - Explain the rationale for the divergence to the user

> This rule was introduced after discovering that AI-assisted development can introduce
> subtle duplication and silent failures that accumulate across implementation steps.

## Lint Suite — Run Before Every Commit

```bash
# 1. Auto-fix import/style issues
ruff check --fix kreview/ nbs/

# 2. Format
black kreview/

# 3. Type checking
mypy kreview/ --ignore-missing-imports

# 4. Run nbdev tests
nbdev-test --n_workers 4
```

## Required in All Code

- [ ] All public functions have type hints
- [ ] All public functions have docstrings (Google style)
- [ ] Use `logging` module, NOT `print()` — configured via structlog
- [ ] All modules define `__all__` for explicit exports
- [ ] No commented-out code (use version control)

## No Duplication

- [ ] Common DataFrame operations (load, merge, filter) use shared helpers from `kreview.core`
- [ ] Plotting functions reused from `kreview.eval.viz`, not re-implemented per feature
- [ ] Statistical tests called from `kreview.eval.stats`, not inlined
- [ ] If you write similar code twice, extract it immediately

## No Silent Failures

- [ ] Every `try/except` either logs the exception or re-raises
- [ ] Every `if not data: return` logs what was skipped and why
- [ ] Empty DataFrames always logged: `log.warning("empty_result", feature=..., reason=...)`
- [ ] Failed model fits logged: `log.error("model_failed", feature=..., error=str(e))`
- [ ] Missing files logged: `log.warning("file_missing", path=..., sample_id=...)`

## Commenting, Logging & Monitoring

### Commenting
- [ ] All modules: top-level docstring explaining purpose
- [ ] All public functions: Google-style docstrings with Args/Returns
- [ ] Complex logic: inline comments explaining "why", not "what"
- [ ] Decision points: comment the rationale (e.g., "# Use RF here because feature is multi-dimensional")

### Logging (structlog)
```python
# ✅ Good: structured, queryable
log.info("feature_extracted", feature="FSC.gene", n_samples=4021, elapsed_sec=3.2)
log.warning("underpowered_stratum", cancer_type="ACC", n_positive=3, min_required=10)
log.error("model_failed", feature="WPS.panel", error="singular matrix")

# ❌ Bad: unstructured f-strings
log.info(f"Loaded {n} samples")  # not queryable
print("done")  # NEVER use print
```

### Monitoring
- [ ] All DuckDB glob scans log: n_files_found, n_rows_loaded, elapsed_sec
- [ ] All evaluator runs log: feature_name, n_samples, n_strata, elapsed_sec
- [ ] All model fits log: model_type, n_features, auc, elapsed_sec
- [ ] Pipeline end-to-end log: total_elapsed, n_features_evaluated, n_strata_evaluated

## QC Checklist (Before PR)

### Input Validation
- [ ] All `Path` arguments validated with `.exists()` check
- [ ] All DataFrames validated for expected columns
- [ ] Informative error messages on missing data

### Error Handling
- [ ] Never silently swallow exceptions
- [ ] Use `log.warning()` for recoverable issues (e.g., underpowered strata)
- [ ] Use `raise` for unrecoverable issues (e.g., missing cBioPortal files)

### Performance
- [ ] Use DuckDB glob scans for cross-sample loading, not pandas loops
- [ ] No unnecessary DataFrame copies — use `df.copy()` only when needed
- [ ] Large DataFrames not held in memory longer than needed

### Testing
- [ ] All `#| export` cells have corresponding `#| test` cells
- [ ] Edge cases tested: empty DataFrames, single-sample strata, missing features
- [ ] Tests are deterministic — set random seeds for sklearn models
