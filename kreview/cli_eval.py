"""Evaluation CLI subcommands: kreview eval cpu|gpu|multimodal.

Registered in the main CLI via::

    from kreview.cli_eval import eval_app
    app.add_typer(eval_app, name="eval")

This keeps evaluation-specific code out of the 1,500-line cli.py.
"""

import typer
import json
import time as _time
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

eval_app = typer.Typer(name="eval", help="Model evaluation commands")


# ── Shared helpers ────────────────────────────────────────────────────────────


def _load_matrix_and_labels(
    matrix_path: Path,
    label_col: str = "label",
    sample_id_col: str = "sample_id",
) -> tuple[pd.DataFrame, np.ndarray, list[str], np.ndarray | None, np.ndarray | None]:
    """Load a feature matrix parquet and extract features, labels, metadata.

    Returns (model_df, y, feature_cols, cancer_types, assays).
    Raises typer.Exit on validation errors.
    """
    if not matrix_path.exists():
        print(f"ERROR: Matrix not found: {matrix_path}", flush=True)
        raise typer.Exit(code=1)

    df = pd.read_parquet(matrix_path)
    print(f"  Loaded: {df.shape[0]} samples x {df.shape[1]} columns", flush=True)

    # Identify feature columns (sub-metric format or __ prefixed)
    feature_cols = [
        c
        for c in df.columns
        if c
        not in {
            label_col,
            sample_id_col,
            "CANCER_TYPE",
            "access_version",
            "DMP_ASSAY_ID",
            "sample_key",
        }
        and not c.startswith("_meta")
    ]

    if not feature_cols:
        print("ERROR: No feature columns found in matrix", flush=True)
        raise typer.Exit(code=1)

    # Build binary target
    model_mask = df[label_col].isin(
        [
            "True ctDNA+",
            "Possible ctDNA+",
            "Healthy Normal",
            "Possible ctDNA-",
            "Possible ctDNA\u2212",
        ]
    )
    model_df = df[model_mask].copy()
    y = model_df[label_col].isin(["True ctDNA+", "Possible ctDNA+"]).astype(int).values

    if len(model_df) < 20 or len(np.unique(y)) < 2:
        print(
            f"ERROR: Insufficient data (n={len(model_df)}, "
            f"classes={len(np.unique(y))})",
            flush=True,
        )
        raise typer.Exit(code=1)

    # Impute + drop zero-variance
    X_df = model_df[feature_cols].copy()
    X_df = X_df.fillna(X_df.median())
    nonconst = [c for c in feature_cols if X_df[c].std() > 0]
    n_dropped = len(feature_cols) - len(nonconst)
    if n_dropped > 0:
        print(f"  Dropped {n_dropped} zero-variance features", flush=True)
    feature_cols = nonconst

    if not feature_cols:
        print("ERROR: All features have zero variance", flush=True)
        raise typer.Exit(code=1)

    # Extract metadata arrays
    cancer_types = model_df.get("CANCER_TYPE", None)
    if cancer_types is not None:
        cancer_types = cancer_types.values
    assays = model_df.get("access_version", None)
    if assays is not None:
        assays = assays.values

    return model_df, y, feature_cols, cancer_types, assays


