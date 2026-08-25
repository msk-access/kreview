# Running the Pipeline

The backbone of `kreview` is run through a highly modular `typer` CLI. It connects all independent elements of the pipeline dynamically.

---

## Available Commands

`kreview` provides a modular CLI: each pipeline stage is its own command. The stages are
orchestrated by the **Nextflow multistage DAG**, which is the supported way to run the full
pipeline; the individual commands are for debugging or re-running a single step.

| Command | Purpose | Pipeline Order |
|---------|---------|---------------|
| `kreview label` | Generate ctDNA labels only | 1 |
| `kreview extract` | Label + extract feature matrices per evaluator | 2 |
| `kreview select` | Score features (AUC/MI) + mRMR or hybrid union selection | 3 |
| `kreview eval ablate cpu` | Nested CV feature group ablation (CPU models) | 3a (optional) |
| `kreview eval ablate gpu` | Nested CV feature group ablation (GPU models) | 3b (optional) |
| `kreview eval ablate merge` | Merge CPU + GPU ablation → `best_subset.json` | 3c (optional) |
| `kreview eval cpu` | CPU model evaluation (LR, RF, XGB) | 4a (parallel) |
| `kreview eval gpu` | GPU model evaluation (TabPFN, TabPFN-FT, TabICL, TabICL-FT) | 4b (parallel) |
| `kreview fuse` | Fuse per-evaluator matrices → super-matrix | 4c (parallel) |
| `kreview eval multimodal run` | Cross-evaluator stacking + ablation (monolithic) | 5 (needs 4a+4b+4c) |
| `kreview eval multimodal prep` | Build stacking matrix + feature selection | 5a |
| `kreview eval multimodal single` | Train single stacking model (parallelizable) | 5b |
| `kreview eval multimodal ablation` | Feature ablation analysis | 5c |
| `kreview eval multimodal merge` | Aggregate stacking + ablation results | 5d |
| `kreview report` | Render the single-page evaluation report | 6 |
| `kreview features-list` | List registered evaluators | — |

!!! note "Steps 4a, 4b, and 4c are independent"
    After feature selection (and optional ablation), `eval cpu`, `eval gpu`, and `fuse` can run in **parallel**. They all converge at `eval multimodal`, which needs the OOF predictions from eval + the super-matrix from fuse.

!!! info "Decomposed Multimodal (v0.0.18+)"
    `kreview eval multimodal run` executes the full multimodal pipeline as a single command. For HPC/Nextflow parallelization, use the decomposed subcommands: `prep` → `single` (×M models) → `ablation` → `merge`.

!!! tip "Nested CV Feature Group Ablation (v0.0.20+)"
    When `--run-ablation` is enabled, steps 3a–3c run between `select` and `eval`. The ablation uses inner cross-validation to identify the optimal feature group subset per model, producing a `best_subset.json` that is then consumed by `eval cpu --best-subset` and `eval gpu --best-subset`. This eliminates non-informative feature groups before final evaluation.

---

## Running the Pipeline

The full pipeline is one Nextflow invocation. Stage flags are exposed as Nextflow params
(underscored rather than hyphenated):

```bash
nextflow run nextflow/main.nf \
  --cancer_samplesheet /path/to/cancer.csv \
  --healthy_xs1_samplesheet /path/to/xs1.csv \
  --healthy_xs2_samplesheet /path/to/xs2.csv \
  --cbioportal_dir /path/to/msk_solid_heme/ \
  --krewlyzer_dir /path/to/results/ \
  --outdir output/ \
  -profile docker            # or iris / slurm on HPC
```

Common options (see `nextflow/nextflow.config` for the full list):

| Goal | Param |
|------|-------|
| Restrict to specific evaluators | `--features "FSCOnTarget,AtacOnTarget"` |
| Restrict by tier | `--tier 1` |
| Feature selection | `--strategy mrmr`, `--top_percentile 10` |
| Nested-CV ablation | `--run_ablation true` |
| GPU models | `--run_gpu_eval true --gpu_models "tabpfn,tabicl"` |
| Multimodal stacking | `--run_multimodal_eval true --multimodal_selection grootcv` |
| SHAP / dashboards | `--shap_samples 500`, `--shap_features 10`, `--cvd_safe true` |
| I/O-constrained hosts | `--chunk_size 100` |
| Skip the report | `--skip_report true` |

