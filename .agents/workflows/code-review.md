---
description: Automated code review checklist for a PR or diff
---

1. Identify the files changed:
   ```bash
   git diff --name-only origin/main..HEAD
   ```

2. For each changed file, review against these criteria:

   ### Architecture
   - [ ] Does this follow the FeatureEvaluator pattern?
   - [ ] Is DuckDB used for cross-sample loading (not pandas loops)?
   - [ ] Are labels joined correctly (inner join on SAMPLE_ID)?

   ### Code Quality
   - [ ] All functions have type hints and docstrings?
   - [ ] No `print()` — using `log.info/warn/error`?
   - [ ] No hardcoded paths — using config or CLI args?

   ### Performance
   - [ ] No unnecessary DataFrame copies?
   - [ ] DuckDB SQL filters before `.df()` conversion?
   - [ ] Sklearn models use `random_state` for reproducibility?

   ### Testing
   - [ ] Every `#| export` cell has a corresponding `#| test` cell?
   - [ ] Edge cases: empty DataFrames, single-sample cancer types?

   ### Security / Data
   - [ ] No PHI/PII logged or committed?
   - [ ] Sample IDs only — no patient identifiers?

3. Output findings as a structured report with:
   - ✅ PASS / ⚠️ WARN / ❌ FAIL for each category
   - Specific file:line references for issues
   - Suggested fixes
