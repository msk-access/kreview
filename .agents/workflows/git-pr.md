---
description: Create a pull request with a standardized description template
---

1. Ensure branch is up to date:
   ```bash
   git fetch origin main
   git log --oneline origin/main..HEAD
   ```

// turbo
2. Run the full QA check first:
   ```bash
   ruff check kreview/ && black --check kreview/ && nbdev-test --n_workers 4
   ```

3. Collect all commits since branching:
   ```bash
   git log --oneline origin/main..HEAD
   ```

4. Push the branch:
   ```bash
   git push -u origin $(git branch --show-current)
   ```

5. Generate the PR description using this template:

   ```
   ## What
   [One sentence: what this PR does]

   ## Why
   [Context: what problem it solves or what need it addresses]

   ## How
   [Technical approach — key design decisions, algorithms, trade-offs]

   ## Changes
   - [ ] file1.py — description
   - [ ] file2.ipynb — description

   ## Testing
   - [ ] `nbdev-test` passes
   - [ ] Lint clean (`ruff check` + `black --check`)
   - [ ] Manual verification: [describe]

   ## Breaking Changes
   [None / list any breaking API or output format changes]
   ```

6. Create the PR using `gh` CLI:
   ```bash
   gh pr create --title "<type(scope): description>" --body "<generated description>"
   ```
