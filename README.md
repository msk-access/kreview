<div align="center">
  <img src="https://img.shields.io/badge/Release-v0.1.0-FF9B42.svg" alt="Release Badge">
  <img src="https://img.shields.io/badge/nbdev-Enabled-blue.svg" alt="nbdev Badge">
  <img src="https://img.shields.io/badge/Powered_by-DuckDB-yellow.svg" alt="DuckDB Badge">
  <img src="https://img.shields.io/badge/Reports-Quarto-blueviolet.svg" alt="Quarto Badge">
  
  <h1>kreview</h1>
  <p><b>Advanced cfDNA Fragmentomics Core Evaluation Engine</b></p>
</div>

---

## 🧬 Overview

`kreview` is a production-grade, notebook-first (`nbdev`) evaluation engine designed for high-throughput cancer liquid biopsy fragmentomics feature analysis. Developed at Memorial Sloan Kettering (MSKCC), it processes cohorts containing tens of thousands of samples using an embedded DuckDB query engine with chunked I/O and automatic retry logic.

📖 **[Full Documentation](https://msk-access.github.io/kreview/)**

## 🚀 Features

- **5-Tier ctDNA Taxonomy**: MSK-IMPACT paired-inference to label `True ctDNA+`, `Possible ctDNA+`, `Possible ctDNA−`, `Healthy Normal`, and `Insufficient Data`.
- **DuckDB Dynamic Data Lake**: In-memory `read_parquet` bindings with chunked I/O and exponential backoff retry. Builds a merged SQL-queryable `kreview_lake.duckdb` on demand.
- **Multi-Model Evaluation**: Random Forest, XGBoost, and Logistic Regression with Stratified K-Fold CV, SHAP explainability, and subgroup analysis.
- **Interactive Dashboards**: Plotly-native HTML reports with ROC curves, violin plots, SHAP beeswarm/waterfall, and per-cancer-type sensitivity tables.
- **26 Built-In Evaluators**: Modular extractors covering fragment sizes (FSC, FSD, FSR), nucleosome protection (WPS, TFBS), cleavage motifs (EndMotif, BreakPointMotif), chromatin accessibility (ATAC), motif divergence (MDS), and orientation (OCF).

## ⚙️ Quick Start

### Installation

> [!IMPORTANT]
> **Quarto is strictly required** for programmatic dashboard generation. Because `quarto-cli` wrapper packages are unreliable across Python environments, `kreview` assumes the Quarto executable is installed dynamically on your OS or container.

#### Option 1: Docker (Recommended "Batteries-Included" Method)
The easiest way to run `kreview` without managing external dependencies is to use our pre-built Docker container (hosted on GHCR). It natively ships with `Python 3.12`, all ML libraries, and the underlying `quarto` linux binaries configured flawlessly:
```bash
docker pull ghcr.io/msk-access/kreview:latest
docker run -v /your/data:/data ghcr.io/msk-access/kreview:latest \
  kreview run --cancer-samplesheet /data/cancer.csv ...
```

#### Option 2: Local Install (Pip)
If you install via pip, you **must separately install Quarto** via your OS manager:
1. **Install Quarto:** Follow the [official Quarto Installation Guide](https://quarto.org/docs/get-started/) (e.g. `brew install quarto` on macOS).
2. **Install kreview:**
```bash
git clone https://github.com/msk-access/kreview.git
cd kreview
pip install -e .
```

### Running the Pipeline

```bash
PYTHONUNBUFFERED=1 kreview run \
  --cancer-samplesheet "/path/to/cancer/samplesheet.csv" \
  --healthy-xs1-samplesheet "/path/to/healthy/xs1/samplesheet.csv" \
  --healthy-xs2-samplesheet "/path/to/healthy/xs2/samplesheet.csv" \
  --cbioportal-dir "/path/to/cBioPortal_MAF_CNA_SV/" \
  --krewlyzer-dir "/path/to/unified_krewlyzer_results" \
  --output output/ \
  --workers 4 \
  --export-duckdb
```

### Dashboard Access

Once finished, open the generated HTML reports:
```bash
open output/reports/ATAC_dashboard.html
```

## 🏗️ nbdev Architecture

This project operates as an `nbdev` repo. Do **not** edit `.py` scripts manually in `kreview/`. Build natively inside Jupyter notebooks within `nbs/` and trigger:
```bash
nbdev-export
```

## 📚 Resources

- **[Documentation](https://msk-access.github.io/kreview/)** — Full user and developer guide
- **[Contributing](CONTRIBUTING.md)** — How to contribute
- **[Changelog](https://msk-access.github.io/kreview/changelog/)** — Version history
