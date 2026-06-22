# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.25] - 2026-06-22

### Fixed
- **Container Dependencies**: Moved `papermill>=2.5.0` from `[jupyter]` optional extra to core dependencies. Quarto's `--execute-params` (`-P`) flag requires papermill at runtime, and the CPU Docker container did not include it — causing all 26 evaluator reports to fail on HPC with `"The papermill package is required for processing --execute-params"`.
- **BorutaShapPlus Container Availability**: Ensured `BorutaShapPlus>=0.1.3` (already in core deps since v0.0.24) is present in rebuilt containers. The v0.0.24 container was built from a stale state, causing multimodal prep to fail with `"No module named 'BorutaShapPlus'"` and cascading failure of the entire multimodal pipeline chain.

## [0.0.24] - 2026-06-18

### Added
- **ARFS Feature Selection**: Added Leshy (Boruta+LightGBM/SHAP) and GrootCV (cross-validated SHAP importance) as `--multimodal-selection` options. Install via `pip install kreview[arfs]`.
- **Strategy Validation**: `_select_multimodal_features()` now raises `ValueError` on unknown strategy names instead of silently falling through to MI ranking. Typos like `--multimodal-selection borta_shap` are caught immediately.
- **MI-Reduction Helper**: Extracted `_mi_reduce_confirmed()` to deduplicate the >500-feature MI reduction logic across Boruta-SHAP, Leshy, and GrootCV strategies.
- **Tests**: Added `test_invalid_strategy_raises`, `test_valid_strategies_constant`, `test_leshy_passes_through`, and `test_grootcv_passes_through` to `test_selection.py`.

### Changed
- **BorutaShap → BorutaShapPlus**: Migrated from `BorutaShap>=1.0.17` to `BorutaShapPlus>=0.1.3` with scipy `binom_test` and NumPy `np.NaN` compatibility shims.

### Fixed
- **Quarto EROFS on Read-Only Singularity**: Quarto 1.9+ creates a `.quarto/` project directory next to the QMD source. Inside read-only Singularity containers, this failed with `EROFS (error 30)`. Templates are now staged to a writable `.render_{feat_name}/` directory before `quarto render`.
- **Report publishDir Double-Nesting**: Fixed `publishDir "${params.outdir}/reports"` → `"${params.outdir}"` in `report.nf` and `report_multimodal.nf` to prevent `results/reports/reports/` nesting.
- **GrootCV Constructor**: Fixed invalid parameters (`estimator`, `n_iterations`, `cv`) → correct ARFS API (`objective="binary"`, `n_folds=5`, `n_iter=50`, `silent=True`).
- **Leshy Constructor**: Fixed `n_iter` (not a valid param) → `max_iter=50`; added `n_estimators=1000`, `verbose=0`.
- **Test Import**: Updated `test_selection.py` skip guard from `import BorutaShap` to `import BorutaShapPlus`.

## [0.0.23] - 2026-06-16

### Fixed
- **Scoreboard Nextflow Quote-Escaping**: Replaced `python3 -c "..."` with bash heredoc (`python3 << 'EOF'`) in `scoreboard.nf` to prevent Nextflow shell interpolation from stripping escaped quotes, which caused `NameError: name 'evaluator' is not defined` and `KREVIEW_SCOREBOARD` failing all retry attempts.
- **scipy.stats Version Attribute**: Fixed `AttributeError` in the `binom_test` compatibility shim by importing `scipy` (top-level) instead of accessing `__version__` on `scipy.stats` (which has no such attribute). This caused `KREVIEW_MULTIMODAL_PREP` to crash when `--multimodal-selection boruta_shap` was used (scipy ≥1.12).
- **Quarto HPC Cache Permissions**: Export `XDG_CACHE_HOME` and `XDG_DATA_HOME` to writable local paths in `report.nf` and `report_multimodal.nf`, preventing Quarto from failing on HPC compute nodes with read-only `~/.cache` directories.

## [0.0.22] - 2026-06-11

