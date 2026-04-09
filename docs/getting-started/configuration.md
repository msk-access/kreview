# System Configuration

To run smoothly across large-scale cohorts, `kreview` needs two things:

1. Access to cleanly formatted MSK-IMPACT clinical cohort files from cBioPortal.
2. Paths pointing to the Krewlyzer parquet output directories.

---

## The `Paths` Dataclass

The core data structure mapping all input locations is defined in `kreview.core`:

```python
@dataclass
class Paths:
    """All input paths for the labeling pipeline."""
    cancer_samplesheet: Path
    healthy_xs1_samplesheet: Path
    healthy_xs2_samplesheet: Path
    cbioportal_dir: Path          # Directory containing all 5 cBioPortal files
    krewlyzer_dirs: list[Path] = field(default_factory=list)
```

!!! info "Manifest File Support"
    The `krewlyzer_dirs` field is flexible. You can pass it:

    - **Direct directories**: `/path/to/krewlyzer/v0.8.2/access_12_245/`
    - **A manifest `.txt` file**: A text file listing one directory per line. The pipeline will automatically expand it:

    ```text
    # manifest.txt
    /data/krewlyzer/v0.8.2/access_12_245
    /data/krewlyzer/v0.8.2/access_13_180
    /data/krewlyzer/v0.8.2/healthy_controls
    ```

    Missing paths are logged as warnings but do not crash the pipeline.

---

## The `LabelConfig` Dataclass

Fine-tune the biological labeling thresholds:

```python
@dataclass
class LabelConfig:
    """Configuration for the ctDNA labeling engine."""
    min_vaf: float = 0.01        # VAF threshold for Possible ctDNA+
    min_variants: int = 1        # Minimum # somatic SNVs passing VAF threshold
    min_fragments: int = 2000    # Min fragments for Depth QC gate
    access_panels: tuple = ("ACCESS129", "ACCESS146")
    impact_panels: tuple = ("IMPACT341", "IMPACT410", "IMPACT468", "IMPACT505")
```

These are configurable directly from the CLI via `--min-vaf`, `--min-variants`, and `--min-fragments`.

---

## The `cbioportal_dir`

!!! danger "Required Files"
    When you point the pipeline at `--cbioportal-dir`, it rigidly expects **five** specific files inside that directory. If any are missing, the labeling engine will crash to prevent erroneous biological ground truths.

| # | File | Purpose |
|---|------|---------|
| 1 | `data_mutations_extended.txt` | Global MAF (somatic variants) |
| 2 | `data_sv.txt` | Structural Variants |
| 3 | `data_CNA.txt` | Wide-matrix discrete Copy Number Alterations |
| 4 | `data_clinical_sample.txt` | Sample-level clinical metadata |
| 5 | `data_clinical_patient.txt` | Patient-level clinical metadata |

---

## DuckDB Networking Tuning

When loading large cohorts (e.g., 4,600+ samples), DuckDB may attempt to open thousands of parquet file handles simultaneously when reading from remote network-mounted directories. This can exceed OS-level open file limits.

To prevent this, `kreview` applies two layers of protection natively:

```python
conn.execute("SET threads=4;")    # Throttle parallel I/O threads
conn.execute("SET memory_limit='4GB';")
```

If your system still crashes mid-read, lower the batch load via the CLI:

```bash
kreview run ... --chunk-size 100
```

See the [DuckDB Architecture](../developer/duckdb-architecture.md) page for the full technical deep-dive.
