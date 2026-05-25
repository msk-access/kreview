# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Reproducibility Seed**: `--seed` CLI flag on `run`, `eval cpu`, `eval gpu`, `eval multimodal`, and `select` commands (default: 42).
- **Deterministic Mode**: `--deterministic / --no-deterministic` flag for PyTorch cudnn (default: True) on all eval commands.
- **`kreview/reproducibility.py`**: `seed_everything()` utility for Python, PyTorch, and cuDNN seeding.
- **Nextflow Params**: `seed` and `deterministic` params in `nextflow.config`, forwarded through all 8 pipeline modules.
- **Reproducibility Docs**: New section in `models-and-metrics.md` documenting seed propagation strategy.

### Fixed
- 3 hardcoded `random_state=42` in `_select_multimodal_features()` now accept caller seed.
- 7 internal forwarding gaps where `random_state` was not passed to child functions.
- GPU models (TabPFN, TabICL) now receive `random_state` parameter via `_build_gpu_model()`.
- `shapiq.TabularExplainer` and `shap.PermutationExplainer` now seeded for reproducible SHAP values.
- `BorutaShap.fit()` now receives `random_state` for deterministic feature selection.
- **SLURM Partition Routing**: All `withName` process blocks now pin `queue` explicitly to bypass the nf-core iris institutional config's dynamic queue closure that injects the inaccessible `cpu` partition into `sbatch -p`.
- **KREVIEW_LABEL Error Strategy**: Changed from inherited `'ignore'` (from iris config) to `'terminate'` — pipeline aborts immediately if labeling fails instead of deadlocking.

## [0.0.13] - 2026-05-24

### Added
- **GPU Foundation Models**: TabPFN v8.0.3 and TabICL v2.1 support via `_build_gpu_model()` with updated import paths (`tabpfn.TabPFNClassifier`, `tabicl.TabICLClassifier`).
- **shapiq Integration**: SHAP values for GPU models now computed via `shapiq.TabularExplainer` (model-agnostic kernel-based Shapley values), replacing the deprecated `tabpfn-extensions` interpreter.
- **Unified Model Persistence**: `_save_fitted_models()` helper in `cli_eval.py` provides consistent joblib saves for both CPU and GPU models. `--skip-gpu-joblib` flag opts out of large GPU model files.
- **Multimodal GPU Models**: `kreview eval multimodal` now accepts `--gpu-models tabpfn,tabicl` for GPU-accelerated stacking and raw feature evaluation.
- **Pre-computed SHAP Fallback**: Report templates render mean |SHAP| bar charts from JSON when joblib files are unavailable (e.g., `--skip-gpu-joblib`).
- **KREVIEW_REPORT_MULTIMODAL**: New Nextflow process for rendering multimodal stacking dashboards in multistage mode.
- **HPC Script v0.0.13**: Updated SLURM launch script with GPU multimodal params, Boruta-SHAP selection, and top_percentile.

### Changed
- **Feature Selection**: `--top-percentile` replaces `--top-k` for MI-based feature selection. Percentage-based selection adapts to varying feature set sizes across evaluators.
- **Boruta-SHAP MI Reducer**: When Boruta-SHAP confirms >500 features, an MI-based reducer narrows the set to `top_percentile` (default 10%).
- **SLURM Hardening**: `KREVIEW_LABEL` and `KREVIEW_EVAL_GPU_SINGLE` processes now set `cache = 'lenient'` and `scratch = false` to prevent institutional queue/cache interference on IRIS.
- **Dynamic Report Rendering**: ROC CI reverse-map, DCA loop, and AUC deltas now dynamically discover models from `DYNAMIC_MODELS` instead of hardcoding LR/RF/XGB.

### Fixed
- **ROC CI KeyError**: Hardcoded `{"Logistic Regression": "lr", ...}` reverse-map in `report_template.qmd` replaced with dynamic lookup from `DYNAMIC_MODELS`, preventing crashes when GPU models are present.
- **DCA Loop**: DCA now renders curves for all trained models (was hardcoded to RF/XGB only).
- **AUC Deltas**: Pairwise AUC delta display now discovers all `auc_delta_*` keys dynamically.
- **Monolithic GPU Fitted Capture**: `gpu_res, gpu_fitted = gpu_models(...)` now captures fitted models (was `_ = ...`).

### Dependencies
- `tabpfn >= 8.0.3` (was `>= 2.0`)
- `tabicl >= 2.1` (was `>= 0.0.4`)
- Added `shapiq` for GPU model SHAP computation.

