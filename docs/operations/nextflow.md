# Nextflow Integration

While `kreview` provides a robust, fully-featured CLI orchestrator, executing large-scale fragmentomics evaluation directly on local Posix systems (e.g. your laptop) can become a bottleneck when navigating tens of thousands of network parquet files.

For enterprise environments, `kreview` natively ships a standardized **nf-core DSL2 Nextflow pipeline wrapper**. This ensures `kreview` can securely attach to the execution tail of High-Performance Computing (HPC) workflows (like the MSK `krewlyzer` fragmentomics caller).

---

## Architecture Overview

All Nextflow pipeline logic resides within the `nextflow/` directory:

- `nextflow/main.nf` — Entrypoint
- `nextflow/nextflow.config` — Execution profiles, defaults
- `nextflow/workflows/kreview_eval.nf` — Pipeline DAG (monolithic or multistage)
- `nextflow/modules/local/kreview/` — Individual process modules:
    - `run.nf` — Monolithic mode (backward compatible)
    - `extract.nf` — Per-evaluator feature extraction
    - `select.nf` — Feature scoring + mRMR/hybrid-union selection
    - `eval_cpu.nf` — CPU model evaluation (LR, RF, XGB)
    - `eval_gpu.nf` — GPU model evaluation (TabPFN, TabICL)
    - `fuse.nf` — Super-matrix construction
    - `eval_multimodal.nf` — Cross-evaluator stacking
    - `report.nf` — HTML dashboard generation

The pipeline supports two modes controlled by `params.pipeline_mode`:

- **`monolithic`** (default) — Single-process `KREVIEW_RUN` for backward compatibility.
- **`multistage`** — Decomposed: Extract(×N) → Select → parallel(Fuse, Eval CPU, Eval GPU) → Eval Multimodal → Report.

For a detailed architecture overview with notebook-to-module mappings, see the [Pipeline Architecture](../developer/pipeline-architecture.md) developer guide.

The workflow transparently wraps the `kreview` Typer CLI, binding the computation natively to the `ghcr.io/msk-access/kreview:latest` container.

## Pipeline Execution

To trigger the `kreview` evaluation over a massive cohort using your standard Nextflow runner, use the `main.nf` script:

```bash
nextflow run /path/to/kreview/nextflow/main.nf \
  --cancer_samplesheet /data/cancer.csv \
  --healthy_xs1_samplesheet /data/healthy1.csv \
  --healthy_xs2_samplesheet /data/healthy2.csv \
  --cbioportal_dir /data/msk_solid_heme/ \
  --krewlyzer_dir /data/krewlyzer_parquets/ \
  -profile docker
```

!!! tip "Targeted Nextflow Execution"
    Just like the vanilla CLI, you can limit the Nextflow computation to specific features! You are allowed to pass the `--features` or `--tier` parameters dynamically through Nextflow:
    ```bash
    nextflow run nextflow/main.nf \
      ...
      --features "AtacOnTarget,FSCOnTarget"
    ```

---

## Profiling & Scaling (SLURM)

Because `kreview` accesses thousands of files aggressively using DuckDB, network filesystem socket limits (`Ulimit N`) behave entirely differently between a desktop Mac and a remote HPC SLURM cluster.

### 1. Local (Docker)
`nextflow run ... -profile docker` 

When operating locally, `nextflow.config` strictly maps `docker.runOptions = '-v /:/'` to guarantee absolute URI paths don't break the container's volume map. It safely hardcaps `--chunk-size` at `50` to defend local Posix max-file limits.

### 2. High-Performance Computing (SLURM)
`nextflow run ... -profile slurm`

If analyzing clinical trials against HPC hardware (like MSK's `cmobic_short` queues on `IRIS`), the pipeline invokes `Singularity` (via `autoMounts = true`) and overrides the fallback logic. 
The configuration aggressively sets `--chunk-size 500` to maximize network ingestion speeds on hardware that naturally supports `102400` open network sockets.

---

## Averting Path-Staging Collapse

If Nextflow were allowed to behave natively, it would attempt to symlink all `14,000` Krewlyzer `.parquet` target output files independently into the isolated `.work/` module directory. This mathematically guarantees a localized freeze or file-limit crash on practically all operating systems.

To fundamentally solve this problem: 

> The `kreview` Nextflow module (`run.nf`) completely bypasses standard `path` file orchestration for the target Krewlyzer output. It captures `--krewlyzer_dir` exactly as an absolute Native `val` String, sending it securely inside the Python container.

You can safely drop either an absolute directory path or the explicit path to a `manifest.txt` file directly into the `--krewlyzer_dir` mechanism!