### Fixed
- **WPSGenome MAD Memory Optimization**: Replaced the nested Python loop that materialized ~446M rows in memory with a DuckDB-native window function query, reducing peak memory usage to under 100MB and runtime to ~7s.
- **GPU Ablation TypeError**: Fixed a bug where `_build_ablation_model_factories` called `GPUModelCVAdapter` directly with invalid `model_name` argument instead of using `_build_gpu_model` builder, causing GPU ablation to silently fail and default to `ALL`.

## [0.0.21] - 2026-06-10

### Performance
- **WPSGenome SQL pushdown**: Uses DuckDB native `list_avg()`, `list_max()`, `list_min()`
  to aggregate 1.9B rows inside DuckDB instead of materializing in pandas.
  Reduces peak memory from 96+ GB to ~17 GB.
- **DuckDB resource tuning**: Default threads 4→8, memory 4GB→32GB,
  exposed via `--duckdb-threads` / `--duckdb-memory` CLI options.
- **Nextflow KREVIEW_EXTRACT**: cpus 4→8, memory 32GB→64GB per attempt,
  maxRetries 7→3 (SQL pushdown eliminates the memory ladder).

### Added
- `configure_duckdb()` API for pre-connection resource configuration.
- `--duckdb-threads` and `--duckdb-memory` CLI options on `extract` and `run` commands.
- `sql_pivot_column` evaluator property for multi-row SQL result pivoting.
- Exact MAD hybrid computation via second lightweight DuckDB query.
- Nextflow params: `duckdb_threads`, `duckdb_memory`.

### Fixed
- **Nextflow resilience**: Added explicit `errorStrategy` + `maxRetries` to 14
  processes that relied on global defaults. One failed evaluator no longer
  terminates the entire pipeline — it is ignored after 3 retries.
- KREVIEW_FUSE uses `terminate` (not `ignore`) since downstream processes
  depend on the super-matrix.
- Added `ifEmpty` channel guards on EXTRACT→SELECT and GPU ablation `.combine()`
  to prevent pipeline deadlocks when upstream processes are ignored.
- Added missing `withName` config blocks for `KREVIEW_MULTIMODAL_SINGLE_CPU`,
  `KREVIEW_MULTIMODAL_SINGLE_GPU`, and `KREVIEW_MULTIMODAL_MERGE`.

### Changed
- `get_duckdb_conn()` defaults: 8 threads, 32GB memory (was 4 threads, 4GB).

## [0.0.20] - 2026-06-09

### Added
- **Feature Group Ablation**: `kreview eval ablate {cpu,gpu,merge}` CLI commands for nested CV feature group selection. Identifies suffix-based feature groups, evaluates all subsets via inner CV, and picks the optimal subset per model per fold using `sensitivity_at_100spec_healthy`.
- **Nested CV Pipeline**: Per-model per-fold feature subsets flow from ablation → merge → eval via `--best-subset`. Supports both CPU (LR/RF/XGB) and GPU (TabPFN/TabICL) models.
- **Nextflow Ablation Stages**: 3 new modules (`ablate_cpu_single.nf`, `ablate_gpu_single.nf`, `merge_ablation.nf`) wired into `kreview_eval.nf` behind `params.run_ablation` flag. All stages run in parallel per evaluator.
- **Scoreboard Columns**: `nested_cv` flag and `best_sens_100spec_healthy` (best sensitivity across ALL models) added to `build_scoreboard()`.
- **Bootstrap CIs**: `_compute_oof_metrics()` produces 95% bootstrap CIs for AUC, sensitivity@100%spec, and all clinical metrics.
- **GPU Subgroup Stats**: `gpu_models()` now reports `assay_stats` and `cancer_type_stats` for subgroup analysis.
- **Test Suite**: `tests/test_ablation.py` with 17 tests covering feature grouping, subset generation, OOF metrics, backward compatibility, and scoreboard.

