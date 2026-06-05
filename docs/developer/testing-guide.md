# Testing Guide

`kreview` is built to process large Fragmentomics datasets and evaluate complex Machine Learning features. Because the codebase runs cross-validation, hyperparameter sweeping, and ML model training (LR, RF, XGBoost + optional GPU models) natively in Python, the test suite can quickly become a massive bottleneck if not managed carefully.

This guide outlines our testing philosophy, how to run tests, and critical performance optimization strategies.

---

## 🏃 Running Tests Locally

To run the entire test suite:
```bash
pytest
```

To run a specific test file or module:
```bash
pytest tests/test_eval_engine.py
```

### Coverage
We track test coverage to ensure new evaluators and core functionalities are adequately tested. To run tests with coverage reporting:
```bash
pytest --cov=kreview
```
A summary will be printed to your terminal. Our CI/CD pipeline enforces passing tests on every PR to `develop`.

---

## 🏎️ Profiling and Performance

If `pytest` takes more than **2 minutes** to execute, something is likely misconfigured or a test is repeatedly spinning up expensive resources. 

You can identify the slowest tests by using the `--durations` flag:
```bash
# Show the 10 slowest tests
pytest --durations=10
```

### The "Module Scope" Fixture Pattern (CRITICAL)

The most common reason for a slow test suite in `kreview` is repeatedly fitting models inside the test setup. 

For instance, `test_eval_engine.py` contains over 20 test cases that validate the outputs of `single_feature_model()`. If each test calls `single_feature_model(X, y)` independently, it runs 5-fold cross validation for 3+ different algorithms *20 times*, adding minutes to the test run.

**The Solution:**
We heavily leverage `@pytest.fixture(scope="module")` to cache expensive computations *once per test session*.

**Example:**
Instead of computing the model inside the test:
```python
# ❌ BAD: Runs a 5-fold CV Random Forest every single time
def test_auc_std_present(self, binary_Xy):
    X, y = binary_Xy
    results, *_ = single_feature_model(X, y)
    assert "rf_auc_std" in results
```

Use the cached module fixture:
```python
# ✅ GOOD: Reuses the result from the module cache (Instant!)
def test_auc_std_present(self, cached_cpu_model_results):
    results, *_ = cached_cpu_model_results
    assert "rf_auc_std" in results
```

When writing new tests that require model fitting or complex DuckDB table generation, **always construct a module-scoped fixture** so that subsequent tests can run instantly.

---

## 🧪 Testing Auto-Generated Code
Remember that `kreview` uses [nbdev](nbdev-workflow.md). The application source code (`kreview/*.py`) is generated from Jupyter notebooks in `nbs/`. 

However, **the test suite in `tests/` is NOT auto-generated.**
You should edit the files in `tests/*.py` directly using your standard IDE (VS Code, PyCharm, vim). You do not need to write tests inside the Jupyter notebooks.

## 🗃️ Mocking DuckDB

When testing extraction pipelines, prefer writing small synthentic Parquet files using `pandas.DataFrame.to_parquet()` into a Pytest `tmp_path` fixture rather than querying real patient data. This ensures tests remain deterministic, fast, and secure.

## 🧠 Testing GPU Models

GPU model tests are **marked with `@pytest.mark.gpu`** and skipped when CUDA is unavailable. The `GPUModelCVAdapter` wrapper can be tested without a GPU by mocking the inner model:

```python
# ✅ Test GPUModelCVAdapter without GPU
@pytest.fixture(scope="module")
def mock_gpu_adapter():
    from kreview.eval_engine import GPUModelCVAdapter
    from sklearn.linear_model import LogisticRegression
    # Use LR as a stand-in to test adapter delegation
    adapter = GPUModelCVAdapter(LogisticRegression())
    return adapter

def test_adapter_sets_classes(mock_gpu_adapter, binary_Xy):
    X, y = binary_Xy
    mock_gpu_adapter.fit(X, y)
    assert hasattr(mock_gpu_adapter, 'classes_')
    assert list(mock_gpu_adapter.classes_) == [0, 1]
```

For integration tests that require actual GPU hardware, use the `gpu` mark:
```bash
pytest -m gpu  # Run GPU tests only (requires CUDA)
pytest -m "not gpu"  # Skip GPU tests (CI default)
```
