"""VAF-stratified LOD audit at the 98%-spec-TN operating point. Aggregates only."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

D = Path.home() / "Downloads" / "v0.0.32_eval"
lb = pd.read_parquet(D / "labels" / "labels.parquet")
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
stk = json.load(open(D / "models" / "multimodal" / "stacking_tabicl_ft_results.json"))
sm["STACK"] = np.asarray(stk["stacking_tabicl_ft_oof_probs"], float)
sb = pd.read_parquet(D / "scoreboard_combined__all.parquet").set_index("evaluator")
X = sm
for ev in ("FSCGenomewide", "TfbsOnTarget"):
    col = f"{ev}_{sb.loc[ev,'best_model']}"
    X[ev] = sm[col]
m = X[["_sample_id", "STACK", "FSCGenomewide", "TfbsOnTarget"]].merge(
    lb, left_on="_sample_id", right_on="SAMPLE_ID"
)
qtn = (
    (m["label"] == "Possible ctDNA−")
    & (m["has_paired_impact"] == True)
    & (m["n_impact_confirmed"] == 0)
)
pos = m["label"].isin(["True ctDNA+", "Possible ctDNA+"])


def wilson(k, n):
    if n == 0:
        return (np.nan, np.nan)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


BINS = [
    (0, 0.001, "<0.1%"),
    (0.001, 0.005, "0.1–0.5%"),
    (0.005, 0.01, "0.5–1%"),
    (0.01, 0.02, "1–2%"),
    (0.02, 0.05, "2–5%"),
    (0.05, 0.10, "5–10%"),
    (0.10, 0.20, "10–20%"),
    (0.20, 1.01, ">20%"),
]
for score in ("STACK", "FSCGenomewide", "TfbsOnTarget"):
    neg = np.sort(m.loc[qtn, score].to_numpy())
    thr = neg[int(np.ceil(0.98 * len(neg))) - 1]
    det = (m[score] > thr) & pos
    p_ = m[pos]
    no_snv = p_[~(p_["max_vaf"] > 0)]
    print(f"\n── {score} @98%-spec-TN — detection by max VAF bin ──")
    for lo, hi, lab in BINS:
        b = p_[(p_["max_vaf"] > 0) & (p_["max_vaf"] >= lo) & (p_["max_vaf"] < hi)]
        if not len(b):
            continue
        k = int((b[score] > thr).sum())
        ci = wilson(k, len(b))
        print(
            f"   {lab:9s} n={len(b):5d}  det {k/len(b):5.1%} [{ci[0]:.1%},{ci[1]:.1%}]"
        )
    if len(no_snv):
        k = int((no_snv[score] > thr).sum())
        print(f"   no-SNV-VAF (SV/CNA-driven) n={len(no_snv)}  det {k/len(no_snv):.1%}")
    miss = p_[~(p_[score] > thr)]
    if len(miss):
        mv = miss[miss["max_vaf"] > 0]["max_vaf"]
        print(
            f"   misses: {len(miss)} total; {float((mv<0.01).mean()):.0%} of VAF-carrying misses have VAF<1%; median miss VAF {mv.median()*100:.2f}%"
        )
    hi_miss = miss[miss["max_vaf"] >= 0.10]
    if score == "STACK":
        print(
            f"   HIGH-BURDEN misses (VAF>=10%): {len(hi_miss)} — cancer types: "
            f"{hi_miss['CANCER_TYPE'].value_counts().head(4).to_dict()}"
        )
        r, _ = spearmanr(p_[p_["max_vaf"] > 0]["max_vaf"], p_[p_["max_vaf"] > 0][score])
        print(f"   Spearman(score, VAF) among positives: {r:.3f}")
        print("   within-cancer-type detection at 1–5% VAF (top 4 types):")
        band = p_[(p_["max_vaf"] >= 0.01) & (p_["max_vaf"] < 0.05)]
        for ct, g in band.groupby("CANCER_TYPE"):
            if len(g) >= 100:
                print(
                    f"      {ct[:34]:34s} n={len(g):4d} det {float((g[score]>thr).mean()):5.1%}"
                )
