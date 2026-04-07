---
description: Git conventions for kreview development
alwaysApply: true
---

# Git Conventions

## Conventional Commits (MANDATORY)

All commits MUST follow conventional commits format:

```
<type>(<scope>): <description>

[optional body]
```

| Type | Use For |
|---|---|
| `feat` | New feature (evaluator, metric, visualization) |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `docs` | Documentation only (mkdocs, docstrings) |
| `test` | Adding/fixing tests |
| `chore` | Build, CI, dependency updates |
| `data` | Label definitions, feature configs |

**Scopes** (optional but encouraged):
`labels`, `fsc`, `fsd`, `fsr`, `wps`, `ocf`, `mds`, `motif`, `eval`,
`scoreboard`, `cli`, `docs`, `duckdb`, `ci`

**Examples:**
- `feat(fsc): add FSC.gene evaluator notebook`
- `fix(labels): handle missing IMPACT sample gracefully`
- `refactor(eval): extract common plotting to base class`
- `docs(labeling): add 4-tier hierarchy flowchart`

## Branch Naming

```
feature/<scope>-<description>    # feature/fsc-gene-evaluator
fix/<scope>-<description>        # fix/labels-missing-impact
docs/<description>               # docs/quickstart-guide
release/<version>                # release/0.1.0
```

## Commit Discipline

- **Atomic commits**: One logical change per commit
- **Never commit**: `.ipynb_checkpoints/`, `__pycache__/`, `.parquet` data files
- **Run before every commit**:
  ```bash
  ruff check kreview/
  black --check kreview/
  nbdev-test --n_workers 4
  ```
- **Squash** trial-and-error commits before merging to `main`

## Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/psf/black
    rev: 25.1.0
    hooks:
      - id: black
```
