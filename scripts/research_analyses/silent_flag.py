"""Characterize fragmentomics flags among genotype-silent samples. Counts only."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

D = Path.home() / "Downloads" / "v0.0.32_eval"
lb = pd.read_parquet(D / "labels" / "labels.parquet")
lb["tp"] = lb["SAMPLE_ID"].str.extract(r"-T(\d+)-")[0].astype(float)
lb["is_pos"] = lb["label"].isin(["True ctDNA+", "Possible ctDNA+"])
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
stk = json.load(open(D / "models" / "multimodal" / "stacking_tabicl_ft_results.json"))
sm["score"] = np.asarray(stk["stacking_tabicl_ft_oof_probs"], float)
m = sm[["_sample_id", "score"]].merge(lb, left_on="_sample_id", right_on="SAMPLE_ID")

qtn = (
    (m["label"] == "Possible ctDNA−")
    & (m["has_paired_impact"] == True)
    & (m["n_impact_confirmed"] == 0)
)
unp = (m["label"] == "Possible ctDNA−") & (m["has_paired_impact"] == False)
thr = np.sort(m.loc[qtn, "score"])[int(np.ceil(0.98 * qtn.sum())) - 1]
m["flag"] = m["score"] > thr

first_pos = m[m.is_pos].groupby("PATIENT_ID")["tp"].min().rename("first_pos_tp")
m = m.merge(first_pos, on="PATIENT_ID", how="left")
m["future_pos"] = m["first_pos_tp"].notna() & (m["first_pos_tp"] > m["tp"])

for name, mask in (("UNPAIRED negatives", unp), ("PAIRED qualified TN", qtn)):
    g = m[mask]
    f, nf = g[g.flag], g[~g.flag]
    print(f"\n── {name}: n={len(g)}, flagged {len(f)} ({len(f)/len(g):.1%}) ──")
    for colname, col in (
        ("plasma-only n_somatic_snvs>0", (g["n_somatic_snvs"] > 0)),
        ("has_sv", g["has_sv"] == True),
        ("has_cna", g["has_cna"] == True),
        ("future genotype+ (later timepoint)", g["future_pos"]),
    ):
        a = int(col[g.flag].sum())
        b = int(col[~g.flag].sum())
        pa, pb = a / max(len(f), 1), b / max(len(nf), 1)
        odds, p = fisher_exact([[a, len(f) - a], [b, len(nf) - b]])
        print(
            f"   {colname:36s} flagged {pa:6.1%} vs unflagged {pb:6.1%}  OR={odds:5.2f} p={p:.3g}"
        )
    mv_f, mv_nf = (
        f.loc[f["max_vaf"] > 0, "max_vaf"],
        nf.loc[nf["max_vaf"] > 0, "max_vaf"],
    )
    if len(mv_f) >= 5:
        _, p = mannwhitneyu(mv_f, mv_nf, alternative="greater")
        print(
            f"   sub-threshold plasma max_vaf: flagged median {mv_f.median()*100:.3f}% vs {mv_nf.median()*100:.3f}% (one-sided p={p:.3g})"
        )
    print(
        f"   flagged cancer types: {f['CANCER_TYPE'].value_counts().head(4).to_dict()}"
    )
