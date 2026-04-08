# Running the Pipeline

The backbone of `kreview` is run through a highly modular `typer` CLI. It connects all independent elements of the pipeline dynamically.

---

## Basic Execution

To launch a standard execution across all available features, define all your parameters directly from the terminal. 

!!! warning "Disable Python Buffering"
    When running over terminal orchestrators (like `nohup`, standard piping, or `slurm`), it is critical to run Python with `PYTHONUNBUFFERED=1` so that the `structlog` progress bars output asynchronously instead of stalling and hiding in memory!

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

=== "Safe Load Mode (I/O Constraints)"

    If you see **PermissionError Code 5** over your network mounts, dynamically drop the parquet chunk-size down to 100 handles per burst:

    ```bash
    PYTHONUNBUFFERED=1 kreview run \
      --cancer-samplesheet ... \
      --krewlyzer-dir ... \
      --chunk-size 100
    ```

---

## Targeted Execution

If you are just developing a new feature—or just want to target an existing one without having DuckDB load 22 multi-gigabyte queries—you can easily specify exact features to run!

=== "Isolating Features"

    Use the `--features` flag (which can be repeated!) to isolate exactly what you want the ML models to evaluate.

    ```bash
    kreview run \
      ...
      --features BreakPointMotif \
      --features EndMotif
    ```

=== "Skipping Reports"

    If you are running in headless CI environments and don't want Quarto HTML Plotly dashboards spitting out, you can run in silent ML mode:

    ```bash
    kreview run \
      ...
      --skip-report
    ```

---

## Data Lakes integration

Every time `kreview run` is successfully executed, the features are queried in DuckDB, extracted through our matrix reducers, evaluated through Sklearn ML models, and eventually destroyed in memory.

However, if you want a **persistent output** of the analytical matricies—so that downstream researchers can bypass the `krewlyzer` SFTP drive entirely and just run Pandas against the raw features—just add `--export-duckdb`!

```bash
kreview run \
  ...
  --features FSC_gene \
  --export-duckdb
```

This will automatically create or merge an immutable `kreview_lake.duckdb` file directly into your `output/` directory!
