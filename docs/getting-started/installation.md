# Installation Guide

`kreview` is built to be a high-performance evaluation environment. It depends on DuckDB, XGBoost, SHAP, and scientific Python libraries.

## Requirements

- Python ≥ 3.10
- `pip` (latest)

---

## Environment Setup

### 1. Clone the Source

`kreview` is developed entirely using `nbdev`, so the source notebooks (`nbs/`) act as the active execution environment.

```bash
git clone https://github.com/msk-access/kreview.git
cd kreview
```

### 2. Install the Package

=== "User Install"

    Install the core package with all runtime dependencies:

    ```bash
    pip install -e .
    ```

=== "Developer Install"

    Install with linting, testing, and documentation tools:

    ```bash
    pip install -e '.[dev,test,docs]'
    ```

=== "Docs Only"

    If you only want to build or preview the documentation:

    ```bash
    pip install -e '.[docs]'
    mkdocs serve
    ```

### 3. Install Git Hooks

!!! tip "Development Hook"
    If you are contributing code, install the pre-commit hooks to automatically strip Jupyter notebook metadata and run linters before each commit:

    ```bash
    nbdev-install-hooks
    pre-commit install
    ```

---

## 4. Verification Check

To quickly verify that the CLI was successfully mapped:

```bash
kreview --help
```

You should see an output tree listing `run`, `label`, `features-list`, and `report`. If so, you're clear to proceed to [Configuration](configuration.md)!

!!! info "Listing Registered Features"
    You can immediately verify all 26 feature evaluators are discoverable:
    ```bash
    kreview features-list
    ```