### Changed
- `eval cpu` and `eval gpu` accept optional `--best-subset` for nested CV with per-fold feature subsets.
- `eval_cpu_single.nf` and `eval_gpu_single.nf` accept optional `best_subset` input channel (backward compatible via sentinel file).
- `nextflow.config`: new params `run_ablation` (default: false), `ablation_inner_folds` (default: 3).

## [0.0.19] - 2026-06-08

### Fixed
- **WPSGenome Extraction Failure**: Removed broken SQL pushdown (`extract_sql()`) that used `trim(col, '[]')` on native `list<float>` arrays, silently producing NULL results. Replaced with pure-Python `extract()` using `_to_array()` helper that handles numpy arrays, Python lists, and legacy string-encoded arrays. Added `_to_array()` as a public utility.
- **WPSGenome Last-Row-Wins Bug**: Rewrote `extract()` to aggregate per-region-type (TSS, CTCF) statistics across all regions instead of overwriting with the last row. Now computes mean, peak_valley, std, and MAD of per-region array means.
- **WPSPanel Last-Row-Wins Bug**: Rewrote `extract()` to aggregate per-region-type (TSS, CTCF) statistics across all panel regions (~59-85 rows per type) instead of overwriting with the last row. `local_depth` now averaged across panel regions instead of using last value.
- **GPUModelCVAdapter Serialization**: Added `__getstate__`/`__setstate__` to exclude unpicklable `model_factory` lambda from pickle. Deserialized adapters work for inference (`predict_proba`) but raise `TypeError` on `fit()` — preventing silent misuse.
- **Joblib Corrupt File Detection**: `_save_fitted_models()` now validates post-write file size (>100 bytes) and deletes truncated files. Error-level logging replaces silent `log.warning`. Partial files from failed `joblib.dump()` are cleaned up.
- **`parse_array()` Numpy Passthrough**: Now handles numpy arrays and Python lists as input (passthrough), not just string-encoded arrays. Previously returned `[]` for native parquet `list<float>` data, causing silent data loss.

### Changed
- **WPSBackground Cleanup**: Removed bare `try/except` for consistency with WPSGenome/WPSPanel. Errors now propagate to CLI handler. Added structured logging for empty/success cases with feature counts and chromosome counts. Metrics list moved to class constant `_metrics`.

### Removed
- **WPSGenome SQL Pushdown**: Removed `extract_sql()`, `sql_pivot_column`, and CLI pivot code. See v0.0.17 entry — the SQL path was fundamentally incompatible with native array storage.
- **WPSGenome FFT Features**: Dropped `spectral_max_power` and `spectral_dominant_freq`. Empirical analysis (r=0.91–1.00 with basic stats) proved FFT is redundant with mean/std/peak_valley. Nucleosome periodicity is captured by `WPSBackgroundEvaluator`.
- **WPSPanel `spectral_max_power`**: Removed — real-data analysis (4 patient samples) showed r=0.90–1.00 with `std` after per-region-type aggregation. `spectral_dominant_freq` retained (38.5% CV in `wps_tf` across samples — potentially informative for curated TSS/CTCF loci).


## [0.0.18] - 2026-06-05

