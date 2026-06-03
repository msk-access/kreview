# Running the Pipeline

The backbone of `kreview` is run through a highly modular `typer` CLI. It connects all independent elements of the pipeline dynamically.

---

## Available Commands

`kreview` provides a modular CLI where each pipeline stage can run independently or together via `kreview run`:

| Command | Purpose | Pipeline Order |
|---------|---------|---------------|
| `kreview label` | Generate ctDNA labels only | 1 |
| `kreview extract` | Label + extract feature matrices per evaluator | 2 |
| `kreview select` | Score features (AUC/MI) + mRMR or hybrid union selection | 3 |
| `kreview eval cpu` | CPU model evaluation (LR, RF, XGB) | 4a (parallel) |
| `kreview eval gpu` | GPU model evaluation (TabPFN, TabICL) | 4b (parallel) |
| `kreview fuse` | Fuse per-evaluator matrices → super-matrix | 4c (parallel) |
| `kreview eval multimodal` | Cross-evaluator stacking + ablation | 5 (needs 4a+4b+4c) |
| `kreview report` | Re-generate HTML dashboards | 6 |
| `kreview run` | Full pipeline: all of the above in sequence | — |
| `kreview features-list` | List registered evaluators | — |

!!! note "Steps 4a, 4b, and 4c are independent"
    After feature selection, `eval cpu`, `eval gpu`, and `fuse` can run in **parallel**. They all converge at `eval multimodal`, which needs the OOF predictions from eval + the super-matrix from fuse.

---

## Basic Execution

!!! warning "Disable Python Buffering"
    When running over terminal orchestrators (like `nohup`, standard piping, or SLURM), it is critical to run Python with `PYTHONUNBUFFERED=1` so that the `structlog` progress output streams in real-time.

=== "Standard Run (All Features)"

    ```bash
    PYTHONUNBUFFERED=1 kreview run \
      --cancer-samplesheet "/path/to/samplesheet.csv" \
      --healthy-xs1-samplesheet "/path/to/healthy1.csv" \
      --healthy-xs2-samplesheet "/path/to/healthy2.csv" \
      --cbioportal-dir "/path/to/msk_solid_heme_cbioportal" \
      --krewlyzer-dir "/path/to/feature_parquets" \
      --output output/ \
      --strategy mrmr \
      --ch-hotspot-maf /path/to/ch_hotspots.maf \
      --export-duckdb
    ```
    *Note: `--export-duckdb` automatically writes a persistent SQL-queryable `kreview_lake.duckdb` after processing.*

=== "Using a Manifest File"

    If your Krewlyzer results span multiple directories, create a `manifest.txt` listing one directory per line, then pass it down:

    ```bash
    kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir manifest.txt \
      --output output/
    ```

=== "Machine Learning Tuning"

    Control statistical parameters and cross-validation:

    ```bash
    kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir ... \
      --cv-folds 5 \
      --impute-strategy median
    ```
    *Options for imputation: `median`, `mean`, `zero`. Folds must be `3-20`.*

=== "SHAP & Visualization"

    Control SHAP explainability and display:

    ```bash
    kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir ... \
      --shap-samples 5000 \
      --shap-features 10 \
      --top-percentile 20
    ```

    | Flag | Default | Description |
    |------|---------|-------------|
    | `--shap-samples` | 500 | Max samples for SHAP computation (higher = slower but more stable) |
    | `--shap-features` | 10 | Number of features to show in SHAP beeswarm/waterfall |
    | `--top-percentile` | 10.0 | Top X% of features per metric (AUC, MI). Union of both sets feeds models. |

=== "Accessibility & Theme"

    ```bash
    kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir ... \
      --cvd-safe
    ```

    The `--cvd-safe` flag switches all dashboard visualizations to the Okabe-Ito color palette, which is accessible for red-green colorblindness. By default, kreview uses a curated neon palette optimized for dark backgrounds.

=== "Feature Selection"

    ```bash
    kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir ... \
      --top-percentile 20
    ```

    Feature selection uses **mRMR (Minimum Redundancy Maximum Relevance)** by default. It selects features that are highly correlated with the target but mutually dissimilar, preventing multi-collinearity. A legacy **Hybrid Union** strategy (top X% by AUC ∪ top X% by MI) is also available.

    | Flag | Default | Description |
    |------|---------|-------------|
    | `--strategy` | mrmr | Feature selection strategy: `mrmr` or `hybrid_union` |
    | `--top-percentile` | 10.0 | Percentile cutoff. For mRMR, this controls `K` features to select. |
    | `--compute-univariate-auc` | True | Compute per-feature LR AUC (required for hybrid selection). |
    | `--no-compute-univariate-auc` | — | Opt-out: degrades selection to MI-only with a warning. |

    !!! note "Deprecated: `--top-n`"
        The `--top-n` flag is deprecated since v0.0.9 and will be removed in v0.1.0. Use `--top-percentile` instead.

=== "Safe Load Mode (I/O Constraints)"

    If you see `PermissionError` during large cohort loading, reduce the parquet chunk-size:

    ```bash
    kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir ... \
      --chunk-size 100
    ```

---

## Targeted Execution

=== "Isolating Features"

    Use the `--features` flag with a comma-separated list to run only specific evaluators:

    ```bash
    kreview run \
      ...
      --features "BreakPointMotifOnTarget,EndMotifOnTarget"
    ```

