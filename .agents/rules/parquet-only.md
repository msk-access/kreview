# Parquet-Only I/O Rule

## Data Loading
- ONLY load `.parquet` files from krewlyzer results directories.
- NEVER load `.tsv.gz`, `.tsv`, `.features.json`, or `.bed.gz` files.
- Use `pd.read_parquet()` for all feature loading.

## Why
- features.json is 256 MB per sample (~3.5 TB across cohort) — redundant with parquet
- tsv.gz files are slower to load and larger than parquet equivalents
- Parquet supports columnar reads, predicate pushdown, and type preservation

## File Naming Convention
- Feature suffix: `{sample_id}.{FEATURE}.{target_mode}.parquet`
- Example: `P-0000280-T02-XS1.FSC.ontarget.parquet`
- Some features have no target_mode: `P-0000280-T02-XS1.FSC.gene.parquet`
- See §3 and §4 of the implementation plan for the complete file inventory.
