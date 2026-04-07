---
name: duckdb-patterns
description: DuckDB glob scan patterns, connection management, and performance for kreview
---

# DuckDB Patterns for kreview

## Feature Suffix Reference

| Feature | Suffix | Rows Per Sample |
|---|---|---|
| FSC.gene | `.FSC.gene.parquet` | ~128 |
| FSD | `.FSD.chr_arm.parquet` | ~39 |
| FSR | `.FSR.parquet` | 1 |
| OCF.ontarget | `.OCF.ontarget.parquet` | ~100 |
| WPS.background | `.WPS_background.parquet` | ~22 |
| metadata | `.metadata.parquet` | 1 |

## Glob Patterns

```python
# Single feature, all samples
read_parquet('results/*/*.FSC.gene.parquet', filename=true)

# Multiple features via UNION ALL
SELECT 'FSC' AS feature, * FROM read_parquet('results/*/*.FSC.gene.parquet', filename=true)
UNION ALL
SELECT 'FSD' AS feature, * FROM read_parquet('results/*/*.FSD.chr_arm.parquet', filename=true)
```

## Connection Management

```python
# ✅ Per-function connection (recommended)
def load_data():
    conn = get_duckdb_conn()  # from kreview.core
    return conn.sql("...").df()

# ❌ Global connection (fragile in notebooks)
CONN = duckdb.connect()  # dies on kernel restart
```

## Performance Tips

1. **Predicate pushdown**: Filter in SQL before `.df()`
2. **Column projection**: `SELECT col1, col2` not `SELECT *`
3. **Thread config**: `SET threads TO 4` (default is all cores)
4. **Memory limit**: `SET memory_limit = '4GB'` for large cohorts

## Future: DuckLake Migration

When DuckLake reaches v1.0, the migration is:
```python
# Before (DuckDB glob):
conn.sql("SELECT * FROM read_parquet('results/*/*.FSC.gene.parquet')")

# After (DuckLake):
conn.execute("ATTACH 'ducklake:catalog.ducklake' AS eval")
conn.sql("SELECT * FROM eval.fsc_gene")
```
Downstream code is identical — only the data source changes.