def _save_results(
    results: dict,
    output_dir: Path,
    filename: str,
    extra_meta: dict | None = None,
) -> Path:
    """Save model results to JSON with optional metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename

    if extra_meta and "error" not in results:
        results.update(extra_meta)

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"  Output: {out_path}", flush=True)
    return out_path


# ── eval cpu ──────────────────────────────────────────────────────────────────


@eval_app.command("cpu")
def eval_cpu(
    matrices_dir: Path = typer.Option(
        ...,
        "--matrices-dir",
        help="Directory containing *_matrix.parquet files from kreview extract",
    ),
    output: Path = typer.Option("output/", help="Output directory"),
    models: str = typer.Option(
        "lr,rf,xgb",
        "--models",
        help="Comma-separated CPU models: lr,rf,xgb",
    ),
    cv_folds: int = typer.Option(5, "--cv-folds", help="Cross-validation folds"),
    resume: bool = typer.Option(
        False, "--resume", help="Skip evaluators with existing results"
    ),
):
    """Per-evaluator evaluation using LR, RF, XGBoost (CPU).

    Iterates over all *_matrix.parquet files in --matrices-dir,
    trains the specified models, and writes *_model_results.json
    to --output.
    """
    from kreview.eval_engine import cpu_models

    print("=== kreview eval cpu ===", flush=True)
    print(f"  --matrices-dir : {matrices_dir}", flush=True)
    print(f"  --output       : {output}", flush=True)
    print(f"  --models       : {models}", flush=True)
    print(f"  --cv-folds     : {cv_folds}", flush=True)
    print(f"  --resume       : {resume}", flush=True)
    print("", flush=True)

    if not matrices_dir.exists():
        print(f"ERROR: Matrices directory not found: {matrices_dir}", flush=True)
        raise typer.Exit(code=1)

    matrix_files = sorted(matrices_dir.glob("*_matrix.parquet"))
    if not matrix_files:
        print(f"ERROR: No *_matrix.parquet files in {matrices_dir}", flush=True)
        raise typer.Exit(code=1)

    print(f"  Found {len(matrix_files)} evaluator matrices", flush=True)

    models_list = [m.strip() for m in models.split(",")]
    output.mkdir(parents=True, exist_ok=True)

    for mf in matrix_files:
        evaluator = mf.stem.replace("_matrix", "")
        out_file = output / f"{evaluator}_model_results.json"

        # Resume: check for existing model keys
        if resume and out_file.exists():
            with open(out_file) as f:
                existing = json.load(f)
            existing_models = {
                k.replace("auc_", "")
                for k in existing
                if k.startswith("auc_") and isinstance(existing[k], (int, float))
            }
            remaining = set(models_list) - existing_models
            if not remaining:
                print(
                    f"  SKIP ({evaluator}): all {len(existing_models)} models computed",
                    flush=True,
                )
                continue
            print(
                f"  RESUME ({evaluator}): running {remaining} "
                f"(existing: {existing_models})",
                flush=True,
            )

        print(f"\n  Evaluating: {evaluator}", flush=True)
        t0 = _time.time()

        try:
            model_df, y, feature_cols, c_types, a_types = _load_matrix_and_labels(mf)
            X = model_df[feature_cols].fillna(model_df[feature_cols].median()).values

            results, lr, rf, xgb = cpu_models(
                X,
                y,
                feature_names=feature_cols,
                cancer_types=c_types,
                assays=a_types,
                n_folds=cv_folds,
            )

            # Add sample IDs for multimodal alignment
            if "sample_id" in model_df.columns:
                results["oof_sample_ids"] = model_df["sample_id"].tolist()

            _save_results(
                results,
                output,
                f"{evaluator}_model_results.json",
                extra_meta={"evaluator": evaluator, "matrix_path": str(mf)},
            )

            def _fmt(v):
                return "N/A" if v is None else f"{v:.3f}"

            elapsed = _time.time() - t0
            print(
                f"  {evaluator}: AUC_LR={_fmt(results.get('auc_lr'))}, "
                f"AUC_RF={_fmt(results.get('auc_rf'))}, "
                f"AUC_XGB={_fmt(results.get('auc_xgb'))} "
                f"in {elapsed:.1f}s",
                flush=True,
            )
        except SystemExit:
            raise  # re-raise typer.Exit
        except Exception as e:
            log.error("eval_cpu_evaluator_failed", evaluator=evaluator, error=str(e))
            print(f"  ERROR ({evaluator}): {e}", flush=True)
            continue

    print("\n=== eval cpu complete ===", flush=True)


# ── eval gpu ──────────────────────────────────────────────────────────────────


@eval_app.command("gpu")
def eval_gpu(
    matrices_dir: Path = typer.Option(
        ...,
        "--matrices-dir",
        help="Directory containing *_matrix.parquet files from kreview extract",
    ),
    output: Path = typer.Option("output/", help="Output directory"),
    models: str = typer.Option(
        "tabpfn,tabicl",
        "--models",
        help="Comma-separated GPU models: tabpfn,tabicl",
    ),
    cv_folds: int = typer.Option(5, "--cv-folds", help="Cross-validation folds"),
    no_finetune: bool = typer.Option(
        False,
        "--no-finetune",
        help="Use zero-shot inference instead of fine-tuning (not recommended)",
    ),
    finetune_epochs: int = typer.Option(
        30, "--finetune-epochs", help="Fine-tuning epochs"
    ),
    finetune_lr: float = typer.Option(
        1e-5, "--finetune-lr", help="Fine-tuning learning rate"
    ),
    device: str = typer.Option("cuda", "--device", help="PyTorch device: cuda, cpu"),
    compute_shap: bool = typer.Option(False, "--shap", help="Compute SHAP values"),
    shap_samples: int = typer.Option(500, "--shap-samples", help="Max SHAP samples"),
    resume: bool = typer.Option(
        False, "--resume", help="Skip evaluators with existing results"
    ),
):
    """Per-evaluator evaluation using TabPFN, TabICL (GPU).

    Fine-tuning is ON by default. Use --no-finetune for zero-shot.
    Iterates over all *_matrix.parquet files and writes results JSONs.
    """
    from kreview.eval_engine import gpu_models

    print("=== kreview eval gpu ===", flush=True)
    print(f"  --matrices-dir   : {matrices_dir}", flush=True)
    print(f"  --output         : {output}", flush=True)
    print(f"  --models         : {models}", flush=True)
    print(f"  --device         : {device}", flush=True)
    print(f"  --finetune       : {not no_finetune}", flush=True)
    print(f"  --finetune-epochs: {finetune_epochs}", flush=True)
    print(f"  --cv-folds       : {cv_folds}", flush=True)
    print(f"  --resume         : {resume}", flush=True)
    print("", flush=True)

    if not matrices_dir.exists():
        print(f"ERROR: Matrices directory not found: {matrices_dir}", flush=True)
        raise typer.Exit(code=1)

    matrix_files = sorted(matrices_dir.glob("*_matrix.parquet"))
    if not matrix_files:
        print(f"ERROR: No *_matrix.parquet files in {matrices_dir}", flush=True)
        raise typer.Exit(code=1)

    print(f"  Found {len(matrix_files)} evaluator matrices", flush=True)

    models_list = tuple(m.strip() for m in models.split(","))
    output.mkdir(parents=True, exist_ok=True)

    for mf in matrix_files:
        evaluator = mf.stem.replace("_matrix", "")
        out_file = output / f"{evaluator}_model_results.json"

        # Resume: check existing model keys
        existing_results = {}
        if resume and out_file.exists():
            with open(out_file) as f:
                existing_results = json.load(f)
            existing_models = {
                k.replace("auc_", "")
                for k in existing_results
                if k.startswith("auc_")
                and isinstance(existing_results[k], (int, float))
            }
            remaining = set(models_list) - existing_models
            if not remaining:
                print(f"  SKIP ({evaluator}): all models computed", flush=True)
                continue
            models_list_run = tuple(remaining)
            print(f"  RESUME ({evaluator}): running {remaining}", flush=True)
        else:
            models_list_run = models_list

        print(f"\n  Evaluating: {evaluator} with {models_list_run}", flush=True)
        t0 = _time.time()

        try:
            model_df, y, feature_cols, c_types, a_types = _load_matrix_and_labels(mf)
            X = model_df[feature_cols].fillna(model_df[feature_cols].median()).values

            results, fitted = gpu_models(
                X,
                y,
                feature_names=feature_cols,
                cancer_types=c_types,
                assays=a_types,
                n_folds=cv_folds,
                models=models_list_run,
                device=device,
                finetune=not no_finetune,
                finetune_epochs=finetune_epochs,
                finetune_lr=finetune_lr,
                compute_shap=compute_shap,
                shap_samples=shap_samples,
            )

            # Add sample IDs for multimodal alignment
            if "sample_id" in model_df.columns:
                results["oof_sample_ids"] = model_df["sample_id"].tolist()

            # Merge with existing results if resuming
            if existing_results:
                existing_results.update(results)
                results = existing_results

            _save_results(
                results,
                output,
                f"{evaluator}_model_results.json",
                extra_meta={"evaluator": evaluator, "matrix_path": str(mf)},
            )

            elapsed = _time.time() - t0
            for mn in models_list_run:
                auc_val = results.get(f"auc_{mn}")
                if auc_val is not None:
                    print(f"  {evaluator}/{mn}: AUC={auc_val:.3f}", flush=True)
            print(f"  Completed in {elapsed:.1f}s", flush=True)

        except SystemExit:
            raise
        except Exception as e:
            log.error("eval_gpu_evaluator_failed", evaluator=evaluator, error=str(e))
            print(f"  ERROR ({evaluator}): {e}", flush=True)
            continue

    print("\n=== eval gpu complete ===", flush=True)


# ── eval multimodal (stub — Phase D) ─────────────────────────────────────────


@eval_app.command("multimodal")
def eval_multimodal(
    super_matrix: Path = typer.Option(
        ...,
        "--super-matrix",
        help="Path to super_matrix.parquet",
    ),
    results_dir: Path = typer.Option(
        ...,
        "--results-dir",
        help="Directory with *_model_results.json files",
    ),
    output: Path = typer.Option("output/", help="Output directory"),
    models: str = typer.Option(
        "rf,xgb",
        "--models",
        help="Models for multimodal evaluation",
    ),
    top_k: int = typer.Option(50, "--top-k", help="Top-K features for selection"),
):
    """Cross-evaluator multimodal evaluation on fused super-matrix.

    Reads per-evaluator results JSONs for OOF probabilities and combines
    with the super_matrix for stacking and ablation analysis.

    NOTE: Full implementation in Phase D.
    """
    print("=== kreview eval multimodal ===", flush=True)
    print(f"  --super-matrix : {super_matrix}", flush=True)
    print(f"  --results-dir  : {results_dir}", flush=True)
    print(f"  --output       : {output}", flush=True)
    print(f"  --models       : {models}", flush=True)
    print(f"  --top-k        : {top_k}", flush=True)
    print("", flush=True)
    print("  NOTE: Multimodal evaluation will be implemented in Phase D.", flush=True)
    print("  This command validates inputs and exits.", flush=True)

    if not super_matrix.exists():
        print(f"ERROR: Super-matrix not found: {super_matrix}", flush=True)
        raise typer.Exit(code=1)

    if not results_dir.exists():
        print(f"ERROR: Results directory not found: {results_dir}", flush=True)
        raise typer.Exit(code=1)

    json_files = sorted(results_dir.glob("*_model_results.json"))
    print(f"  Found {len(json_files)} evaluator result files", flush=True)

    print("\n=== eval multimodal (stub) complete ===", flush=True)
