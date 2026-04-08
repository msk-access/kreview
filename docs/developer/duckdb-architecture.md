# DuckDB Network Architecture

`kreview` aggregates tens of millions of rows of heavily nested fragmentomics data gracefully on a consumer Macbook, utilizing **DuckDB** as the high-velocity backing query engine.

However, processing large-scale cohorts physically located on an enterprise-cluster requires significant logic tuning to prevent total systemic failures over remote-mounted drives (like Cyberduck FUSE).

---

## The Unix `maxfiles` Limit 

When loading a massive cohort (e.g., 4,600 samples), a naive query using glob-scanning:
```sql
SELECT * FROM read_parquet('/mount/islogin01/share/krewlyzer/0.8.2/access_12_245/*/*_matrix.parquet')
```

Will cause DuckDB to aggressively initiate parallel filesystem thread expansion. It attempts to open all 4,600 `file-handles` simultaneously. Over high-latency SFTP mounts on Mac, this trips the macOS underlying POSIX `ulimit` for concurrent open files (usually hardcapped at 256 or 1024 Unix sockets).

The error you will see is a seemingly random system-side IO failure:
```python
PermissionError: [Errno 1] Operation not permitted (or Permission denied)
```

## I/O Thread Throttling

To fix this natively internally inside Python, we override DuckDBs default architecture config map when initializing an SQL connection (`get_duckdb_conn`).

We strictly constrain it mathematically from exhausting cluster queues:
```python
conn.execute("SET threads = 4")
conn.execute("SET memory_limit = '4GB'")
```

## Feature Batching (`chunk_size`)

Inside our `load_feature_cohort` function, we completely abandoned `read_parquet(*/*)` glob functionality.

Instead, we generate an explicit python structural `list` of strings by discovering files manually using `Path.iterdir()`. 

We then chunk that explicit python list and query them individually recursively through DuckDB array slicing:
```python
chunk_size = 500

for i in range(0, len(file_paths), chunk_size):
    chunk = file_paths[i:i + chunk_size]
    
    # Send strict array to DuckDB, meaning only max 500 files are requested
    df_chunk = conn.execute("SELECT * FROM read_parquet(?, union_by_name=true)", [chunk]).df()
```

By default, the `chunk_size` is tuned to `500` to sit comfortably underneath the default 1024 OSX limits. You can tune this further downward if operating on heavily congested Wifi systems using the CLI `--chunk-size` flag!
