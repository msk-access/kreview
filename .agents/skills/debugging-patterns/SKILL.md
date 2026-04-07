---
name: debugging-patterns
description: Structured debugging framework for kreview data pipeline issues
---

# Debugging Patterns

## The 5-Step Framework

1. **Reproduce** — Always reproduce locally before debugging
2. **Isolate** — Single sample, single feature, single stratum
3. **Inspect** — Check data shapes, column names, dtypes
4. **Fix** — Apply minimal fix
5. **Regress** — Add test to prevent recurrence

## Common Failure Modes

### 1. Empty DataFrame from DuckDB Glob
**Symptom**: `load_feature_cohort()` returns 0 rows
**Causes**:
- Glob pattern doesn't match any files
- All samples filtered out by `sample_ids` filter
- Feature suffix typo (`.FSC.gene.parquet` vs `.fsc.gene.parquet`)

**Debug**:
```python
import glob as g
print(len(g.glob(f"{results_dir}/*/*.FSC.gene.parquet")))
```

### 2. Label-Feature Merge Produces Fewer Rows
**Symptom**: `merged = features.merge(labels, on="SAMPLE_ID")` drops samples
**Causes**:
- `sample_id` column has different format (e.g., path prefix)
- Labels use `SAMPLE_ID`, features use `sample_id` (case mismatch)

**Debug**:
```python
print(features["sample_id"].iloc[:3])
print(labels["SAMPLE_ID"].iloc[:3])
shared = set(features["sample_id"]) & set(labels["SAMPLE_ID"])
print(f"Shared: {len(shared)} / features: {features['sample_id'].nunique()} / labels: {labels['SAMPLE_ID'].nunique()}")
```

### 3. Sklearn Model Fails on NaN
**Symptom**: `ValueError: Input contains NaN` from LogisticRegression
**Fix**: Always add NaN handling before modeling:
```python
df = df.dropna(subset=[feature_col])
log.warning("dropped_nan", n_dropped=original_len - len(df))
```

### 4. DuckDB Type Mismatch
**Symptom**: `ConversionException: Could not convert string to INT32`
**Cause**: Parquet files from different samples have different schemas
**Fix**: Use `union_by_name=true` in `read_parquet()`

## Structured Logging with structlog

```python
import structlog
log = structlog.get_logger()

# Good: structured key-value pairs
log.info("feature_loaded", feature="FSC.gene", n_samples=4021, n_rows=514688)

# Bad: f-string messages
log.info(f"Loaded FSC.gene with {n} samples")  # ❌ not queryable
```
