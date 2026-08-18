"""#96 phase 2 — downstream stacking performance per selection method.

Replicates the pipeline's multimodal protocol (selection on the train stacking
matrix, then 10-fold CV stacking models on the selected columns) for each
method's full-train selection, so the two arms differ ONLY in which features
they kept. Reports OOF CV AUC and sens@100spec-healthy per model.

Both arms share whatever optimism the shipped protocol has (selection sees all
of train), so the paired deltas are a fair method comparison and the absolute
numbers are comparable to the shipped stacking results.

Run in the arfs3 venv (sklearn/xgboost only — no arfs/boruta needed here).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

META_COLS = ("_label", "_sample_id", "_sample_label")


def models():
    return {
        "lr": Pipeline(
            [("s", StandardScaler()), ("m", LogisticRegression(max_iter=1000, random_state=42))]
        ),
        "rf": RandomForestClassifier(
            n_estimators=200, max_depth=6, random_state=42, n_jobs=-1
        ),
        "xgb": XGBClassifier(
            n_estimators=100, max_depth=5, eval_metric="logloss",
            random_state=42, verbosity=0, n_jobs=-1,
        ),
    }


def sens_at_100spec_healthy(y, probs, healthy_mask) -> tuple[float, int]:
    if healthy_mask.sum() == 0:
        return float("nan"), 0
    thr = probs[healthy_mask].max()
    pos = y == 1
    return float((probs[pos] > thr).mean()), int(healthy_mask.sum())


def main() -> None:
    vdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    data_dir = vdir.parent
    sm = pd.read_parquet(data_dir / "models" / "multimodal" / "stacking_matrix.parquet")
    y = sm["_label"].to_numpy()
    healthy = (sm["_sample_label"] == "Healthy Normal").to_numpy()
    X_all = sm.drop(columns=[c for c in META_COLS if c in sm.columns])

    out = {}
    for strat_dir in sorted(vdir.iterdir()):
        ft = strat_dir / "full_train.json"
        if not strat_dir.is_dir() or not ft.exists():
            continue
        sel = json.loads(ft.read_text())["selected"]
        X = X_all[sel].to_numpy()
        out[strat_dir.name] = {"n_features": len(sel)}
        cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
        for mname, model in models().items():
            probs = cross_val_predict(model, X, y, cv=cv, method="predict_proba", n_jobs=1)[:, 1]
            auc = roc_auc_score(y, probs)
            sens, n_h = sens_at_100spec_healthy(y, probs, healthy)
            out[strat_dir.name][mname] = {
                "oof_cv_auc": round(float(auc), 4),
                "sens_at_100spec_healthy": round(sens, 4),
                "n_healthy": n_h,
            }
            print(f"[{strat_dir.name}] {mname}: AUC={auc:.4f} sens@100spec-h={sens:.4f} (k={len(sel)})", flush=True)

    (vdir / "downstream_results.json").write_text(json.dumps(out, indent=1))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
