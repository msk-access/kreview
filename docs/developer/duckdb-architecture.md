# DuckDB Network Architecture

`kreview` aggregates tens of millions of rows of heavily nested fragmentomics data on a consumer MacBook, utilizing **DuckDB** as the high-velocity backing query engine.

Processing large-scale cohorts located on remote network-mounted directories requires significant logic tuning to prevent systemic failures from concurrent file handle exhaustion.

---

## The Unix `maxfiles` Limit 

When loading a massive cohort (e.g., 4,600 samples), a naive query using glob-scanning:

```sql
SELECT * FROM read_parquet('/data/krewlyzer/v0.8.2/*/*_matrix.parquet')
```

will cause DuckDB to aggressively initiate parallel filesystem thread expansion, attempting to open all 4,600 file handles simultaneously. This trips the macOS POSIX `ulimit` for concurrent open files (usually hardcapped at 256 or 1024):

```
PermissionError: [Errno 1] Operation not permitted
```

## I/O Thread Throttling

To fix this natively inside Python, we override DuckDB's default configuration:

```python
conn.execute("SET threads = 4")       # (1)!
conn.execute("SET memory_limit = '4GB'")  # (2)!
```

1. Limits DuckDB to 4 concurrent I/O threads instead of `os.cpu_count()`
2. Prevents DuckDB from consuming all available memory during large joins

## Feature Batching (`chunk_size`)

Inside `load_feature_cohort`, we completely abandoned `read_parquet(*/*)` glob functionality.

Instead, we generate an explicit Python `list` of file paths by discovering files manually using `Path.iterdir()`, then chunk that list:

```python
chunk_size = 500

for i in range(0, len(file_paths), chunk_size):
    chunk = file_paths[i:i + chunk_size]
    df_chunk = conn.execute(
        "SELECT * FROM read_parquet(?, union_by_name=true)",
        [chunk]
    ).df()
```

By default, `chunk_size` is tuned to `500` to sit comfortably underneath the default 1024 macOS limits. You can tune this further downward using the CLI `--chunk-size` flag.

## Exponential Backoff Retry

Even with chunking, transient I/O failures can occur when reading parquet files from network-mounted directories. To handle this gracefully, `kreview` implements automatic retry logic with exponential backoff:

```python
max_retries = 3

for attempt in range(max_retries):
    try:
        df_chunk = conn.execute(query, [chunk]).df()
        df_list.append(df_chunk)
        break
    except Exception as e:
        if attempt < max_retries - 1:
            log.warning("duckdb_retry", attempt=attempt+1, error=str(e))
            time.sleep(2 ** attempt)  # 1s, 2s, 4s backoff
        else:
            log.error("chunk_load_failed", error=str(e))
            return pd.DataFrame()  # Permanent failure
```

!!! tip "When to Use `--chunk-size`"
    If you see `PermissionError` or `IO Error` during large cohort loading:

    - First retry: the backoff mechanism will handle transient failures automatically
    - Persistent failures: reduce `--chunk-size` to `100` or `50`
    - Very congested networks: also try `--workers 1` to serialize I/O completely
