"""Re-anchor operating points on tumor-informed true negatives (IMPACT-paired,
zero confirmed variants) vs the 55-donor healthy anchor. Patient-bootstrap CIs
cover BOTH threshold and sensitivity uncertainty. Counts only."""

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
healthy = (m["_sample_label"] == "Healthy Normal").to_numpy()
tn = (
    (m["label"] == "Possible ctDNA−")
    & (m["has_paired_impact"] == True)
    & (m["n_impact_confirmed"] == 0)
).to_numpy()
patients = m["PATIENT_ID"].fillna(m["_sample_id"]).to_numpy()
print(
    f"train rows {len(m)}: positives {int(pos.sum())}, healthy {int(healthy.sum())}, qualified TN {int(tn.sum())}"
)

X = sm.drop(
    columns=[c for c in ("_label", "_sample_id", "_sample_label") if c in sm.columns]
)
sb = pd.read_parquet(D / "scoreboard_combined__all.parquet").sort_values(
    "best_auc", ascending=False
)
scores = {}
for _, r in sb.head(6).iterrows():
    col = f"{r['evaluator']}_{r['best_model']}"
    if col in X.columns:
        scores[r["evaluator"]] = X[col].to_numpy()
for f in sorted((D / "models" / "multimodal").glob("stacking_*_results.json")):
    d = json.load(open(f))
    mn = f.stem.replace("stacking_", "").replace("_results", "")
    p = d.get(f"stacking_{mn}_oof_probs")
    if p and len(p) == len(y):
        scores[f"STACK[{mn}]"] = np.asarray(p, float)


def sens(p, pool_mask, spec):
    neg = np.sort(p[pool_mask])
    thr = (
        neg[-1]
        if spec >= 1.0
        else neg[min(int(np.ceil(spec * len(neg))) - 1, len(neg) - 1)]
    )
    return float((p[pos] > thr).mean())


rng = np.random.RandomState(11)
uniq = np.unique(patients)
rows = {q: np.where(patients == q)[0] for q in uniq}


def boot_ci(p, pool_mask, spec, n=300):
    vals = []
    for _ in range(n):
        idx = np.concatenate(
            [rows[q] for q in rng.choice(uniq, size=len(uniq), replace=True)]
        )
        pm, ym = pool_mask[idx], y[idx] == 1
        if pm.sum() < 5 or ym.sum() < 5:
            continue
        neg = np.sort(p[idx][pm])
        thr = (
            neg[-1]
            if spec >= 1.0
            else neg[min(int(np.ceil(spec * len(neg))) - 1, len(neg) - 1)]
        )
        vals.append(float((p[idx][ym] > thr).mean()))
    return np.percentile(vals, [2.5, 97.5])


print(
    f"\n{'score':22s} {'H:s@100':>8s} {'H 95% CI':>15s} {'TN:s@100':>9s} {'TN 95% CI':>15s} {'TN:s@99':>8s} {'TN:s@98':>8s}"
)
for name, p in scores.items():
    h100 = sens(p, healthy, 1.0)
    hci = boot_ci(p, healthy, 1.0)
    t100 = sens(p, tn, 1.0)
    tci = boot_ci(p, tn, 1.0)
    t99 = sens(p, tn, 0.99)
    t98 = sens(p, tn, 0.98)
    print(
        f"{name:22s} {h100:8.3f} [{hci[0]:.3f},{hci[1]:.3f}] {t100:9.3f} [{tci[0]:.3f},{tci[1]:.3f}] {t99:8.3f} {t98:8.3f}",
        flush=True,
    )
