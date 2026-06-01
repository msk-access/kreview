"""Cross-evaluator scoreboard aggregation.

Reads all *_model_results.json files from the output directory
and produces a unified ranking table comparing AUC, sensitivity,
and specificity across all evaluators.
"""

from __future__ import annotations
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
    from kreview.eval_engine import load_all_model_results

    records = []
    all_results = load_all_model_results(output_dir)

    if not all_results:
        log.warning("scoreboard_no_results", dir=str(output_dir))
        return pd.DataFrame()

    for evaluator_name, data in all_results.items():

        # Extract all AUCs dynamically and find the best model
        # Support both flat keys and nested 'stacking' multimodal keys
        all_aucs = {}

        # Pull flat models
        for k, v in data.items():
            if (
                k.startswith("auc_")
                and not k.endswith(("_ci_lower", "_ci_upper"))
                and not k.startswith("auc_delta_")
            ):
                m_id = k.replace("auc_", "")
                if v is not None and not (isinstance(v, float) and np.isnan(v)):
                    all_aucs[m_id] = v

        # Pull multimodal stacking models if present
        if "stacking" in data:
            for k, v in data["stacking"].items():
                if (
                    k.startswith("auc_")
                    and not k.endswith(("_ci_lower", "_ci_upper"))
                    and not k.startswith("auc_delta_")
                ):
                    m_id = k.replace("auc_", "")
                    if v is not None and not (isinstance(v, float) and np.isnan(v)):
                        all_aucs[m_id] = v

        best_auc = np.nan
        best_model = None
        if all_aucs:
            best_model = max(all_aucs, key=all_aucs.get)
            best_auc = all_aucs[best_model]

        # Extract sensitivity/specificity for the BEST model
        cr = {}
        if best_model:
            # Check flat dict
            if f"{best_model}_classification_report" in data:
                cr = data[f"{best_model}_classification_report"]
            # Check stacking dict
            elif (
                "stacking" in data
                and f"{best_model}_classification_report" in data["stacking"]
            ):
                cr = data["stacking"][f"{best_model}_classification_report"]

        sensitivity = np.nan
        specificity = np.nan
        n_samples = np.nan
        n_positive = np.nan

        if isinstance(cr, dict) and cr:
            pos_class = cr.get("1", cr.get("1.0", {}))
            neg_class = cr.get("0", cr.get("0.0", {}))
            sensitivity = pos_class.get("recall", np.nan) if pos_class else np.nan
            specificity = neg_class.get("recall", np.nan) if neg_class else np.nan
            weighted = cr.get("weighted avg", {})
            n_samples = weighted.get("support", np.nan) if weighted else np.nan
            n_positive = pos_class.get("support", np.nan) if pos_class else np.nan

        # Extract selection QC metadata (added in v0.0.9)
        sel_qc = data.get("selection_qc", {})
        n_sel = sel_qc.get("n_selected_union", len(data.get("top_features", [])))
        n_overlap = sel_qc.get("n_overlap_both", 0)

        rec = {
            "evaluator": evaluator_name,
            "best_auc": best_auc,
            "best_model": best_model,
            "n_features": len(data.get("top_features", [])),
            "cv_folds": data.get("cv_folds_actual", np.nan),
            "sensitivity": sensitivity,
            "specificity": specificity,
            "n_samples": n_samples,
            "n_positive": n_positive,
            "selection_method": sel_qc.get("method", "legacy_cohens_d"),
            "n_selected_features": n_sel,
            "selection_overlap_pct": round(n_overlap / max(1, n_sel) * 100, 1),
        }

        # Add all individual AUCs
        for m_id, auc_val in all_aucs.items():
            rec[f"auc_{m_id}"] = auc_val

        records.append(rec)

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
