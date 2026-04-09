# Core Architecture

The `kreview.core` module establishes all `dataclass` configurations (`Paths`, `LabelConfig`, `EvalRun`), DuckDB connection management, and the thread-throttled parquet loading engine with exponential backoff retry.

For conceptual explanations, see:

- [Configuration Guide](../getting-started/configuration.md)
- [DuckDB Architecture](../developer/duckdb-architecture.md)

---

::: kreview.core
    options:
      show_root_heading: true
      show_source: false
      members_order: source