Nextflow's own `-resume` re-uses cached stage outputs, so a failed run continues from the
last successful stage rather than restarting.

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

# Step 3 (optional): Feature group ablation — nested CV subset selection
# 3a: CPU ablation (inner CV on LR, RF, XGB — parallelizable per evaluator)
kreview eval ablate cpu --matrices-dir selected/ --output ablation/
# 3b: GPU ablation (inner CV on TabPFN, TabICL — parallelizable per evaluator)
kreview eval ablate gpu --matrices-dir selected/ --output ablation/ \
    --eval-stats-dir selected/ --gpu-models "tabpfn,tabicl"
# 3c: Merge CPU + GPU ablation → best_subset.json
kreview eval ablate merge --cpu-json ablation/*_ablation_cpu_results.json \
    --gpu-json ablation/*_ablation_gpu_results.json --output ablation/

# Steps 4a/4b/4c can run in PARALLEL
# 4a: CPU model evaluation (uses --best-subset if ablation ran)
kreview eval cpu --matrices-dir selected/ --output results/ \
    --best-subset ablation/best_subset.json
# 4b: GPU model evaluation (uses --best-subset if ablation ran)
kreview eval gpu --matrices-dir selected/ --output results/ \
    --eval-stats-dir selected/ --max-gpu-features 150 \
    --gpu-models "tabpfn,tabpfn_ft,tabicl,tabicl_ft" \
    --best-subset ablation/best_subset.json
# 4c: Fuse selected matrices → super-matrix
kreview fuse --output-dir selected/

# Step 5: Multimodal evaluation (single-shot: prep -> single -> ablation -> merge in one process)
kreview eval multimodal run \
    --results-dir results/ \
    --super-matrix selected/super_matrix.parquet \
    --multimodal-selection grootcv \
    --output results/

# OR: Decomposed multimodal (HPC-optimized — parallelizable per-model)
kreview eval multimodal prep \
    --results-dir results/ \
    --super-matrix selected/super_matrix.parquet \
    --output results/multimodal/

# Run per-model stacking in parallel (CPU models)
kreview eval multimodal single \
    --stacking-matrix results/multimodal/stacking_matrix.parquet \
    --model rf --output results/multimodal/
kreview eval multimodal single \
    --stacking-matrix results/multimodal/stacking_matrix.parquet \
    --model xgb --output results/multimodal/

# GPU stacking models (optional)
kreview eval multimodal single \
    --stacking-matrix results/multimodal/stacking_matrix.parquet \
    --model tabpfn_ft --device cuda --output results/multimodal/

kreview eval multimodal ablation \
    --stacking-matrix results/multimodal/stacking_matrix.parquet \
    --stacking-results-dir results/multimodal/ \
    --output results/multimodal/

kreview eval multimodal merge \
    --stacking-results-dir results/multimodal/ \
    --prep-metadata results/multimodal/prep_metadata.json \
    --output results/multimodal/

# Step 6: Report — one self-contained HTML from the output dir
kreview report --outdir results/ --out-dir results/reports
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

This produces a single Parquet file with sample IDs, clinical metadata, the assigned 6-tier labels, and a `split` column (`train`/`test`/`exclude`) for holdout validation.

---

## Querying the Feature Matrices

Feature matrices are written as parquet under `output/`, so downstream analysis can query them
directly with DuckDB or pandas without re-running the pipeline:

```python
import duckdb
duckdb.sql("SELECT * FROM 'output/*_matrix.parquet' LIMIT 10").df()
```

!!! note
    The `--export-duckdb` flag (which packed the matrices into a single `kreview_lake.duckdb`)
    was removed in v0.0.29 along with `kreview run`. It was only ever reachable from the
    monolithic path, never from the Nextflow DAG. Query the parquet files directly instead.


---

## Re-generating Reports

If you have existing evaluation results (`stats.json`, `*_matrix.parquet`) and want to regenerate the HTML dashboard:

```bash
kreview report \
  --results-dir output/BreakPointMotifOnTarget/ \
  --output-dir output/reports/
```

For a guide to interpreting the generated dashboard, see the [Dashboard Interpretation Guide](../machine-learning/dashboard-guide.md).
