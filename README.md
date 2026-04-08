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

`kreview` is a production-grade, notebook-first (`nbdev`) evaluation engine designed strictly for high-throughput cancer liquid biopsy fragmentomics feature analysis. Designed at Memorial Sloan Kettering (MSKCC), it securely processes enormous arrays containing tens of thousands of samples using an embedded DuckDB multi-threaded memory lake.

## 🚀 Features

- **Biological 4-Tier ctDNA Taxonomy**: Mathematical MSK-IMPACT paired-inference to securely label `True ctDNA+`, `Possible ctDNA+`, `Possible ctDNA-`, and `Healthy Normal` baselines. 
- **DuckDB Dynamic Data Lake**: In-memory `read_parquet` bindings mapped directly to SFTP network mounts to bypass file I/O limitations. Automatically builds a merged SQL-queryable `kreview_lake.duckdb` file when finished.
- **Cyber-Aesthetic Dashboards**: Programmatic Quarto generation! Constructs deeply educational, Plotly-native visual diagnostic layouts (Themes: Cyborg/Neon Amber). 
- **Scalable Multiprocessing**: Dispatches features sequentially globally but aggressively parallelizes patient data locally to map matrices rapidly without disk locking.
- **20+ Built-In Modular Evaluators**: Contains fully independent mathematical extractors out-of-the-box (MDS, FSD, WPS, Motif Densities, ATAC Coverage, etc.).

## ⚙️ Quick Start

### Installation
The environment is strictly controlled using `mamba` to securely resolve the Quarto, DuckDB, plotting, and algorithmic ML backends:

```bash
git clone https://github.com/msk-access/kreview.git
cd kreview
mamba env create -f environment.yml
mamba activate kreview-eval
```

### Running the Global Engine
To aggressively scan an SFTP network data mount across 4 parallel instances and produce the absolute matrix evaluations:

```bash
PYTHONUNBUFFERED=1 kreview run \
  --cancer-samplesheet "/path/to/cancer/samplesheet.csv" \
  --healthy-xs1-samplesheet "/path/to/healthy/xs1/samplesheet.csv" \
  --cbioportal-dir "/path/to/cBioPortal_MAF_CNA_SV/" \
  --krewlyzer-dir "/path/to/unified_krewlyzer_results" \
  --output output/ \
  --workers 4 \
  --export-duckdb
```

### Dashboard Access
Once finished natively parsing all ~22 analytical features, Quarto recursively spins up visual `.html` reports locally across all evaluated feature sets:
```bash
open output/reports/ATAC_dashboard.html
```

## 🏗️ nbdev Architecture
This project proudly operates fundamentally as an `nbdev` repo!
Do **not** edit `.py` scripts manually in `/kreview`. Build natively inside Jupyter notebooks within `nbs/` and trigger:
```bash
nbdev_export
```

**Developer Workflows Built-in:**
- `/run-eval`
- `/add-feature`
- `/release`
