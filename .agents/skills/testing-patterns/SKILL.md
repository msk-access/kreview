---
name: testing-patterns
description: "Testing conventions, patterns, and best practices for kreview. MANDATORY reading before adding or modifying tests."
---

# Testing Patterns for kreview

## Quick Reference

```bash
# Run all tests
python3 -m pytest tests/ -x -q

# Run specific test file
python3 -m pytest tests/test_eval_engine.py -x -q

# Run a single test class
python3 -m pytest tests/test_eval_engine.py::TestWPSGenomeExtract -x -v

# Run a single test
python3 -m pytest tests/test_eval_engine.py::TestWPSGenomeExtract::test_no_overwrite_bug -x -v

# Run tests matching a pattern
python3 -m pytest tests/ -x -q -k "wps or duckdb"

# List all tests without running
python3 -m pytest tests/ --co -q
```

---

## Test File Layout

| File | Module Under Test | Scope |
|------|------------------|-------|
| `test_core.py` | `kreview.core` | Paths, LabelConfig, constants, DuckDB conn, data loaders |
| `test_cli.py` | `kreview.cli` | CLI smoke tests (--help, param validation) |
| `test_eval_engine.py` | `kreview.eval_engine` + `kreview.features.*` | Feature stats, model training, GPU dispatch, WPS extractors |
| `test_labels.py` | `kreview.labels` | 5-tier labeling, CH filtering, IMPACT tissue rescue |
| `test_selection.py` | `kreview.selection` | mRMR, hybrid-union, variance guard, AUC scoring |
| `test_fuse.py` | `kreview.cli` (fuse) | Matrix fusion, column alignment |
| `test_scoreboard.py` | `kreview.scoreboard` | JSON aggregation, ranking, formatting |
| `test_ablation.py` | `kreview.cli_eval` | Feature group identification, nested CV subset eval |
| `test_feature_cards.py` | `kreview.feature_cards` | Card rendering and formatting |
| `test_merge_helpers.py` | `kreview.cli_eval` | JSON merge for decomposed pipeline |
| `test_multimodal_decomposed.py` | `kreview.eval_engine` | Stacking, prep, single-model, merge |
| `test_pipeline_parity.py` | Integration | Monolithic vs multistage result consistency |
| `test_reproducibility.py` | `kreview.eval_engine` | `seed_everything()` determinism |

---

## Test Conventions

### 1. One test class = one functional unit

Group tests by the function/class they exercise:

```python
class TestWPSGenomeExtract:
    """Tests for WPSGenomeEvaluator.extract() — per-region-type aggregation."""

    def test_numpy_arrays_extracted(self): ...
    def test_string_arrays_extracted(self): ...
    def test_empty_dataframe_returns_empty(self): ...
```

**Name classes** `Test<FunctionOrClassName>`. Don't name them after versions (avoid `TestV013Fixes`).

### 2. Use descriptive test names

Good: `test_empty_dataframe_returns_empty`, `test_single_class_returns_error`
Bad: `test_edge_case_1`, `test_bug_fix`

### 3. Import inside test methods

Always import the module under test inside the test method. This ensures tests fail with clear `ImportError` if the module breaks:

```python
def test_configure_sets_defaults(self):
    import kreview.core as core  # Import inside test
    core.configure_duckdb(threads=16, memory="64GB")
    assert core._DUCKDB_THREADS == 16
```

### 4. Clean up module-level state

Tests that modify module globals **must** restore them:

```python
def test_configure_sets_defaults(self):
    import kreview.core as core

    orig_threads = core._DUCKDB_THREADS
    orig_mem = core._DUCKDB_MEMORY
    try:
        core.configure_duckdb(threads=16, memory="64GB")
        assert core._DUCKDB_THREADS == 16
    finally:
        core._DUCKDB_THREADS = orig_threads
        core._DUCKDB_MEMORY = orig_mem
```

### 5. Use cached fixtures for expensive operations

Model training is slow. Use `@pytest.fixture(scope="class")` with caching:

```python
@pytest.fixture(scope="class")
def cached_cpu_model_results(self, binary_Xy):
    """Train once, reuse across all tests in this class."""
    X, y = binary_Xy
    result, fitted = cpu_models(X, y, n_folds=3, random_state=42)
    return result, fitted
```

