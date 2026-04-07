---
description: DuckDB usage patterns and anti-patterns for kreview
alwaysApply: true
---

# DuckDB Usage Patterns

## ✅ DO — Glob Scans for Cross-Sample Loading

```python
# Load all FSC.gene files in one query
df = duckdb.sql("""
    SELECT *, regexp_extract(filename, '/([^/]+)/[^/]+$', 1) AS sample_id
    FROM read_parquet('results/*/*.FSC.gene.parquet', filename=true)
""").df()
```

## ✅ DO — Filter in SQL, Not Python

```python
# Filter BEFORE loading into pandas
df = duckdb.sql("""
    SELECT * FROM read_parquet('results/*/*.FSC.gene.parquet', filename=true)
    WHERE gene = 'TP53'
""").df()
```

## ❌ DON'T — Loop with pd.read_parquet

```python
# NEVER do this — 14K individual file opens
for sid in sample_ids:
    df = pd.read_parquet(f"results/{sid}/{sid}.FSC.gene.parquet")  # ❌
```

## ❌ DON'T — Persistent DuckDB Files

```python
# DON'T create persistent .duckdb files — we use glob scans on raw parquets
conn = duckdb.connect("my_data.duckdb")  # ❌
# DO use in-memory connections
conn = duckdb.connect()  # ✅
```

## Connection Lifecycle

- Create per-function or per-notebook, NOT global
- Use `get_duckdb_conn()` helper from `kreview.core`
- Never pass DuckDB connections between notebooks
