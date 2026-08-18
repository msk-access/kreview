# Installation Guide

`kreview` is built to be a high-performance evaluation environment. It depends on DuckDB, XGBoost, SHAP, and scientific Python libraries.

## Requirements

- Python ≥ 3.10
- `pip` (latest)

---

## Environment Setup

> [!IMPORTANT]
> The report is a single self-contained HTML rendered directly by `kreview report` — no external tooling (Quarto was removed in the #79 report redesign).

### Option 1: Docker (Recommended "Batteries-Included" Method)
The easiest way to run `kreview` without managing external dependencies is to use our pre-built Docker container (hosted on GHCR). It ships with `Python 3.12` and all ML libraries:
```bash
docker pull ghcr.io/msk-access/kreview:latest
docker run -v /your/data:/data ghcr.io/msk-access/kreview:latest \
  label --cancer-samplesheet /data/cancer.csv ...   # stages are driven by Nextflow
```
For more complex execution commands (e.g., binding multiple access paths), see the [Docker Operations Guide](../operations/docker.md).

### Option 2: Local Install (Pip)


Then clone the repository. `kreview` is developed entirely using `nbdev`, so the source notebooks (`nbs/`) act as the active execution environment.

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

    For GPU model evaluation (TabPFN, TabICL and fine-tuned variants), install with GPU extras:
    ```bash
    pip install -e '.[gpu]'
    ```
    This adds `tabpfn`, `tabicl`, `shapiq`, and `torch` as dependencies.

=== "Developer Install"
    Install with all linting, testing, CI, and documentation tools bundled:
    ```bash
    pip install -e '.[all]'
    ```

### Optional Sub-Packages
If you only need specific toolchains instead of the full `all` suite:
- **Jupyter Only**: `pip install -e '.[jupyter]'`
- **Testing Only**: `pip install -e '.[test]'`
- **Docs Only**: `pip install -e '.[docs]'`
- **Multimodal selectors (GrootCV/Leshy)**: `pip install -e '.[arfs]'` — required for
  `--multimodal-selection grootcv|leshy` (the containers ship it by default).

!!! warning "`[arfs]` and `[legacy-boruta]` are mutually exclusive"
    The deprecated `boruta_shap` selector needs `pip install -e '.[legacy-boruta]'`, which
    **cannot coexist** with the `arfs` extra: BorutaShapPlus pins `numpy<=2.0.0` while
    arfs 3.0 requires `numpy>=2.0.2` — pip refuses any environment containing both.
    `legacy-boruta` exists only to reproduce pre-#96 runs.

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
