# System Configuration

To run smoothly across multi-terabyte data lakes, `kreview` expects two things: 
1. Access to cleanly formatted MSK-IMPACT Clinical Cohort files.
2. Stability when dealing with Mac FUSE SFTP drivers.

---

## DuckDB Networking Tuning
Because the evaluation engine utilizes DuckDB to query remote `.parquet` files, local Macs using mount clients (like **Cyberduck** `duck` or **SSHFS**) frequently hit `maxfiles` or parallel socket crash limits (`PermissionError`). 

To solve this we have heavily chunked the I/O engine natively in the Python code:
```python
conn.execute("SET threads=4;") # Throttle SFTP I/O bursts
def load_feature_cohort(..., chunk_size=500):
    # Reads 500 files at a time to circumvent maxfiles limits
```

If your system crashes mid-read, you can manually lower the burst load via the CLI using the `--chunk-size` flag! See more in the [Pipeline Reference](pipeline-cli.md).

---

## The Paths Matrix

The core data structure mapping all network drives relies on defining exactly where the metadata is located. You will need to explicitly path out these directories when running `kreview`.

```python
@dataclass
class Paths:
    """All input paths for the labeling pipeline."""
    cancer_samplesheet: Path
    healthy_xs1_samplesheet: Path
    healthy_xs2_samplesheet: Path
    cbioportal_dir: Path  # Must contain the 5 canonical cBioPortal files!
    results_dir: Path | None = None
```

### The `cbioportal_dir`
When you point your pipeline at the `--cbioportal-dir`, it rigidly expects five specific files inside that folder to construct the `True ctDNA+` label matrix:

1. `data_mutations_extended.txt` (The global MAF)
2. `data_sv.txt` (Structural Variants)
3. `data_CNA.txt` (Wide-matrix discrete copy number alterations)
4. `data_clinical_sample.txt`
5. `data_clinical_patient.txt`

If any of these are missing from your directory, the labeling engine will crash, preventing erroneous or partial biological ground truths!
