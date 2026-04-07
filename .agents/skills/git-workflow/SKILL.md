---
name: git-workflow
description: Git workflow conventions, conventional commits, and PR patterns for kreview
---

# Git Workflow Patterns

## Conventional Commits Quick Reference

| Prefix | When to Use | Example |
|---|---|---|
| `feat` | New evaluator, metric, visualization | `feat(fsc): add FSC.gene evaluator` |
| `fix` | Bug fix in existing code | `fix(labels): handle missing IMPACT sample` |
| `refactor` | Code restructuring, no behavior change | `refactor(eval): extract common plotting` |
| `docs` | mkdocs pages, docstrings, README | `docs(labeling): add hierarchy flowchart` |
| `test` | New/fixed test cells | `test(fsc): add edge case for empty parquet` |
| `chore` | Dependencies, CI, build config | `chore: bump duckdb to 1.2.0` |
| `data` | Label configs, thresholds | `data(labels): add VAF 2% config` |

## Branch Strategy

```
main ← stable releases only
  └── develop ← integration branch
       ├── feature/fsc-gene-evaluator
       ├── feature/wps-background-evaluator
       ├── fix/labels-missing-impact
       └── docs/quickstart-guide
```

## Merge Strategy
- **feature → develop**: Squash merge (clean history)
- **develop → main**: Merge commit (preserves history)
- **hotfix → main**: Cherry-pick + back-merge to develop

## PR Checklist (copy into PR description)
```markdown
- [ ] `ruff check` passes
- [ ] `black --check` passes
- [ ] `nbdev-test` passes
- [ ] `mkdocs build --strict` passes
- [ ] No `.parquet` or data files committed
- [ ] Conventional commit messages
- [ ] Docstrings on all public functions
```
