"""Cross-evaluator scoreboard aggregation.

Reads all *_model_results.json files from the output directory
and produces a unified ranking table comparing AUC, sensitivity,
and specificity across all evaluators.
"""

from __future__ import annotations
import json
import numpy as np
import pandas as pd
from pathlib import Path
import structlog

log = structlog.get_logger()

__all__ = ["log", "build_scoreboard"]


def build_scoreboard(output_dir: Path) -> pd.DataFrame:
    """Aggregate all evaluator model results into a ranked scoreboard.

    Scans for ``*_model_results.json`` files, extracts key metrics, and
    returns a DataFrame sorted by best AUC descending.

    Args:
        output_dir: Path containing model result JSON files.

    Returns:
        DataFrame with one row per evaluator, sorted by ``best_auc``.
        Empty DataFrame if no results are found.
    """
    records = []
    json_files = sorted(output_dir.glob("*_model_results.json"))

    if not json_files:
        log.warning("scoreboard_no_results", dir=str(output_dir))
        return pd.DataFrame()

    for json_path in json_files:
        evaluator_name = json_path.stem.replace("_model_results", "")
        try:
            with open(json_path) as f:
                data = json.load(f)
        except Exception as e:
            log.warning("scoreboard_read_failed", file=str(json_path), error=str(e))
            continue

        auc_rf = data.get("auc_rf", np.nan)
        auc_lr = data.get("auc_lr", np.nan)
        auc_xgb = data.get("auc_xgb", np.nan)

        # Compute best AUC across all model types (ignoring NaN and None)
        valid_aucs = [
            x
            for x in [auc_rf, auc_lr, auc_xgb]
            if x is not None and not (isinstance(x, float) and np.isnan(x))
        ]
        best_auc = max(valid_aucs) if valid_aucs else np.nan

        # Extract sensitivity/specificity from classification report
        # sensitivity = recall of positive class (1)
        # specificity = recall of negative class (0)
        cr = data.get("rf_classification_report", {})
        sensitivity_rf = np.nan
        specificity_rf = np.nan
        n_samples = np.nan
        n_positive = np.nan
        if isinstance(cr, dict):
            pos_class = cr.get("1", cr.get("1.0", {}))
            neg_class = cr.get("0", cr.get("0.0", {}))
            sensitivity_rf = pos_class.get("recall", np.nan) if pos_class else np.nan
            specificity_rf = neg_class.get("recall", np.nan) if neg_class else np.nan
            weighted = cr.get("weighted avg", {})
            n_samples = weighted.get("support", np.nan) if weighted else np.nan
            n_positive = pos_class.get("support", np.nan) if pos_class else np.nan

        records.append(
            {
                "evaluator": evaluator_name,
                "auc_rf": auc_rf,
                "auc_lr": auc_lr,
                "auc_xgb": auc_xgb,
                "best_auc": best_auc,
                "n_features": len(data.get("top_features", [])),
                "cv_folds": data.get("cv_folds_actual", np.nan),
                "sensitivity_rf": sensitivity_rf,
                "specificity_rf": specificity_rf,
                "optimal_threshold_rf": data.get("rf_optimal_threshold", np.nan),
                "n_samples": n_samples,
                "n_positive": n_positive,
            }
        )

    if not records:
        log.warning("scoreboard_empty_after_parsing", dir=str(output_dir))
        return pd.DataFrame()

    df = pd.DataFrame(records).sort_values("best_auc", ascending=False)
    log.info(
        "scoreboard_built",
        n_evaluators=len(df),
        best_evaluator=df.iloc[0]["evaluator"],
        best_auc=float(df.iloc[0]["best_auc"]),
    )
    return df
