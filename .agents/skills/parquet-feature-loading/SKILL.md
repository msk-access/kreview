---
name: parquet-feature-loading
description: How to load krewlyzer parquet feature files with correct suffixes and schemas per feature type.
---

# Parquet Feature Loading

## When to use this skill
- Implementing a new FeatureEvaluator
- Loading sample feature data in exploration cells
- Debugging missing or malformed feature files

## Loading Pattern
```python
from kreview.core import load_sample_feature

# Load a feature parquet for one sample
df = load_sample_feature(
    sample_id="P-0000280-T02-XS1",
    feature_suffix=".FSC.gene.parquet",  # exact suffix from §4 table
    results_dir="/path/to/results/",
)
```

## Feature File Suffix Reference

| Evaluator | `source_file` |
|---|---|
| FSC.gene | `.FSC.gene.parquet` |
| FSC bin-level | `.FSC.ontarget.parquet` |
| FSC.regions | `.FSC.regions.parquet` |
| FSD | `.FSD.ontarget.parquet` |
| FSR | `.FSR.ontarget.parquet` |
| OCF ontarget | `.OCF.ontarget.parquet` |
| OCF offtarget | `.OCF.offtarget.parquet` |
| ATAC | `.ATAC.ontarget.parquet` |
| TFBS | `.TFBS.ontarget.parquet` |
| MDS | `.MDS.ontarget.parquet` |
| MDS.gene | `.MDS.gene.parquet` |
| MDS.exon | `.MDS.exon.parquet` |
| EndMotif | `.EndMotif.ontarget.parquet` |
| BreakPointMotif | `.BreakPointMotif.ontarget.parquet` |
| EndMotif1mer | `.EndMotif1mer.parquet` |
| WPS.panel | `.WPS.panel.parquet` |
| WPS genome | `.WPS.parquet` |
| WPS background | `.WPS_background.parquet` |
| metadata | `.metadata.parquet` |

## Anti-Patterns
- ❌ Loading `.tsv.gz` or `.features.json`
- ❌ Constructing file paths manually — use `load_sample_feature()`
- ❌ Loading `.correction_factors.parquet` or `.fsc_counts.parquet` (excluded)
