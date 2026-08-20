"""Assay-effect battery: fingerprint, cross-assay generalization, negative-score shift."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from scipy.stats import mannwhitneyu

D = Path.home() / "Downloads" / "v0.0.32_eval"
lb = pd.read_parquet(D / "labels" / "labels.parquet")
rf_ = pd.read_parquet(D / "models" / "multimodal" / "raw_features_matrix.parquet")
m = rf_.merge(lb, left_on="_sample_id", right_on="SAMPLE_ID")
feats = [c for c in m.columns if "__" in c]
X = np.nan_to_num(m[feats].to_numpy(float), nan=0.0)
groups = m["PATIENT_ID"].fillna(m["_sample_id"]).to_numpy()
xs2 = (m["access_version"] == "XS2").to_numpy().astype(int)
ypos = m["label"].isin(["True ctDNA+", "Possible ctDNA+"]).to_numpy().astype(int)
model_mask = (
    m["label"]
    .isin(["True ctDNA+", "Possible ctDNA+", "Possible ctDNA−", "Healthy Normal"])
    .to_numpy()
)
qtn = (
    (m["label"] == "Possible ctDNA−")
    & (m["has_paired_impact"] == True)
    & (m["n_impact_confirmed"] == 0)
).to_numpy()


def mk_rf():
    return RandomForestClassifier(
        n_estimators=300, max_depth=8, random_state=42, n_jobs=-1
    )


def mk_lr():
    return Pipeline(
        [
            ("s", StandardScaler()),
            ("m", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


# 1. fingerprint: features -> assay version (grouped CV)
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
oof = np.full(len(X), np.nan)
for tr, te in cv.split(X, xs2, groups):
    oof[te] = mk_rf().fit(X[tr], xs2[tr]).predict_proba(X[te])[:, 1]
print(
    f"[fingerprint] AUC(features -> assay version, grouped OOF): {roc_auc_score(xs2, oof):.4f}",
    flush=True,
)
imp = mk_rf().fit(X, xs2).feature_importances_
top = sorted(zip(feats, imp), key=lambda kv: -kv[1])[:5]
print(
    "[fingerprint] top assay-discriminating features:",
    [f"{f} ({v:.2f})" for f, v in top],
    flush=True,
)

# 2. cross-assay generalization (disease task)
mask1 = model_mask & (xs2 == 0)
mask2 = model_mask & (xs2 == 1)


def within(mask):
    idx = np.where(mask)[0]
    oo = np.full(len(idx), np.nan)
    for tr, te in cv.split(X[idx], ypos[idx], groups[idx]):
        oo[te] = mk_rf().fit(X[idx][tr], ypos[idx][tr]).predict_proba(X[idx][te])[:, 1]
    return roc_auc_score(ypos[idx], oo)


def cross(tr_mask, te_mask):
    mdl = mk_rf().fit(X[tr_mask], ypos[tr_mask])
    return roc_auc_score(ypos[te_mask], mdl.predict_proba(X[te_mask])[:, 1])


w1, w2 = within(mask1), within(mask2)
c12, c21 = cross(mask1, mask2), cross(mask2, mask1)
print(f"\n[generalization] within-XS1 {w1:.4f} | within-XS2 {w2:.4f}", flush=True)
print(
    f"[generalization] train XS1 -> test XS2: {c12:.4f} (gap {w2-c12:+.4f})", flush=True
)
print(
    f"[generalization] train XS2 -> test XS1: {c21:.4f} (gap {w1-c21:+.4f})", flush=True
)

# 3. negative-score shift at the operating point (stacking OOF, qualified TN)
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
stk = json.load(open(D / "models" / "multimodal" / "stacking_tabicl_ft_results.json"))
sm["score"] = np.asarray(stk["stacking_tabicl_ft_oof_probs"], float)
ms = sm[["_sample_id", "score"]].merge(lb, left_on="_sample_id", right_on="SAMPLE_ID")
q = ms[
    (ms["label"] == "Possible ctDNA−")
    & (ms["has_paired_impact"] == True)
    & (ms["n_impact_confirmed"] == 0)
]
s1, s2 = q[q.access_version == "XS1"]["score"], q[q.access_version == "XS2"]["score"]
u, p = mannwhitneyu(s1, s2)
print(
    f"\n[threshold-shift] qualified-TN stacking scores: XS1 n={len(s1)} median {s1.median():.3f} | XS2 n={len(s2)} median {s2.median():.3f} | MWU p={p:.2e}",
    flush=True,
)
pool = np.sort(q["score"])
thr = pool[int(np.ceil(0.98 * len(pool))) - 1]
print(
    f"[threshold-shift] one global 98%-spec threshold -> realized specificity: XS1 {1-float((s1>thr).mean()):.3f}, XS2 {1-float((s2>thr).mean()):.3f}",
    flush=True,
)
pos_ms = ms[ms["label"].isin(["True ctDNA+", "Possible ctDNA+"])]
for v in ("XS1", "XS2"):
    pv = pos_ms[pos_ms.access_version == v]["score"]
    print(
        f"[threshold-shift] positives flagged at global threshold, {v}: {float((pv>thr).mean()):.1%} (n={len(pv)})",
        flush=True,
    )