## [0.0.12] - 2026-05-24
### Added
- **Nextflow publishDir**: All 8 multistage modules now publish outputs to `params.outdir` with `mode: copy`. Output structure: `labels/`, `matrices/raw/`, `matrices/selected/`, `models/cpu/`, `models/gpu/`, `matrices/fused/`, `models/multimodal/`, `reports/`.
- **Label-first DAG**: `KREVIEW_LABEL` runs once as the first step in multistage mode, producing `labels.parquet` shared across all extract jobs. Eliminates 26× redundant re-labeling (~13 min saved).
- **`--labels` CLI flag**: `kreview extract` now accepts `--labels /path/to/labels.parquet` to skip internal labeling and use pre-computed labels.
- **Boruta-SHAP in HPC script**: `scripts/run_hpc_v0.0.11.sh` now passes `--multimodal_selection boruta_shap` for rigorous multimodal feature selection.

### Changed
- **Report DAG dependency**: Report process now receives both matrices AND `*_model_results.json` from CPU/GPU eval, enabling complete dashboard rendering (ROC, SHAP, metrics). Report runs in parallel with FUSE + MULTIMODAL.
- **Extract module**: `extract.nf` now accepts `labels.parquet` as input from upstream `KREVIEW_LABEL`.

### Documentation
- **README**: Comprehensive overhaul — added mRMR/Boruta-SHAP, GPU models, multimodal stacking, Nextflow HPC, pipeline architecture Mermaid diagram, fixed stale `--workers` flag.
- **Statistical Tests**: Detailed mRMR documentation (optimization objective, F-statistic/Pearson explanation, algorithm steps), Boruta-SHAP documentation (shadow features, SHAP importance, flowchart, configuration table, when-to-choose guide), fixed stale Selection QC keys.
- **Nextflow Operations**: Updated module list to match actual filenames, added `iris` profile docs, added publishDir output structure tree, added `parq-cli` tip.
- **Pipeline CLI**: Fixed stale `--workers 4`, added `--labels` to extract example, added `--ch-hotspot-maf`, added label-first modular pipeline flow, added `parq-cli` tip.
- **Pipeline Architecture**: Updated DAG (Label-first, Report parallel with Multimodal), fixed process table with actual `_single.nf` module names, added publishDir column.

## [0.0.11] - 2026-05-24
### Changed
- **Feature Selection (Default)**: Default single-evaluator strategy changed from `hybrid_union` to `mrmr` (Minimum Redundancy Maximum Relevance). mRMR selects features maximizing target correlation while minimizing inter-feature redundancy, preventing multi-collinearity.
- **Multimodal Selection**: `--multimodal-selection` now supports `boruta_shap` (interaction-aware, SHAP-based) in addition to `mi` (mutual information, default).
- **CLI Log Output**: `kreview select` and `kreview run` now display method-aware selection summaries (mRMR shows variance-dropped count; hybrid_union shows AUC∩MI overlap breakdown).

### Added
- **`mrmr-selection` dependency**: Added `mrmr-selection>=0.2.8` to `pyproject.toml`.
- **`BorutaShap` dependency**: Added `BorutaShap>=1.0.17` to `pyproject.toml`.
- **Structured startup logging**: `kreview select` and `kreview eval multimodal` now emit `log.info("select_start", ...)` and `log.info("eval_multimodal_start", ...)` at startup for machine-parseable audit trails.
- **Multimodal selection method persistence**: `multimodal_results.json` now includes `raw_features_selection_method` (`"mi"` or `"boruta_shap"`).
- **Selection Strategy value box**: Multimodal dashboard executive summary displays the cross-evaluator selection strategy.
- **Scoreboard `selection_method` column**: Now visible in both single-evaluator and multimodal dashboard scoreboard tables.
- **mRMR scatter disclaimer**: When `strategy="mrmr"`, the Feature Selection scatter plot displays a callout explaining that AUC/MI axes are observational (mRMR uses F-statistic + Pearson correlation internally).
- **mRMR scatter coloring**: Selected features labeled "Selected (mRMR)" with cyan color, distinct from hybrid_union's 4-way AUC/MI overlap coloring.

### Fixed
- **`KeyError` crash in `cli_select.py`**: Fixed crash when `--strategy mrmr` was used — the log output tried to access hybrid-union-only QC keys (`n_overlap_both`, `n_auc_only`, `n_mi_only`).
- **Misleading `cli.py` log output**: `kreview run --strategy mrmr` now shows mRMR-specific summary instead of zeroed-out hybrid_union counts.
- **Stale docstrings**: Updated module docstrings in `selection.py`, `cli_select.py`, `cli_eval.py`, and `eval_engine.py` to reflect mRMR as default.