### Added
- **Fine-tuned GPU Model Variants**: `tabpfn_ft` and `tabicl_ft` via `FinetunedTabPFNClassifier` and `FinetunedTabICLClassifier` with configurable `--finetune-epochs` (default: 50) and `--finetune-lr` (default: 1e-5). Total GPU model count: 4 (was 2).
- **`GPUModelCVAdapter`**: sklearn-compatible wrapper in `eval_engine.py` that resolves `AttributeError: 'FinetunedTabPFNClassifier' has no attribute 'classes_'` during `cross_val_predict`. Exposes `classes_` as a plain attribute set during `fit()`.
- **`kreview eval multimodal` nested subgroup**: 5 subcommands — `run` (monolithic backward-compat), `prep`, `single`, `ablation`, `merge`.
- **Decomposed multimodal Nextflow pipeline**: 4 new NF modules (`multimodal_prep.nf`, `multimodal_single.nf`, `multimodal_ablation.nf`, `multimodal_merge.nf`) enabling per-model parallel execution. Legacy `eval_multimodal.nf` kept for standalone testing via `kreview eval multimodal run`.
- **GPU foundation model expansion**: 4 GPU model variants (`tabpfn`, `tabpfn_ft`, `tabicl`, `tabicl_ft`) evaluated per-evaluator in parallel via `KREVIEW_EVAL_GPU_SINGLE`. Each process runs all requested GPU models and outputs a single `{evaluator}_gpu_model_results.json`.
- **Intentional 7-color palette**: Vanilla/FT shade families (`#00e5ff`/`#00b0ff` for TabPFN, `#76ff03`/`#64dd17` for TabICL) in report templates.
- **Stacking feature selection**: MI or Boruta-SHAP on stacking matrix via `--stacking-selection`.
- **Decomposed NF resource configs**: Per-process `withName` blocks for `KREVIEW_MULTIMODAL_PREP`, `KREVIEW_MULTIMODAL_SINGLE_GPU`, and `KREVIEW_MULTIMODAL_ABLATION`.

### Changed
- Default `--gpu-models` → `tabpfn,tabpfn_ft,tabicl,tabicl_ft` (4 models, was 2).
- `kreview eval multimodal` uses nested Typer sub-commands (was flat hyphenated commands).
- NF config: decomposed process resource configs replace monolithic `withName: 'KREVIEW_EVAL_MULTIMODAL'`.
- Report `_name_map` includes `TabPFN-FT` and `TabICL-FT` display names.
- `multimodal_cpu_only` NF param marked as legacy (decomposed pipeline routes CPU/GPU per-process).

### Removed
- `--no-finetune` CLI flag (use `--gpu-models tabpfn,tabicl` for zero-shot only).
- Dead `KREVIEW_EVAL_MULTIMODAL` import from `kreview_eval.nf`.

### Fixed
- TabPFN `AttributeError: 'FinetunedTabPFNClassifier' has no attribute 'classes_'` via `GPUModelCVAdapter` wrapper.
- Stale `multimodal-prep` (hyphen) references in CLI help strings → `multimodal prep` (space).
- Stale DAG comments in `eval_cpu_single.nf`, `eval_gpu_single.nf`, `report_multimodal.nf` referencing removed `KREVIEW_EVAL_MULTIMODAL`.

## [0.0.17] - 2026-06-04

### Added
- **GPU Model Pre-flight Validation**: `_validate_gpu_models()` in `cli_eval.py` verifies GPU model packages are installed and `TABPFN_TOKEN` is set before any work begins. Shared across `eval gpu`, `eval multimodal`, and monolithic `run` commands. Exits with code 1 and actionable instructions on failure.

