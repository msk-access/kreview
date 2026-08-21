"""Does the sample-level inner CV inflate the headline?

The train/test holdout is patient-grouped (`StratifiedGroupKFold` on PATIENT_ID,
#101), but the inner CV that produces the out-of-fold predictions -- and therefore
the headline operating point -- is a plain `StratifiedKFold` over samples. A patient
with several timepoints can be in the training folds and in the fold being scored.

This re-runs the identical data and models under both schemes and reports the delta,
with a paired patient-level bootstrap on the difference. Aggregates only; no ids.

    python3 scripts/research_analyses/grouped_cv_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import (
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_val_predict,
)

D = Path.home() / "Downloads" / "v0.0.32_eval"
SEED, FOLDS, BOOT = 42, 5, 500
rng = np.random.default_rng(SEED)


def models() -> dict:
    """Production CPU model settings (kreview/eval_engine.py)."""
    out = {
        "rf": lambda: RandomForestClassifier(
            n_estimators=500,
            max_depth=8,
            class_weight="balanced",
            random_state=SEED,
            n_jobs=-1,
        )
    }
    try:
        from xgboost import XGBClassifier

        out["xgb"] = lambda: XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            scale_pos_weight=1.0,
            eval_metric="logloss",
            random_state=SEED,
            n_jobs=-1,
            verbosity=0,
        )
    except ImportError:
        print("  (xgboost unavailable — rf only)")
    return out


def sens_at_spec(
    y: np.ndarray, p: np.ndarray, tn: np.ndarray, spec: float = 0.98
) -> float:
    """Sensitivity at a threshold set on the verified true-negative anchor."""
    if tn.sum() < 20 or (y == 1).sum() == 0:
        return float("nan")
    thr = float(np.quantile(p[tn], spec))
    return float((p[y == 1] > thr).mean())


def exposure(groups: np.ndarray, cv, X, y) -> float:
    """Share of scored samples whose patient also appears in their training folds."""
    leaked = 0
    for tr, te in cv.split(X, y, groups):
        leaked += int(np.isin(groups[te], np.unique(groups[tr])).sum())
    return leaked / len(y)


def paired_bootstrap(y, a, b, patients, tn) -> tuple:
    """Patient-resampled CI for (grouped - ungrouped), both metrics."""
    uniq = np.unique(patients)
    idx_by_patient = {p: np.flatnonzero(patients == p) for p in uniq}
    d_auc, d_sens = [], []
    for _ in range(BOOT):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([idx_by_patient[p] for p in pick])
        yy = y[idx]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        d_auc.append(roc_auc_score(yy, b[idx]) - roc_auc_score(yy, a[idx]))
        d_sens.append(
            sens_at_spec(yy, b[idx], tn[idx]) - sens_at_spec(yy, a[idx], tn[idx])
        )
    q = lambda v: (float(np.nanquantile(v, 0.025)), float(np.nanquantile(v, 0.975)))
    return q(d_auc), q(d_sens)


def run(
    name: str, X: pd.DataFrame, y: np.ndarray, patients: np.ndarray, tn: np.ndarray
) -> None:
    n_pat = len(np.unique(patients))
    print(f"\n=== {name} ===")
    print(
        f"  {len(y):,} train samples · {n_pat:,} patients ({len(y)/n_pat:.2f} samples/patient)"
        f" · {int(y.sum()):,} positives · {int(tn.sum()):,} verified TN · {X.shape[1]} features"
    )

    ung = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    grp = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    print(
        f"  same-patient exposure — sample-level CV {exposure(patients, ung, X, y):6.1%}"
        f" · patient-grouped CV {exposure(patients, grp, X, y):6.1%}"
    )

    for mname, factory in models().items():
        p_ung = cross_val_predict(factory(), X, y, cv=ung, method="predict_proba")[:, 1]
        p_grp = cross_val_predict(
            factory(), X, y, cv=grp.split(X, y, patients), method="predict_proba"
        )[:, 1]
        a_ung, a_grp = roc_auc_score(y, p_ung), roc_auc_score(y, p_grp)
        s_ung, s_grp = sens_at_spec(y, p_ung, tn), sens_at_spec(y, p_grp, tn)
        (lo_a, hi_a), (lo_s, hi_s) = paired_bootstrap(y, p_ung, p_grp, patients, tn)
        print(
            f"  {mname:>4}  AUC          {a_ung:.4f} → {a_grp:.4f}   Δ {a_grp - a_ung:+.4f}"
            f"  [{lo_a:+.4f}, {hi_a:+.4f}]"
        )
        print(
            f"        sens@98spec-TN {s_ung:.4f} → {s_grp:.4f}   Δ {s_grp - s_ung:+.4f}"
            f"  [{lo_s:+.4f}, {hi_s:+.4f}]"
        )


def main() -> int:
    lb = pd.read_parquet(D / "labels" / "labels.parquet")
    keep = [
        "SAMPLE_ID",
        "PATIENT_ID",
        "label",
        "has_paired_impact",
        "n_impact_confirmed",
        "split",
    ]

    # arm 1: the primary single evaluator, on its selected feature matrix
    from kreview.core import LABEL_META_COLS

    fm = pd.read_parquet(D / "matrices" / "selected" / "FSCGenomewide_matrix.parquet")
    fm = fm.merge(
        lb[keep], on=["SAMPLE_ID", "PATIENT_ID"], how="left", suffixes=("", "_lb")
    )
    fm = fm[fm["split"] == "train"].reset_index(drop=True)
    feat = [c for c in fm.columns if c not in LABEL_META_COLS and not c.endswith("_lb")]
    y = (
        ((fm["label"] == "True ctDNA+") | (fm["label"] == "Possible ctDNA+"))
        .to_numpy()
        .astype(int)
    )
    tn = (
        (fm["label"] == "Possible ctDNA−")
        & (fm["has_paired_impact"] == True)
        & (fm["n_impact_confirmed"] == 0)
    ).to_numpy()
    pat = fm["PATIENT_ID"].fillna(fm["SAMPLE_ID"]).to_numpy()
    run(
        "FSCGenomewide — primary single evaluator",
        fm[feat].astype(float).fillna(0.0),
        y,
        pat,
        tn,
    )

    # arm 2: the stacking matrix behind the headline multimodal number
    sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
    sm = sm.merge(lb[keep], left_on="_sample_id", right_on="SAMPLE_ID", how="left")
    ys = sm["_label"].to_numpy().astype(int)
    tns = (
        (sm["label"] == "Possible ctDNA−")
        & (sm["has_paired_impact"] == True)
        & (sm["n_impact_confirmed"] == 0)
    ).to_numpy()
    pats = sm["PATIENT_ID"].fillna(sm["_sample_id"]).to_numpy()
    drop = set(keep) | {"_label", "_sample_id", "_sample_label"}
    Xs = sm[[c for c in sm.columns if c not in drop]].astype(float).fillna(0.0)
    run("Stacking — 26 evaluators, CPU meta-learner", Xs, ys, pats, tns)

    print(
        "\nNote: tabicl_ft/tabpfn are GPU-only and cannot run here; this compares CV schemes"
    )
    print(
        "within the CPU model classes on identical data, which is the mechanism question."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