## [0.0.10] - 2026-05-22
### Added
- **Modular CLI**: Extracted `run` into atomic sub-commands (`label`, `extract`, `fuse`, `eval`, `select`, `report`).
- **Nextflow DAG**: Complete rebuild of monolithic pipeline into a multi-stage, per-evaluator parallelized workflow.
- **GPU Evaluation**: Native support for PyTorch-based GPU models (TabPFN, TabICL) via the `kreview eval --gpu-models` target.
- **Multimodal Models**: Cross-evaluator stacking capability allowing evaluation of multiple fragmentomics assays simultaneously.
- **Testing Optimizaton**: Dropped unit testing execution time from >6min to <30s via module-scoped caching.
- **Docker Containers**: Stabilized multi-target release action generating discrete CPU and GPU containers cleanly.

## [0.0.9] - 2026-05-07
### Changed
- **Feature Selection**: Replaced Cohen's D `--top-n` selection with hybrid union: top X% by Univariate AUC ∪ top X% by Mutual Information. This captures both linear and non-linear predictors.
- **CLI**: `--top-n` deprecated (prints warning, ignored). Use `--top-percentile` (default: 10%) instead. `--compute-univariate-auc` now defaults to `True`.
- **Volcano Plot**: X-axis changed from Cohen's D to Univariate AUC for better alignment with model-based selection.
- **Top-20 Bar Chart**: Ranked by Univariate AUC instead of Cohen's D.
- **Statistical Ledger**: Sort priority changed to `univariate_auc > mutual_info > cohens_d > kw_statistic`.
- **Feature Cards**: Display AUC + MI scores instead of Cohen's D.