### Fixed
- **OOF Sample IDs Alignment (P0)**: `oof_sample_ids` scoped to train-split only in CPU, GPU, and monolithic paths to match `oof_probs` length from `cross_val_predict`. Added `oof_sample_ids` and `oof_labels` to merge skip set preventing GPU from overwriting CPU alignment keys. This was the root cause of multimodal stacking failure ("25 had IDs but no probs").
- **BorutaShap scipy Compatibility (P1)**: Monkey-patched `scipy.stats.binom_test` with `binomtest().pvalue` wrapper for BorutaShap compatibility on scipy ≥1.12 (removed in 1.12). Eliminates `ImportError: cannot import name 'binom_test'` in multimodal raw feature selection.
- **Scoreboard Crash Handling (P2)**: Added try/except with traceback to `scoreboard.nf` inline Python. Moved file writes inside try block. Added `KREVIEW_SCOREBOARD` withName config block (retry 3×, then ignore). Added per-evaluator try/except in `build_scoreboard()` so a malformed evaluator result doesn't kill the scoreboard for all evaluators.
- **WPSGenome Timeout (P3)**: Implemented DuckDB SQL pushdown (`extract_sql()`) for `WPSGenomeEvaluator` — parses string-encoded arrays via `list_avg`/`list_max`/`list_min` in C++. Added `sql_pivot_column` for tall-to-wide pivot in CLI. Used `pivot_table(aggfunc='first')` for duplicate safety with null guard on pivot failure fallback. Added time/queue escalation in `nextflow.config` (retries 3+ → `cmobic_cpu` 8h). **Note**: This SQL pushdown was later found to be broken — krewlyzer stores arrays as native `FLOAT[]`, not string-encoded. Removed in [Unreleased].
- **GPU Silent Failure Logging (P4)**: Record per-model error keys (`{model}_error`) in GPU results dict. Detect all-models-failed state and set `results["error"]`. Added visible `⚠ WARNING` stdout output in both `cli_eval.py` and monolithic `cli.py`.
- **REPORT Blocked by SCOREBOARD (P5)**: Guarded REPORT channel with `.ifEmpty(file('NO_SCOREBOARD'))` so reports render even when scoreboard fails. Templates already check `scoreboard_path.exists()`.
- **REPORT_MULTIMODAL SLURM Rejection**: Added `withName: 'KREVIEW_REPORT_MULTIMODAL'` config block with explicit `queue = params.partition ?: 'cmobic_short'`. Previously fell through to `process_medium` label which lacked a queue directive, causing iris institutional config to inject the inaccessible `cpu` partition into sbatch.
- **Nextflow Channel Deadlocks**: Added `.ifEmpty([])` guards on JSON collect, joblib collect, and GPU collect channels to prevent pipeline deadlock when tasks fail with `errorStrategy = 'ignore'`.
- **Pivot Crash on Duplicate Rows**: Switched from `pivot()` to `pivot_table(aggfunc='first')` in CLI wide-pivot for WPSGenome tall-to-wide conversion, preventing `ValueError: cannot reshape` on duplicate region_type rows.
- **Null Guard on Pivot Failure**: Added null check on `feat_matrix` after pivot failure fallback, preventing `AttributeError: NoneType has no attribute 'columns'`.
- **Queue Directive Safety Net**: Added `queue = params.partition ?: 'cmobic_short'` to `process_medium` and `process_high` label defaults. Prevents any future process from failing SLURM submission due to missing partition.

### Changed
- **Version Bump**: `__init__.py`, `settings.ini`, `nextflow.config` → `0.0.17`.
- **Version-agnostic `run_hpc.sh`**: Auto-detects version from `nextflow.config` at runtime. Dynamic `GPU_MODELS` based on `TABPFN_TOKEN` availability. No manual edits needed between releases.

## [0.0.16] - 2026-06-03

### Added
- **80/20 Stratified Holdout Validation**: `_assign_train_test_split()` in `CtDNALabeler.label_all()` assigns a `split` column (`train`/`test`/`exclude`) to `labels.parquet`. Split is stratified by 4-tier label with `random_state=42` for reproducibility. `evaluate_holdout()` in `eval_engine.py` provides unbiased AUC estimates on the held-out 20%.
- **Sensitivity at Fixed Specificity**: `evaluate_model()` now computes sensitivity at 100%, 99%, and 95% specificity, plus a healthy-normal-only variant using `sample_labels`. 12 new JSON fields per model.
- **Intelligent GPU Feature Capping**: `gpu_models()` accepts `--max-gpu-features` (default: 150) and caps features using score-based priority (MI > AUC > variance). Returns `gpu_feature_cap_indices` for holdout dimension consistency.
- **CH-Only → Undetermined Label**: Samples with `n_non_ch_variants == 0` and no SV/CNA/IMPACT match are now labeled `Undetermined` (was: `Possible ctDNA−`). `Undetermined` is excluded from binary classification via `build_binary_target()`.
- **WPSGenome Streaming**: `extract_columns` and `max_chunk_rows` class attributes on `FeatureEvaluator` enable DuckDB column projection and chunked reads. WPSGenome sets `max_chunk_rows = 5_000_000` and projects to 4 columns, reducing peak memory ~80%.
- **Scoreboard Enhancements**: `build_scoreboard()` surfaces `sens_at_100spec`, `holdout_auc`, `holdout_sens_100spec`, `holdout_n_train/n_test`, and `auc_drop` (CV overfit diagnostic).
- **`LABEL_UNDETERMINED` Constant**: `CtDNALabeler.LABEL_UNDETERMINED = "Undetermined"` added alongside existing 5-tier constants.
- **Report Value Boxes**: Both `report_template.qmd` and `report_multimodal_template.qmd` now display "Sens @ 100% Spec" (with detection count) and "Holdout AUC" (with dynamic color: green/yellow/red by AUC drop severity) in the Executive Summary.
- **Report Clinical Metrics**: Model summary tables auto-discover and display `Sens@100%Spec`, `Sens@95%Spec`, and `Holdout AUC` per model.
- **Report Scoreboard Expansion**: Scoreboard display expanded from 7 to 13 columns (`best_model`, `holdout_auc`, `auc_drop`, `sens_at_100spec`, `sens_at_95spec`, `holdout_n_train`, `holdout_n_test`).

