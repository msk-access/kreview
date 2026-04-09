# Contributing to kreview

Thank you for your interest in contributing! Please see our full [Contributing Guide](https://msk-access.github.io/kreview/developer/contributing/) for detailed instructions on:

- Git branching model and commit conventions
- Development setup and the nbdev workflow
- Pull request checklist and code review standards
- Pre-commit hooks and linting configuration

## Quick Start

```bash
git clone https://github.com/msk-access/kreview.git
cd kreview
pip install -e '.[dev,test,docs]'
nbdev-install-hooks
pre-commit install
```

## Important

**Never edit `.py` files directly.** All code changes must be made in the Jupyter notebooks under `nbs/`, then exported with `nbdev-export`.
