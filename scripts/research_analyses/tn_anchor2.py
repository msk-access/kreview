"""CIs for the TN-anchored quantile operating points (99/98% spec) + True-ctDNA+-only sensitivity."""

import json
from pathlib import Path
import numpy as np
import pandas as pd

D = Path.home() / "Downloads" / "v0.0.32_eval"
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
lb = pd.read_parquet(D / "labels" / "labels.parquet")
m = sm.merge(
    lb[["SAMPLE_ID", "PATIENT_ID", "label", "has_paired_impact", "n_impact_confirmed"]],
    left_on="_sample_id",
    right_on="SAMPLE_ID",
    how="left",
)
y = m["_label"].to_numpy()
pos = y == 1
true_pos = (m["label"] == "True ctDNA+").to_numpy()
tn = (
    (m["label"] == "Possible ctDNA−")
    & (m["has_paired_impact"] == True)
    & (m["n_impact_confirmed"] == 0)
).to_numpy()
patients = m["PATIENT_ID"].fillna(m["_sample_id"]).to_numpy()

scores = {}
for f in sorted((D / "models" / "multimodal").glob("stacking_*_results.json")):
    d = json.load(open(f))
    mn = f.stem.replace("stacking_", "").replace("_results", "")
    p = d.get(f"stacking_{mn}_oof_probs")
    if p and len(p) == len(y):
        scores[f"STACK[{mn}]"] = np.asarray(p, float)

rng = np.random.RandomState(11)
uniq = np.unique(patients)
rows = {q: np.where(patients == q)[0] for q in uniq}


def run(p, spec, pos_mask, n=300):
    pt = []
    neg = np.sort(p[tn])
    thr = neg[min(int(np.ceil(spec * len(neg))) - 1, len(neg) - 1)]
    point = float((p[pos_mask] > thr).mean())
    for _ in range(n):
        idx = np.concatenate(
            [rows[q] for q in rng.choice(uniq, size=len(uniq), replace=True)]
        )
        tm, ym = tn[idx], pos_mask[idx]
        if tm.sum() < 50 or ym.sum() < 20:
            continue
        negb = np.sort(p[idx][tm])
        t = negb[min(int(np.ceil(spec * len(negb))) - 1, len(negb) - 1)]
        pt.append(float((p[idx][ym] > t).mean()))
    lo, hi = np.percentile(pt, [2.5, 97.5])
    return point, lo, hi


print(
    f"{'score':18s} {'pool':9s} {'s@99':>6s} {'99 CI':>15s} {'s@98':>6s} {'98 CI':>15s}"
)
for name, p in scores.items():
    for pmask, lab in ((pos, "all-pos"), (true_pos, "TruePos")):
        a = run(p, 0.99, pmask)
        b = run(p, 0.98, pmask)
        print(
            f"{name:18s} {lab:9s} {a[0]:6.3f} [{a[1]:.3f},{a[2]:.3f}] {b[0]:6.3f} [{b[1]:.3f},{b[2]:.3f}]",
            flush=True,
        )