### Changed
- **Feature Selection Train-Only**: `score_features()` and `select_features()` (mRMR + hybrid paths) now filter to `split == "train"` before scoring, preventing test set leakage into feature rankings.
- **`LABEL_META_COLS`**: Added `split` to the 22-entry meta column set in `core.py` to prevent it from leaking into feature matrices.
- **Nextflow GPU Module**: `eval_gpu_single.nf` now stages `eval_stats` parquet and passes `--eval-stats-dir` + `--max-gpu-features` to the CLI.
- **Nextflow Workflow**: `kreview_eval.nf` wires `SELECT.out.eval_stats` → `EVAL_GPU_SINGLE`.
- **Version Bump**: `__init__.py`, `settings.ini`, `nextflow.config` → `0.0.16`.
- **Report `meta_cols` Dynamic Import**: Both templates now import `LABEL_META_COLS` from `kreview.core` instead of maintaining a stale hardcoded copy. Prevents label metadata columns from leaking into feature sets.
- **Report Glossary**: Added `Undetermined` label definition and train/test split documentation to both template glossary sidebars.
- **`MODEL_LABELS` / `POSITIVE_LABELS` Public API**: Promoted from private `_MODEL_LABELS` / `_POSITIVE_LABELS` in `selection.py` to public exports. Backward-compat aliases maintained.

### Fixed
- **GPU Holdout Dimension Mismatch**: `cli.py` and `cli_eval.py` now apply `gpu_feature_cap_indices` to `X_test` before calling `evaluate_holdout()`, matching the capped training feature space.
- **Data Leakage in mRMR/Hybrid Selection**: Both `select_features()` code paths now restrict MI scoring to train-only rows.
- **Unused Import**: Removed `pandas` import from `report.py` (F401).
- **Boolean Comparisons**: Replaced `== False` with `~` operator in `labels.py` (E712).
- **Ambiguous Variable**: Renamed `l` → `lbl` in list comprehensions in `eval_engine.py` (E741).
- **Nested If Statements**: Merged nested `if` blocks in `eval_engine.py` and `registry.py` (SIM102).
- **Ternary Simplifications**: Converted if/else blocks to ternary in `eval_engine.py` (SIM108).
- **Test Lint**: Removed 5 unused imports from test files and fixed 7 E712/SIM108 in test assertions.

## [0.0.15] - 2026-06-01

### Added
- **CPU+GPU JSON Merge Helpers**: `load_model_results(directory, evaluator_name)` and `load_all_model_results(directory)` in `eval_engine.py` transparently discover and merge `*_model_results.json` (CPU) and `*_gpu_model_results.json` (GPU) files. GPU model keys (AUC, OOF probs, SHAP) are merged into the CPU dict. Used by report templates, scoreboard, and multimodal engine.
- **KREVIEW_SCOREBOARD**: New Nextflow process (`scoreboard.nf`) generates `scoreboard_combined__all.parquet` after all CPU/GPU eval jobs complete. Uses `build_scoreboard()` which now calls `load_all_model_results()` for unified GPU+CPU scoring.
- **GPU Exit Code**: `kreview eval gpu` now exits with code 1 if NO models produced valid AUC results (was silent success). Prevents Nextflow from treating empty GPU results as success.
- **Unit Tests**: 11 new tests in `test_merge_helpers.py` covering CPU-only, GPU-only, CPU+GPU merge, malformed JSON, and directory scan scenarios.

