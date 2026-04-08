# Installation Guide

`kreview` is built to be a high-performance evaluation environment. Because of heavy dependencies like DuckDB, XGBoost, and scientific libraries, we highly recommend using `mamba` to resolve the environment quickly.

## Requirements
- `mamba` or `conda`
- Storage space locally for intermediate caches (Mac FUSE or equivalent for network mounts).

## Environment Setup

### 1. Clone the Source
First, pull down the repository. `kreview` is developed entirely using `nbdev`, so the source notebooks (`nbs/`) act as the active execution environment.

```bash
git clone https://github.com/msk-access/kreview.git
cd kreview
```

### 2. Scaffold the Mamba Environment
Use the provided `environment.yml` to build the `kreview-eval` isolated environment.

```bash
mamba env create -f environment.yml
conda activate kreview-eval
```

### 3. Install the Library
Install the `kreview` Python module itself, along with the optional documentation dependencies so you can build exactly what you see here.

```bash
python -m pip install -e '.[docs]'
```

!!! tip "Development Hook"
    If you are planning to write code or commit to the repo, we highly suggest running `nbdev_install_hooks` right now! This prevents massive diffs in Jupyter notebooks from blowing up the git commit history.

---

## 4. Verification Check

To quickly verify that the Command Line Interface (CLI) was successfully mapped to `typer`:

```bash
kreview --help
```

You should see an output tree listing `run` and `export`. If so, you're clear to proceed to [Configuration](configuration.md)!
