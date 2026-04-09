# Troubleshooting FAQ

Common issues and their solutions.

---

## Installation & Environment

??? danger "`nbdev-test` crashes with `ImportError: cannot import name 'strip_ansi'`"

    **Cause:** The `execnb` package installed via conda is outdated (v0.1.11) and incompatible with modern IPython.

    **Fix:** Upgrade via pip:
    ```bash
    pip install --upgrade execnb nbdev
    ```

    This installs `execnb >= 0.1.18` which resolves the `strip_ansi` deprecation.

??? danger "`ModuleNotFoundError: No module named 'kreview.features.xyz'`"

    **Cause:** The notebooks have been edited but `nbdev-export` was not run.

    **Fix:**
    ```bash
    nbdev-export
    ```

    This regenerates all `kreview/*.py` files from the notebooks.

??? warning "`AttributeError: module 'kreview.eval_engine' has no attribute 'xyz'`"

    **Cause:** The function exists in the notebook but the cell is missing the `#| export` directive.

    **Fix:** Open the notebook in `nbs/`, find the cell with the function, and add `#| export` at the top of the cell. Then run `nbdev-export`.

---

## Pipeline Execution

??? danger "`PermissionError: [Errno 1] Operation not permitted` during large cohort loading"

    **Cause:** DuckDB is trying to open more parquet file handles than the OS allows.

    **Fix:** Reduce the chunk size:
    ```bash
    kreview run ... --chunk-size 100
    ```

    The pipeline also has built-in exponential backoff retry (3 attempts with 1s/2s/4s delays), so transient failures are handled automatically.

??? warning "Empty feature matrix — evaluator produces no output"

    **Cause:** The parquet suffix in the evaluator's `source_file` doesn't match the actual files on disk.

    **Fix:** Check the evaluator class definition:
    ```python
    class MyEvaluator(FeatureEvaluator):
        source_file = ".MyFeature.ontarget.parquet"  # Must match exactly!
    ```

    Verify the file exists for at least one sample:
    ```bash
    ls /path/to/krewlyzer/SAMPLE_ID/SAMPLE_ID.MyFeature.ontarget.parquet
    ```

??? warning "Feature evaluator not found in registry"

    **Cause:** The evaluator class was not exported from the notebook, or it doesn't subclass `FeatureEvaluator`.

    **Fix:**
    1. Ensure the notebook cell has `#| export`
    2. Ensure the class inherits from `FeatureEvaluator`
    3. Run `nbdev-export`
    4. Verify with `kreview features-list`

---

## Dashboard & Reports

??? info "Quarto not found — dashboard generation skipped"

    **Cause:** Quarto CLI is not installed in your environment.

    **Fix:** Install Quarto from [quarto.org](https://quarto.org/docs/get-started/) or use the Docker image which includes Quarto pre-installed.

    Alternatively, skip reports entirely:
    ```bash
    kreview run ... --skip-report
    ```

??? info "SHAP plots show blank — only RF appears, no XGBoost"

    **Cause:** XGBoost failed to import silently. The engine degraded to RF-only mode.

    **Fix:** Install XGBoost explicitly:
    ```bash
    pip install xgboost>=2.0.0
    ```

---

## Git & nbdev

??? warning "Massive diffs in notebook files on `git diff`"

    **Cause:** Jupyter notebook metadata (execution counts, outputs) was not stripped.

    **Fix:**
    ```bash
    nbdev-clean
    nbdev-install-hooks  # Prevents this in the future
    ```

??? info "I accidentally edited a `.py` file directly. How do I fix it?"

    Run `nbdev-update` to sync your changes back to the notebooks:
    ```bash
    nbdev-update
    ```

    Then verify and re-export:
    ```bash
    nbdev-export
    ```