### Changed
- **GPU JSON Output Naming**: GPU eval module now produces `*_gpu_model_results.json` (was `*_model_results.json`), preventing filename collision when CPU and GPU outputs are collected into the same Nextflow channel.
- **Report Input Signature**: `KREVIEW_REPORT` now accepts 6 inputs (matrices, model_results, eval_stats, selection_qc, joblib_files, scoreboard) for complete dashboard rendering.
- **Workflow Wiring**: `kreview_eval.nf` creates unified `ch_all_jsons` and `ch_all_joblib` channels that mix CPU+GPU outputs, feeds them to SCOREBOARD → REPORT.
- **Scoreboard Loading**: `build_scoreboard()` now uses `load_all_model_results()` instead of manual glob+load loop.
- **Multimodal Baselines Loading**: `_load_per_evaluator_baselines()` now uses `load_all_model_results()` instead of manual glob+load loop.
- **FSD Density Calculation**: Added `select_dtypes(include="number")` filter before density computation in `fsd.py` and `fsd_genomewide.py` to prevent TypeError on non-numeric metadata columns.
- **Multimodal NF Module**: Removed unnecessary staging loop — `--results-dir .` uses Nextflow work dir symlinks directly.
- **Dockerfile Optimization**: Selective builder `COPY` (only `pyproject.toml`, `kreview/`, `LICENSE`), single `pip install "${WHL}[gpu]"` pass to ensure local wheel resolution, dropped `python3.12-dev` and `wget` from GPU runtime, merged OCI labels into single `LABEL` instruction.
- **CI Parallelism**: `test.yml` split into parallel `test` (Python) and `docker` (matrix `[cpu, gpu]`) jobs with `fail-fast: false`. GPU build gets `jlumbroso/free-disk-space` cleanup (~20-30 GB freed).
- **`.dockerignore`**: Expanded to exclude `docs/`, `nextflow/`, `scripts/`, `tests/`, `.github/`, `.agents/` — reduces build context transfer.

### Fixed
- **OOF Label Key Search**: `"oof_labels".endswith("_oof_labels")` is `False` — fixed to check both exact match and suffix match. Applied to both `report_template.qmd` and `report_multimodal_template.qmd`.
- **FSD TypeError**: Non-numeric columns (e.g., `sample_id`, `filename`) caused `TypeError: ufunc 'divide' not supported` in FSD density calculation. Now filtered to numeric columns only.
- **Multimodal Validation Logging**: Now shows CPU vs GPU JSON counts separately for better debugging.
- **Docker GPU Build CI Failure**: GPU image build exceeded runner disk space (~14 GB free). Fixed by adding `jlumbroso/free-disk-space` action and optimizing Dockerfile layers.

### Removed
- **`tabpfn-extensions[interpretability]`** from `[gpu]` extras — unused since v0.0.13 (SHAP computation replaced by `shapiq`). Eliminates `transformers`, `wandb`, `huggingface-hub`, `tokenizers` transitive dependencies (~500 MB).
- **Deprecated HPC scripts**: `run_hpc_0.8.3.sh`, `run_hpc_v0.0.10.sh`, `run_hpc_v0.0.11.sh`, `runner.sh`, `utils/symlinker.py` — replaced by unified `scripts/run_hpc.sh`.

### Breaking Changes
- GPU JSON output renamed: `{eval}_model_results.json` → `{eval}_gpu_model_results.json`
- `KREVIEW_REPORT` input signature expanded from 2 to 6 inputs

## [0.0.14] - 2026-05-25

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
