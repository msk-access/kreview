"""Paired patient-bootstrap CIs for the grootcv-vs-boruta downstream deltas."""

import json
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

vdir = Path(__file__).parent
data_dir = vdir.parent
sm = pd.read_parquet(data_dir / "models" / "multimodal" / "stacking_matrix.parquet")
lb = pd.read_parquet(
    data_dir / "labels" / "labels.parquet", columns=["SAMPLE_ID", "PATIENT_ID"]
)
pat = sm[["_sample_id"]].merge(
    lb, left_on="_sample_id", right_on="SAMPLE_ID", how="left"
)
patients = pat["PATIENT_ID"].fillna(pat["_sample_id"]).to_numpy()
y = sm["_label"].to_numpy()
healthy = (sm["_sample_label"] == "Healthy Normal").to_numpy()

sels = {
    s: json.loads((vdir / s / "full_train.json").read_text())["selected"]
    for s in ("boruta_shap", "grootcv")
}
a, b = set(sels["boruta_shap"]), set(sels["grootcv"])
print(
    f"full-train sets: boruta k={len(a)} grootcv k={len(b)} overlap={len(a&b)} jaccard={len(a&b)/len(a|b):.2f}"
)
print("only boruta:", sorted(a - b))
print("only grootcv:", sorted(b - a))

MODELS = {
    "lr": lambda: Pipeline(
        [
            ("s", StandardScaler()),
            ("m", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    ),
    "rf": lambda: RandomForestClassifier(
        n_estimators=200, max_depth=6, random_state=42, n_jobs=-1
    ),
    "xgb": lambda: XGBClassifier(
        n_estimators=100,
        max_depth=5,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
        n_jobs=-1,
    ),
}
cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
probs = {
    s: {
        m: cross_val_predict(
            mk(), sm[sels[s]].to_numpy(), y, cv=cv, method="predict_proba"
        )[:, 1]
        for m, mk in MODELS.items()
    }
    for s in sels
}


def sens100h(yv, pv, hv):
    thr = pv[hv].max()
    return float((pv[yv == 1] > thr).mean())


rng = np.random.RandomState(7)
uniq = np.unique(patients)
pat_rows = {p: np.where(patients == p)[0] for p in uniq}
print(f"\n{'model':4s} {'dAUC':>8s} {'95% CI':>18s} {'dSens100h':>10s} {'95% CI':>18s}")
for m in MODELS:
    d_auc, d_sens = [], []
    for _ in range(500):
        draw = rng.choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate([pat_rows[p] for p in draw])
        yv, hv = y[idx], healthy[idx]
        if len(np.unique(yv)) < 2 or hv.sum() == 0:
            continue
        pg, pb = probs["grootcv"][m][idx], probs["boruta_shap"][m][idx]
        d_auc.append(roc_auc_score(yv, pg) - roc_auc_score(yv, pb))
        d_sens.append(sens100h(yv, pg, hv) - sens100h(yv, pb, hv))
    qa, qs = np.percentile(d_auc, [2.5, 97.5]), np.percentile(d_sens, [2.5, 97.5])
    print(
        f"{m:4s} {np.mean(d_auc):+8.4f} [{qa[0]:+.4f},{qa[1]:+.4f}] {np.mean(d_sens):+10.4f} [{qs[0]:+.4f},{qs[1]:+.4f}]"
    )
