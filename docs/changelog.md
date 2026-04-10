# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
## [0.0.6] - 2026-04-10
### Fixed
- **Bin-Level Extractor Coverage Filtering**: Fixed critical data bug where FSC and FSR on-target extractors computed `median()` across all 28,823 genomic bins, including the 98% with zero coverage. The zero-coverage sentinel values (`-29.897` for log2, `0.0` for ratios) dominated the median, producing constant features and AUC=0.500 for all models. Now filters to `total > 0` bins before aggregation.
- **SHAP Feature Shape Mismatch**: Fixed `TreeExplainer` crashes caused by passing a feature-subset matrix instead of the full model-trained feature set. SHAP now computes on all 50 model features; `--shap-features` only limits visualization display count.
- **SHAP Binary Output Handling**: Added robust handling for all `TreeExplainer` return shapes (list, 3D array, 2D array) and safe `expected_value` extraction for binary classifiers.
- **Error Visibility**: Changed Quarto stderr capture from first 500 chars to last 1500 chars, surfacing actual Python errors instead of kernel boot messages.

### Added
- **Nextflow HPC Parity**: Wired all new CLI flags (`--top-n`, `--shap-samples`, `--shap-features`, `--resume`, `--skip-report`, `--cvd-safe`) into Nextflow `nextflow.config` and `run.nf` with HPC-optimized SLURM defaults (10-fold CV, 5000 SHAP samples, 64GB RAM).
- **CLI Configuration Logging**: All three commands (`label`, `run`, `report`) now log their full parameter state at startup for reproducibility.
- **Resume Support**: `--resume` flag skips evaluators with existing model results, enabling incremental re-runs.
- **Variance Guard**: CLI automatically drops zero-variance features before model training with a logged warning, preventing wasted compute on constant columns.
- **Coverage Monitoring**: All bin-level extractors now emit `n_covered_bins` and `n_total_bins` in the feature matrix for downstream QC.

### Changed
- **Memory Management**: Aggressive dashboard optimization — subsampled KDE plots (2000 samples), `gc.collect()` between SHAP runs, explicit dataframe deletion after filtering.
- **SHAP Explainer**: Switched from generic `shap.Explainer` to `shap.TreeExplainer` to prevent OOM-causing `KernelExplainer` fallback.
- **HPC Resource Allocation**: `process_high` memory increased from 32GB to 64GB for SHAP-heavy report generation.

## [0.0.5] - 2026-04-09
### Fixed
- **PyPI Release Wheel Artifact Synchorization**: Enforced a permanent "Triple Bump" protocol standardizing manual version matching globally across `settings.ini`, `nextflow.config`, and `kreview/__init__.py` natively. This resolves a decoupling bug that structurally blocked Github Actions `python -m build` commands from publishing Wheels accurately tracking downstream package footprints correctly.

## [0.0.4] - 2026-04-09
### Fixed
- **Documentation Sync**: Hardcoded the `mike` version provider default target alias gracefully to `latest` intrinsically allowing GitHub Action GH-Pages orchestration arrays to map tags seamlessly.
- **Git Flow Constraints**: Implemented official mandatory 8-step PR-driven workflow structures strictly bypassing raw fast-forward terminal merges blocking CI.

## [0.0.3] - 2026-04-09
### Added
- **Global Config Parity**: Synchronized dynamic execution limits tracking across native Python modules (v0.0.3) and HPC workflow blocks (`nextflow.config` 0.0.3).
- **Core CLI Flags**: Engineered `@app.callback()` directly into `kreview` Typer infrastructure enabling standalone `--version` invocation blocks natively supporting Nextflow `software_versions.yaml` registry capture logging.

### Fixed
- **Systemic Module Sync**: Repaired native `__init__.py` decoupling bugs where sequential tool paths caused legacy `0.0.1` footprints to bypass metadata injections.
- **Git Asset Purge**: Permanently bound dynamic CLI Quarto runtimes (`html`, `static_plots`, `nohup`) directly inside `.gitignore` blocking blob registry accumulation remotely.
- **CI Formatting**: Established uniform `black .` compliance thresholds natively locking both `nbs/` JSON source notebooks and `/kreview` Python exports securely for Github Actions lint workflows.

## [0.0.2] - 2026-04-09
### Added
- **Diagnostic Upgrades**: Implemented explicit Sensitivity and Specificity clinical evaluations automatically calculating Youden's J static cutoffs and logging metrics securely to the results JSON matrix.
- **Model Expansion**: Added scalable `XGBoost` modeling alongside native `Random Forest` and `Logistic Regression` classifiers inline.
- **Theme Selection**: Introduced `set_theme()` support parsing `--cvd-safe` toggle parameters. Allows zero-friction toggling between Okabe-Ito (colorblind secure) and global Muted Neon visualization workflows.
- **Cluster Deployment Optimization**: Injected `[all]` pip extra support resolving seamless multi-tool HPC dependencies smoothly (`pip install -e ".[all]"`). 

### Fixed 
- **Dashboard Standalone Render**: Resolved `format: dashboard` clipping anomalies resulting from undocumented Quarto `_quarto.yml` project context bleeding. Hardcoded formatting constraints dynamically allowing pipeline usage deeply isolated in site-packages perfectly.
- **Path Resolution Hacks**: Removed namespace package AST resolution assumptions and substituted secure `__file__` contextual path checks, completely resolving editable `pip install -e .` template `NoneType` bugs natively.
- **CLI Options**: Restored destroyed `--verbose` option parsing.

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
