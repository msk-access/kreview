---
description: Full quality assurance sweep before merging to main
---

// turbo
1. Run lint:
   ```bash
   ruff check kreview/
   ```

// turbo
2. Check formatting:
   ```bash
   black --check kreview/
   ```

// turbo
3. Type checking:
   ```bash
   mypy kreview/ --ignore-missing-imports
   ```

// turbo
4. Run ALL tests:
   ```bash
   nbdev-test --n_workers 4
   ```

// turbo
5. Export modules (verify notebooks export cleanly):
   ```bash
   nbdev-export
   ```

// turbo
6. Build docs (verify no broken links):
   ```bash
   mkdocs build --strict
   ```

7. Check for uncommitted changes:
   ```bash
   git status
   git diff --stat
   ```

8. Verify no data files accidentally staged:
   ```bash
   git diff --cached --name-only | grep -E '\.(parquet|tsv|csv)$'
   ```

9. If all pass, report:
   ```
   ✅ QA PASS
   - ruff: clean
   - black: formatted
   - mypy: 0 errors
   - nbdev-test: X/X passed
   - mkdocs: builds clean
   - git: clean working tree
   ```