### Added
- **`mutual_info_score()`**: New function in `eval_engine.py` using `sklearn.feature_selection.mutual_info_classif(k=3)` for non-linear feature relevance scoring.
- **`selection_qc` metadata**: Saved in `model_results.json` with method, overlap stats, and feature counts for audit trail.
- **Feature Selection QC Scatter**: New dashboard plot showing AUC vs MI with 4-color category coding (Both / AUC-only / MI-only / Dropped).
- **Scoreboard columns**: `selection_method`, `n_selected_features`, `selection_overlap_pct`.
- **Structured logging**: `feature_scoring_complete`, `feature_selection_complete`, `univariate_auc_disabled`, `variance_guard_dropped`, `model_skip_insufficient_data`.
- **Resume checkpoint**: Warns on legacy JSONs missing `selection_qc` (pre-v0.0.9 Cohen's D runs).
- **Tests**: 13 new tests for `univariate_auc` (6) and `mutual_info_score` (7) covering bounds, NaN handling, constant features, signal detection, and reproducibility.
- **univariate_auc logging**: `log.warning("univariate_auc_failed")` replaces bare silent `except`.

### Fixed
- **Duplicate label mask** (GAP-1): Removed duplicate 4-tier label mask construction; reuse scoring target for model target.
- **Redundant import** (GAP-3): Removed `import structlog as _slog` inside evaluator loop; use module-level `log`.
- **Silent degradation** (GAP-4): Explicit warning when `--no-compute-univariate-auc` degrades to MI-only selection.
- **Double imputation** (GAP-6): Cached `_impute()` result in variance guard to avoid re-computation.
- **Silent model skip** (GAP-7): Added echo + structlog warning when model eligibility fails (< 20 samples or single class).

## [0.0.8] - 2026-05-06
### Fixed
- **AUC Consistency (D-01)**: ROC plots and KDE density now use out-of-fold predictions matching the official AUC value boxes. Eliminates the misleading AUC discrepancy (e.g., 0.845 vs 0.72) caused by mixing training/subsample models.
- **Dashboard Crashes (D-02/D-03)**: All `cohens_d_true_vs_healthy` references guarded with column existence checks. Statistical Ledger falls back to `kw_statistic` → `univariate_auc` when Cohen's D is unavailable.
- **Classification Labels (C-02)**: Confusion matrix and classification report now correctly show "ctDNA Negative" instead of "Healthy Normal".
- **Fold Variability (C-01)**: Now displays all three models (LR, RF, XGBoost) with per-model std in title instead of hardcoded RF-only.
- **Duplicate Imports (C-03)**: Removed redundant plotly import in report template.
- **Volcano Hover (GAP-1)**: NaN-safe hover text shows "N/A" instead of "nan" for zero-variance features.
- **JSON Bloat (GAP-6)**: OOF probability arrays rounded to 6 decimal places (~40% size reduction per evaluator).
- **HPC Memory (OOM)**: Base memory bumped 256→512GB for genome-wide evaluators (FSD, WPS).

### Added
- **Structured Logging**: `structlog`-based logging in CLI `report()` with per-evaluator timing, success/fail counts, and summary statistics.
- **Smart Resume (GAP-4)**: Resume checkpoint validates JSON freshness — warns if OOF keys are missing from pre-hardening runs.
- **SHAP Waterfall Guards (S-04)**: Validates array lengths before plotting to prevent IndexError.
- **SHAP Docstrings**: All three SHAP helper functions now have full docstrings.
- **Variable Initialization**: `oof_y`, `oof_preds`, and `kde_labels` initialized at template top level to prevent NameError when models fail.

### Removed
- `plot_threshold_sensitivity()` — dead code replaced by pre-computed threshold sweep in v0.0.7.
- Redundant `cross_val_score` import and second independent CV computation.
- Stale `plot_threshold_sensitivity` entry from `_modidx.py`.

## [0.0.7] - 2026-04-13
### Added
- **Dashboard Redesign**: Restructured from single-page to 6-page progressive disclosure hierarchy (Executive Summary, Model Validation, Feature Explanation, Biomarker Yield, Cohort & QC, Data Explorer).
- **XGBoost Integration**: Full XGBoost model evaluation alongside LR and RF in `single_feature_model()`.
- **Bootstrap AUC CIs**: 95% confidence intervals for all model AUCs using `scipy.stats.bootstrap`.
- **Decision Curve Analysis (DCA)**: Standalone `decision_curve_analysis()` function computing net clinical benefit across thresholds for RF and XGBoost models.
- **Precision-Recall Curves**: PR curves and average precision for all three models (LR, RF, XGBoost).
- **Fold-Level AUC Tracking**: Per-fold AUC tracking via `cross_val_score` for all three models with `*_auc_std` stability metric.
- **Threshold Sensitivity Sweep**: 50-point sweep of sensitivity, specificity, and PPV across thresholds (0.01–0.99) for RF.
- **Feature Stability**: CV cross-fold feature importance consistency scoring (0.0–1.0 scale).
- **QC Metrics**: Per-feature `n_missing`, `pct_missing`, and `is_zero_variance` computed in `evaluate_feature()`.
- **Feature Cards**: Auto-generated metadata cards from evaluator registry with tier, category, and derived feature type detection.
- **SHAP Tabbed Interface**: Unified SHAP tabs for RF and XGBoost with consistent layout.
- **Verdict Value Box**: AUC-threshold verdict (Strong ≥0.80, Moderate ≥0.70, Weak <0.70) in Executive Summary.
- **Label × Cancer Type Sunburst**: Interactive sunburst visualization replacing static bar chart.
- **Per-Sample Coverage Histogram**: Histogram of non-null feature percentage per sample.
- **Per-Chromosome Feature Chart**: Conditional chromosome-level feature bar chart.
- **Feature Importances Tab**: Top-20 RF Gini importance bar chart in Model Validation.
- **AUC Deltas**: RF–LR and XGB–RF AUC deltas surfaced in Performance Metrics.
- **Training Time**: Model training time displayed in Performance Metrics tab.
- **VAF Scatter**: Re-added tumor burden independence scatter (top feature vs max_vaf, LOWESS trendline).
- **great_tables Integration**: Column-grouped data explorer using `great_tables` with auto-detected feature family spanners.
- **Quarto Auto-Discovery**: `_find_quarto()` probes PATH then 7 well-known install locations (Positron, Homebrew, system, conda).
- **Methods Link**: Sidebar link to API documentation site.
- **Documentation**: New dashboard guide, DCA methodology doc, feature cards API reference, comprehensive CLI flag docs.
- **Tests**: 24 new tests (53 total) covering DCA, PR curves, fold AUC, threshold sweep, feature stability, QC metrics, training time, AUC deltas, and feature cards.

### Changed
- JSON schema expanded from 24 to 44 fields per feature set.
- Dashboard template: 1,555 lines, 52 balanced code blocks.
- Language discipline applied across docs and template (removed promotional/overclaiming language).
- `custom.scss`: bumped font size to 0.95rem, added QC warning class, added `@media print` rules.

### Fixed
- Silent `except: pass` in calibration code replaced with `log.warning()`.
- Division by `len(df)` without zero-guard in class balance text.
- Scoreboard NaN values: sensitivity, specificity, n_samples, n_positive now correctly extracted from `rf_classification_report` dict instead of non-existent top-level keys.
- QC tab Figure code dump: unsuppressed `fig.update_traces()` return displayed as raw `Figure({...})` text.
- Dashboard `debug: true` leaked Python output into rendered HTML; replaced with `warning: false`.
- QC row heights summed to 135%; rebalanced to 100% (10+40+25+25).
- Undefined `_to_float_array` in `wps_panel.py` and `wps_genomewide.py` replaced with correctly imported `parse_array`.
- SHAP waterfall rendering stabilized for edge cases with zero feature contributions.
- Typo `fallsbacks` → `fallbacks` in `pyproject.toml`.
- `great_tables>=0.15.0` added to `pyproject.toml` dependencies.

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
