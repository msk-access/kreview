# Installation Guide

`kreview` is built to be a high-performance evaluation environment. It depends on DuckDB, XGBoost, SHAP, and scientific Python libraries.

## Requirements

- Python ≥ 3.10
- `pip` (latest)

---

## Environment Setup

> [!IMPORTANT]
> **Quarto is strictly required** for programmatic dashboard generation. Because `quarto-cli` wrapper packages are unreliable across Python environments, `kreview` assumes the Quarto executable is installed dynamically on your OS or container.

### Option 1: Docker (Recommended "Batteries-Included" Method)
The easiest way to run `kreview` without managing external dependencies is to use our pre-built Docker container (hosted on GHCR). It natively ships with `Python 3.12`, all ML libraries, and the underlying `quarto` linux binaries configured flawlessly:
```bash
docker pull ghcr.io/msk-access/kreview:latest
docker run -v /your/data:/data ghcr.io/msk-access/kreview:latest \
  kreview run --cancer-samplesheet /data/cancer.csv ...
```
For more complex execution commands (e.g., binding multiple access paths), see the [Docker Operations Guide](../operations/docker.md).

### Option 2: Local Install (Pip)

First, you **must separately install Quarto** via your OS manager:
Follow the [official Quarto Installation Guide](https://quarto.org/docs/get-started/) (e.g. `brew install quarto` on macOS).

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
