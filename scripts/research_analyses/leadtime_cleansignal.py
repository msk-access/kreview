"""Part 1: lead-time — does fragmentomics anticipate genotype conversion?
Part 2: clean-signal model — train on True ctDNA+ vs qualified true negatives
only, score every tier. Sample ids parsed in memory only; outputs are counts."""

import json
import re
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
lb["tp"] = lb["SAMPLE_ID"].str.extract(r"-T(\d+)-")[0].astype(float)
lb["is_pos"] = lb["label"].isin(["True ctDNA+", "Possible ctDNA+"])
lb["is_qtn"] = (
    (lb["label"] == "Possible ctDNA−")
    & (lb["has_paired_impact"] == True)
    & (lb["n_impact_confirmed"] == 0)
)

# ── Part 1: lead-time on stacking OOF scores (train split) ──
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
stk = json.load(open(D / "models" / "multimodal" / "stacking_tabicl_ft_results.json"))
sm["score"] = np.asarray(stk["stacking_tabicl_ft_oof_probs"], float)
mm = sm[["_sample_id", "score"]].merge(lb, left_on="_sample_id", right_on="SAMPLE_ID")

first_pos = mm[mm.is_pos].groupby("PATIENT_ID")["tp"].min().rename("first_pos_tp")
mm = mm.merge(first_pos, on="PATIENT_ID", how="left")
neg = mm[mm.is_qtn]
pre_conv = neg[neg["tp"] < neg["first_pos_tp"]]  # negative draw BEFORE a later positive
pre_conv = (
    pre_conv.sort_values("tp").groupby("PATIENT_ID").tail(1)
)  # latest such draw per patient
never = neg[neg["first_pos_tp"].isna()].sort_values("tp").groupby("PATIENT_ID").tail(1)
print(
    f"[lead-time] converters with a prior qualified-negative draw: {len(pre_conv)} patients"
)
print(
    f"[lead-time] never-converters (control, last negative draw):  {len(never)} patients"
)
if len(pre_conv) >= 10:
    u, p = mannwhitneyu(pre_conv["score"], never["score"], alternative="greater")
    auc = u / (len(pre_conv) * len(never))
    thr98 = np.sort(mm[mm.is_qtn]["score"])[int(np.ceil(0.98 * mm.is_qtn.sum())) - 1]
    print(
        f"[lead-time] pre-conversion score median {pre_conv['score'].median():.3f} vs never {never['score'].median():.3f}"
    )
    print(
        f"[lead-time] AUC(pre-conversion vs never) = {auc:.3f}, one-sided p = {p:.2e}"
    )
    print(
        f"[lead-time] flagged at the 98%-spec threshold: {float((pre_conv['score']>thr98).mean()):.1%} of pre-conversion vs {float((never['score']>thr98).mean()):.1%} of never-converters"
    )

# ── Part 2: clean-signal model on 77 raw grootcv features, all 16,218 samples ──
rf_ = pd.read_parquet(D / "models" / "multimodal" / "raw_features_matrix.parquet")
rf_ = rf_.merge(lb, left_on="_sample_id", right_on="SAMPLE_ID")
feats = [c for c in rf_.columns if "__" in c]
X = np.nan_to_num(rf_[feats].to_numpy(float), nan=0.0)
groups = rf_["PATIENT_ID"].fillna(rf_["_sample_id"]).to_numpy()
tier = np.select(
    [
        rf_["label"].eq("True ctDNA+"),
        rf_["label"].eq("Possible ctDNA+"),
        rf_["is_qtn"],
        rf_["label"].eq("Possible ctDNA−") & ~rf_["is_qtn"],
        rf_["label"].eq("Healthy Normal"),
    ],
    ["True+", "Possible+", "QualifiedTN", "UnpairedNeg", "Healthy"],
    default="Other",
)
print("\n[clean] tier counts:", pd.Series(tier).value_counts().to_dict())

clean = np.isin(tier, ["True+", "QualifiedTN"])
yc = (tier == "True+").astype(int)


def grouped_oof(model_fn, mask, ybin):
    idx = np.where(mask)[0]
    oof = np.full(len(X), np.nan)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    for tr, te in cv.split(X[idx], ybin[idx], groups[idx]):
        m = model_fn().fit(X[idx][tr], ybin[idx][tr])
        oof[idx[te]] = m.predict_proba(X[idx][te])[:, 1]
    full = model_fn().fit(X[idx], ybin[idx])
    out = full.predict_proba(X)[:, 1]
    out[idx] = oof[idx]  # in-subset rows use OOF; out-of-subset use full model
    return out


MF = {
    "lr": lambda: Pipeline(
        [
            ("s", StandardScaler()),
            ("m", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    ),
    "rf": lambda: RandomForestClassifier(
        n_estimators=300, max_depth=8, random_state=42, n_jobs=-1
    ),
}
noisy_pos = rf_["is_pos"].to_numpy().astype(int)
noisy_mask = tier != "Other"
for mn, fn in MF.items():
    s_clean = grouped_oof(fn, clean, yc)
    auc_clean = roc_auc_score(yc[clean], s_clean[clean])
    s_noisy = grouped_oof(fn, noisy_mask, noisy_pos)
    auc_noisy = roc_auc_score(noisy_pos[noisy_mask], s_noisy[noisy_mask])
    print(
        f"\n[clean:{mn}] AUC True+ vs QualifiedTN (clean labels, grouped OOF): {auc_clean:.4f}"
        f"   | same features, noisy binary target: {auc_noisy:.4f}"
    )
    qtn_scores = np.sort(s_clean[tier == "QualifiedTN"])
    thr = qtn_scores[int(np.ceil(0.98 * len(qtn_scores))) - 1]
    print(f"[clean:{mn}] tier medians and detection at 98%-spec-TN threshold:")
    for t in ["True+", "Possible+", "QualifiedTN", "UnpairedNeg", "Healthy"]:
        s = s_clean[tier == t]
        print(
            f"   {t:12s} n={len(s):5d} median {np.median(s):.3f}  flagged {float((s>thr).mean()):.1%}"
        )
