---
description: Structured debugging workflow for traceback or unexpected behavior
---

1. **Reproduce**: Run the failing command/cell and capture the full traceback.

2. **Classify** the error:
   - `FileNotFoundError` → missing parquet file → check sample availability
   - `KeyError` → DataFrame column mismatch → check schema
   - `ValueError` → data shape/type issue → check parquet content
   - `DuckDB Error` → SQL syntax or glob pattern issue

3. **Isolate**: Narrow down to the smallest reproducing case:
   ```python
   # Try with a single sample first
   df = load_feature_cohort('.FSC.gene.parquet', results_dir, sample_ids=['P-0000280-T02-XS1'])
   ```

4. **Add diagnostic logging**:
   ```python
   log.info("debug_checkpoint", shape=df.shape, columns=list(df.columns),
            sample_ids=df["sample_id"].nunique())
   ```

5. **Check data invariants**:
   ```python
   assert "sample_id" in df.columns, f"Missing sample_id. Columns: {df.columns.tolist()}"
   assert len(df) > 0, "Empty DataFrame — check glob pattern"
   assert df["sample_id"].nunique() == len(expected_ids), "Sample count mismatch"
   ```

6. **Fix and verify**: After fixing, run the full test suite:
   ```bash
   nbdev-test --n_workers 4
   ```

7. **Add regression test**: Create a `#| test` cell in the relevant notebook that covers the fixed edge case.

8. **Remove debug logging**: Clean up diagnostic statements before committing.