=== "Running by Tier"

    Run only Tier 1 (fragment size) or Tier 2 (nucleosome/motif) features:

    ```bash
    kreview run \
      ...
      --tier 1
    ```

=== "Skipping Reports"

    If you are running in headless CI environments and don't need HTML dashboards:

    ```bash
    kreview run \
      ...
      --skip-report
    ```
    *Note: When `--skip-report` is omitted, `kreview` generates both interactive Plotly `output/reports/*.html` dashboards and a `static_plots/` subdirectory containing 2x-scaled `.png` versions of every chart.*

=== "Resume Mode"

    Skip evaluators that already have model results (useful for incremental HPC re-runs):

    ```bash
    kreview run \
      ...
      --resume
    ```
    *This checks for existing `*_model_results.json` files and skips extractors that have already completed.*

---

## Modular Pipeline (HPC / Nextflow)

The same pipeline can be run step-by-step for HPC parallelization or debugging:

```bash
# Step 0: Label (run once, share across all extractors)
kreview label \
    --cancer-samplesheet samplesheet.csv \
    --healthy-xs1-samplesheet healthy1.csv \
    --healthy-xs2-samplesheet healthy2.csv \
    --cbioportal-dir /path/to/cbioportal/ \
    --ch-hotspot-maf /path/to/ch_hotspots.maf \
    --output labels.parquet

# Step 1: Extract matrices (parallelizable per evaluator)
# Use --labels to skip re-labeling in each extract job
kreview extract --cancer-samplesheet samplesheet.csv \
    --healthy-xs1-samplesheet healthy1.csv \
    --healthy-xs2-samplesheet healthy2.csv \
    --cbioportal-dir /path/to/cbioportal/ \
    --krewlyzer-dir /path/to/features/ \
    --labels labels.parquet \
    --output output/

# Step 2: Feature selection (mRMR is default)
kreview select --matrices-dir output/ --top-percentile 50 --strategy mrmr --output selected/
# Or overwrite in-place:
# kreview select --matrices-dir output/ --top-percentile 50 --overwrite

# Steps 3a/3b/3c can run in PARALLEL
# 3a: CPU model evaluation
kreview eval cpu --matrices-dir selected/ --output results/
# 3b: GPU model evaluation (optional, uses eval_stats for feature capping)
kreview eval gpu --matrices-dir selected/ --output results/ \
    --eval-stats-dir selected/ --max-gpu-features 150
# 3c: Fuse selected matrices → super-matrix
kreview fuse --output-dir selected/

# Step 4: Multimodal evaluation (needs OOF probs + super_matrix)
kreview eval multimodal \
    --results-dir results/ \
    --super-matrix selected/super_matrix.parquet \
    --multimodal-selection boruta_shap \
    --output results/

# Step 5: Report
kreview report --results-dir results/
```

!!! tip "Inspecting Parquet Outputs"
    Use [`parq-cli`](https://github.com/Tendo33/parq-cli) to quickly inspect parquet files directly from the terminal:
    ```bash
    parq schema output/AtacOnTarget_matrix.parquet  # Column names and types
    parq meta   output/AtacOnTarget_matrix.parquet  # Row count, compression, metadata
    ```

!!! tip "kreview select options"
    | Flag | Default | Description |
    |------|---------|-------------|
    | `--matrices-dir` | required | Directory with `*_matrix.parquet` from extract |
    | `--top-percentile` | 50 | Top N% per metric for selection |
    | `--strategy` | mrmr | Feature selection strategy: `mrmr` or `hybrid_union` |
    | `--cv-folds` | 5 | Folds for univariate AUC scoring |
    | `--impute-strategy` | median | Imputation for missing values |
    | `--output` | output/ | Output directory for selected matrices |
    | `--overwrite` | false | Overwrite originals instead of separate output |

---

## Labels Only

If you only need to generate the ctDNA truth labels without running feature evaluation:

```bash
kreview label \
  --cancer-samplesheet "/path/to/samplesheet.csv" \
  --healthy-xs1-samplesheet "/path/to/healthy1.csv" \
  --healthy-xs2-samplesheet "/path/to/healthy2.csv" \
  --cbioportal-dir "/path/to/cBioPortal/" \
  --output labels.parquet
```

This produces a single Parquet file with sample IDs, clinical metadata, the assigned 5-tier labels, and a `split` column (`train`/`test`/`exclude`) for holdout validation.

---

## Data Lake Integration

Every time `kreview run` executes, feature matrices are loaded into memory, evaluated, and then destroyed. If you want a **persistent output** for downstream analysis:

```bash
kreview run \
  ...
  --export-duckdb
```

This creates or merges an immutable `kreview_lake.duckdb` file in your `output/` directory. Downstream researchers can then query it directly with DuckDB or Pandas without re-running the pipeline.

---

## Re-generating Reports

If you have existing evaluation results (`stats.json`, `*_matrix.parquet`) and want to regenerate the HTML dashboard:

```bash
kreview report \
  --results-dir output/BreakPointMotifOnTarget/ \
  --output-dir output/reports/
```

For a guide to interpreting the generated dashboard, see the [Dashboard Interpretation Guide](../machine-learning/dashboard-guide.md).