### 6. Test both positive and negative paths

For every feature, test:
- **Happy path**: Valid input produces expected output
- **Error path**: Invalid input returns error dict (not crash)
- **Edge case**: Empty input, single-class, constant features

```python
def test_valid_input(self):          # Happy path
def test_single_class_returns_error(self):  # Error path
def test_empty_dataframe_returns_empty(self):  # Edge case
```

### 7. Avoid tautologies

```python
# BAD — always passes, tests nothing:
assert model is None or model is not None

# GOOD — tests actual behavior:
assert model is None  # Expected when deps not installed
# or
assert hasattr(model, "predict_proba")  # Expected when deps installed
```

### 8. Use `pytest.mark.skipif` for optional deps

```python
HAS_XGB = False
try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    pass

@pytest.mark.skipif(not HAS_XGB, reason="XGBoost not available")
def test_xgb_model(self): ...
```

---

## Anti-Patterns to Avoid

### 1. Don't duplicate tests across classes

If `TestBuildGpuModelNameDispatch.test_invalid_name_returns_none` already tests
unknown model names, don't add `TestBuildGpuModelV8.test_unknown_model_returns_none`.

**Check**: Before writing a new test, `grep` for the function being tested:
```bash
grep -n "def test_.*unknown\|def test_.*invalid" tests/test_eval_engine.py
```

### 2. Don't version-name test classes

```python
# BAD — what does "V8" or "V013" mean to a new developer?
class TestBuildGpuModelV8:
class TestBuildModelDispatchV013:

# GOOD — describes what is being tested
class TestGPUModelImportPaths:
class TestBuildModelDispatch:
```

> [!NOTE]
> Existing tests with version names are kept for backward compatibility.
> New tests should use descriptive names.

### 3. Don't test implementation details

```python
# BAD — tests internal data structure, fragile
assert model._internal_cache == {}

# GOOD — tests public API behavior
assert model.predict_proba(X).shape == (n_samples, 2)
```

### 4. Don't ignore test failures with broad `try/except`

```python
# BAD — silently skips on ANY error
try:
    model = _build_gpu_model("tabpfn")
    assert model is not None
except Exception:
    pytest.skip("tabpfn not installed")

# GOOD — only skip on import errors
try:
    model = _build_gpu_model("tabpfn")
except ImportError:
    pytest.skip("tabpfn not installed")
else:
    assert model is not None or model is None  # Fine — either path valid
```

---

## When to Add Tests

### Adding a new evaluator (feature extractor)

Add tests in `test_eval_engine.py`:
1. `test_extract_valid_input` — happy path
2. `test_extract_empty_returns_empty` — edge case
3. `test_extract_missing_column_returns_empty` — error handling
4. `test_no_overwrite_bug` — aggregation correctness (100 rows, check mean)

If the evaluator has `extract_sql()`:
5. `test_extract_sql_returns_query` — non-None string
6. `test_supports_sql_true` — property check
7. `test_sql_contains_expected_functions` — SQL correctness
8. `test_sql_pivot_column_set` — pivot column property

### Adding a new CLI command

Add tests in `test_cli.py`:
1. `test_<cmd>_help` — `--help` returns exit code 0
2. Add `<cmd>` to `TestTopLevel.test_help_lists_all_commands`
3. `test_<cmd>_missing_required` — missing required args → non-zero exit

### Adding a new Nextflow process

Update `nextflow.config`:
1. Add `withName` block with `errorStrategy` + `maxRetries`
2. Pin `queue` explicitly if on SLURM
3. Document memory profile in comments

---

## Pre-Commit Test Checklist

```bash
# 1. Run full test suite
python3 -m pytest tests/ -x -q

# 2. Verify no test count regression
python3 -m pytest tests/ --co -q  # should match expected count

# 3. Check for new test redundancies
# Search for tests with similar names to yours
grep -n "def test_.*<your_function_name>" tests/*.py

# 4. Verify nbdev sync didn't break tests
python3 -m nbdev.export && python3 -m pytest tests/ -x -q
```

---

## Test Timeouts

All tests have a **120-second timeout** (configured in `pyproject.toml`).
If a test approaches this limit:
1. Check if it's doing unnecessary model training
2. Use cached fixtures
3. Reduce data size for the test
