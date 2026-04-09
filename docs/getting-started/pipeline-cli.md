# Running the Pipeline

The backbone of `kreview` is run through a highly modular `typer` CLI. It connects all independent elements of the pipeline dynamically.

---

## Available Commands

`kreview` exposes four subcommands:

| Command | Purpose |
|---------|---------|
| `kreview run` | Full pipeline: label → extract → evaluate → report |
| `kreview label` | Generate ctDNA labels only (no feature evaluation) |
| `kreview features-list` | List all registered feature evaluators |
| `kreview report` | Re-generate HTML dashboard from existing results |

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
      --workers 4
    ```

=== "Using a Manifest File"

    If your Krewlyzer results span multiple directories, create a `manifest.txt` listing one directory per line, then pass it directly:

    ```bash
    kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir manifest.txt \
      --output output/
    ```

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

This produces a single Parquet file with sample IDs, clinical metadata, and the assigned 5-tier labels.

---

## Data Lake Integration

Every time `kreview run` executes, feature matrices are loaded into memory, evaluated, and then destroyed. If you want a **persistent output** for downstream analysis:

```bash
kreview run \
  ...
  --export-duckdb
```

This creates or merges an immutable `kreview_lake.duckdb` file in your `output/` directory. Downstream researchers can then query it directly with DuckDB or Pandas without re-running the pipeline!

---

## Re-generating Reports

If you have existing evaluation results (`stats.json`, `*_matrix.parquet`) and want to regenerate the HTML dashboard:

```bash
kreview report \
  --results-dir output/BreakPointMotifOnTarget/ \
  --output-dir output/reports/
```
