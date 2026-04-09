# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1] - 2026-04-09
### Added
- Formally released the production-grade `kreview` Evaluation Framework for fragmentomics features.
- Five-tier classification algorithm implemented for accurate clinical ctDNA labeling: `Possible ctDNA−`, `True ctDNA+`, `Possible ctDNA+`, `Healthy Normal`, `Malignancy (Heme)`.
- Scikit-learn Pipeline injection to eliminate cross-fold scaling leakage during standard ML `evaluate_feature`.
- DuckDB I/O optimizations strictly mapping internal batch chunks dynamically configured for Desktop (`--chunk-size 50`) and HPC SLURM networks (`--chunk-size 500`).
- Integrated dynamic `kaleido` plotting backends for clinical PDF Quarto workflows.
- Dedicated Nextflow NF-Core DSL2 environment scaling wrapper specifically designed to ingest `manifest.txt` parameters recursively without crushing symmetric `work/` limits.
- GitHub Container Registry release pipeline (`ghcr.io/msk-access/kreview`) fully established utilizing OCI registry labels.

### Fixed
- Out-of-fold probability caching logic strictly refactored away from simplistic aggregation bias.
- Hardcoded `papermill` exceptions mapped into modular pipeline architecture.
- Replaced ambiguous test metrics with explicitly verified Benjamini-Hochberg (FDR) corrections over Mann-Whitney metrics.
