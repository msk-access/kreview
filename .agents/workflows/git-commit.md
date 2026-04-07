---
description: Stage changes, run lint, format commit message, and commit
---

1. View all staged and unstaged changes:
   ```bash
   git status
   git diff --stat
   ```

2. Stage relevant changes (interactive if needed):
   ```bash
   git add -p  # or specific files
   ```

// turbo
3. Run the lint suite:
   ```bash
   ruff check --fix kreview/ && black kreview/
   ```

// turbo
4. Run nbdev-test to verify nothing is broken:
   ```bash
   nbdev-test --n_workers 4
   ```

5. Review the staged diff to determine commit type and scope:
   ```bash
   git diff --cached --stat
   ```

6. Generate a conventional commit message based on the staged changes:
   - Use the format: `type(scope): description`
   - Include body if changes are non-trivial
   - Reference issue numbers if applicable

7. Commit with the generated message:
   ```bash
   git commit -m "<generated message>"
   ```
