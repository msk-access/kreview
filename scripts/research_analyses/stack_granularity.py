"""Stacking granularity experiment: evaluator x model columns (156, production)
vs best-model-per-evaluator (26) vs per-evaluator mean probability (26).
10-fold OOF protocol matching the pipeline; paired patient-bootstrap CIs."""

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

D = Path.home() / "Downloads" / "v0.0.32_eval"
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
meta = [c for c in ("_label", "_sample_id", "_sample_label") if c in sm.columns]
y = sm["_label"].to_numpy()
healthy = (sm["_sample_label"] == "Healthy Normal").to_numpy()
X = sm.drop(columns=meta)
lb = pd.read_parquet(
    D / "labels" / "labels.parquet", columns=["SAMPLE_ID", "PATIENT_ID"]
)
pt = sm[["_sample_id"]].merge(
    lb, left_on="_sample_id", right_on="SAMPLE_ID", how="left"
)
patients = pt["PATIENT_ID"].fillna(pt["_sample_id"]).to_numpy()

MODEL_SUFFIXES = ("lr", "rf", "xgb", "tabpfn", "tabpfn_ft", "tabicl", "tabicl_ft")


def split_col(c):
    for s in sorted(MODEL_SUFFIXES, key=len, reverse=True):
        if c.endswith("_" + s):
            return c[: -len(s) - 1], s
    return None, None


evals = {}
for c in X.columns:
    e, m = split_col(c)
    if e:
        evals.setdefault(e, {})[m] = c
print(f"{len(evals)} evaluators, {X.shape[1]} columns")

# best model per evaluator from the scoreboard
sb = pd.read_parquet(D / "scoreboard_combined__all.parquet").set_index("evaluator")
best_cols = []
for e, mods in evals.items():
    bm = sb.loc[e, "best_model"] if e in sb.index else None
    best_cols.append(mods.get(bm) or max(mods.values(), key=lambda c: 0))
mean_df = pd.DataFrame(
    {e: X[list(mods.values())].mean(axis=1) for e, mods in evals.items()}
)

ARMS = {
    "A_all156": X.to_numpy(),
    "B_best26": X[best_cols].to_numpy(),
    "C_mean26": mean_df.to_numpy(),
}
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


def sens_at(yv, pv, hv, spec=None):
    if spec is None:  # 100% spec vs healthy
        thr = pv[hv].max()
        return float((pv[yv == 1] > thr).mean())
    neg = np.sort(pv[yv == 0])
    thr = neg[int(np.ceil(spec * len(neg))) - 1]
    return float((pv[yv == 1] > thr).mean())


probs = {}
print(f"{'arm':10s} {'model':4s} {'AUC':>7s} {'sens@95':>8s} {'sens@100h':>10s}")
for arm, Xa in ARMS.items():
    for mn, mk in MODELS.items():
        p = cross_val_predict(mk(), Xa, y, cv=cv, method="predict_proba")[:, 1]
        probs[(arm, mn)] = p
        print(
            f"{arm:10s} {mn:4s} {roc_auc_score(y, p):7.4f} {sens_at(y,p,healthy,0.95):8.3f} {sens_at(y,p,healthy):10.3f}",
            flush=True,
        )

# paired patient bootstrap: B and C vs A
rng = np.random.RandomState(7)
uniq = np.unique(patients)
rows = {p_: np.where(patients == p_)[0] for p_ in uniq}
print("\npaired deltas vs A_all156 (500 patient-bootstrap draws):")
print(
    f"{'cmp':14s} {'model':4s} {'dAUC':>8s} {'95% CI':>19s} {'dSens100h':>10s} {'95% CI':>19s}"
)
for other in ("B_best26", "C_mean26"):
    for mn in MODELS:
        da, ds = [], []
        for _ in range(500):
            draw = rng.choice(uniq, size=len(uniq), replace=True)
            idx = np.concatenate([rows[p_] for p_ in draw])
            yv, hv = y[idx], healthy[idx]
            if len(np.unique(yv)) < 2 or hv.sum() == 0:
                continue
            pa, po = probs[("A_all156", mn)][idx], probs[(other, mn)][idx]
            da.append(roc_auc_score(yv, po) - roc_auc_score(yv, pa))
            ds.append(sens_at(yv, po, hv) - sens_at(yv, pa, hv))
        qa, qs = np.percentile(da, [2.5, 97.5]), np.percentile(ds, [2.5, 97.5])
        print(
            f"{other:14s} {mn:4s} {np.mean(da):+8.4f} [{qa[0]:+.4f},{qa[1]:+.4f}] {np.mean(ds):+10.4f} [{qs[0]:+.4f},{qs[1]:+.4f}]",
            flush=True,
        )
