"""Build the ctDNA quantification review workbook + calibration stats.
LOCAL DELIVERABLE: contains sample identifiers -> ~/Downloads only, never the repo."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr
from sklearn.isotonic import IsotonicRegression

D = Path.home() / "Downloads" / "v0.0.32_eval"
lb = pd.read_parquet(D / "labels" / "labels.parquet")
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
stk = json.load(open(D / "models" / "multimodal" / "stacking_tabicl_ft_results.json"))
sm["frag_score"] = np.asarray(stk["stacking_tabicl_ft_oof_probs"], float)
m = sm[["_sample_id", "frag_score"]].merge(
    lb, left_on="_sample_id", right_on="SAMPLE_ID"
)

qtn = (
    (m["label"] == "Possible ctDNA−")
    & (m["has_paired_impact"] == True)
    & (m["n_impact_confirmed"] == 0)
)
tn_scores = np.sort(m.loc[qtn, "frag_score"].to_numpy())
thr98 = tn_scores[int(np.ceil(0.98 * len(tn_scores))) - 1]
m["score_pctl_vs_TN"] = (
    np.searchsorted(tn_scores, m["frag_score"]) / len(tn_scores) * 100
)
m["flag_98spec_TN"] = m["frag_score"] > thr98

# calibration: isotonic score -> VAF on VAF-positive samples
vp = m[m["max_vaf"] > 0]
iso = IsotonicRegression(out_of_bounds="clip").fit(
    vp["frag_score"], np.log10(vp["max_vaf"])
)
m["predicted_vaf_pct"] = np.round(10 ** iso.predict(m["frag_score"]) * 100, 3)
BANDS = [(0, 1, "<1%"), (1, 5, "1-5%"), (5, 10, "5-10%"), (10, 1e9, ">10%")]


def band(v):
    return next(l for lo, hi, l in BANDS if lo <= v < hi)


m["predicted_fraction_band"] = m["predicted_vaf_pct"].map(band)
m["observed_vaf_band"] = np.where(
    m["max_vaf"] > 0, (m["max_vaf"] * 100).map(band), "no-SNV-VAF"
)

# correlation stats for the review doc
sp_all, _ = spearmanr(vp["frag_score"], vp["max_vaf"])
pe_log, _ = pearsonr(iso.predict(vp["frag_score"]), np.log10(vp["max_vaf"]))
print(f"Spearman(score, VAF) all VAF-carrying: {sp_all:.3f} (n={len(vp)})")
for v in ("XS1", "XS2"):
    g = vp[vp.access_version == v]
    s, _ = spearmanr(g["frag_score"], g["max_vaf"])
    print(f"  {v}: Spearman {s:.3f} (n={len(g)})")
print(f"isotonic calibration Pearson r (log10 VAF): {pe_log:.3f}")
agree = m[m["max_vaf"] > 0]
acc = float((agree["predicted_fraction_band"] == agree["observed_vaf_band"]).mean())
adj = float(
    (
        agree.apply(
            lambda r: abs(
                [b[2] for b in BANDS].index(r.predicted_fraction_band)
                - [b[2] for b in BANDS].index(r.observed_vaf_band)
            )
            <= 1,
            axis=1,
        )
    ).mean()
)
print(f"band agreement: exact {acc:.1%}, within-one-band {adj:.1%}")
dec = (
    vp.assign(d=pd.qcut(vp.frag_score, 10, labels=False))
    .groupby("d")["max_vaf"]
    .median()
    * 100
)
print("score-decile -> median VAF%:", [round(x, 2) for x in dec.tolist()])

# discordance queues
m["discord_high_score_low_vaf"] = m["flag_98spec_TN"] & (m["max_vaf"] < 0.01)
m["discord_low_score_high_vaf"] = (m["score_pctl_vs_TN"] < 50) & (m["max_vaf"] >= 0.10)
print(
    "queues: high-score/low-VAF",
    int(m.discord_high_score_low_vaf.sum()),
    "| low-score/high-VAF",
    int(m.discord_low_score_high_vaf.sum()),
)

cols = [
    "SAMPLE_ID",
    "PATIENT_ID",
    "CANCER_TYPE",
    "access_version",
    "GENE_PANEL",
    "label",
    "split",
    "max_vaf",
    "mean_vaf",
    "n_somatic_snvs",
    "n_impact_confirmed",
    "has_paired_impact",
    "has_sv",
    "has_cna",
    "frag_score",
    "score_pctl_vs_TN",
    "flag_98spec_TN",
    "predicted_vaf_pct",
    "predicted_fraction_band",
    "observed_vaf_band",
    "discord_high_score_low_vaf",
    "discord_low_score_high_vaf",
]
out = m[cols].copy()
for c in ("review_status", "reviewer_notes", "orthogonal_evidence"):
    out[c] = ""

dd = pd.DataFrame(
    [
        (
            "SAMPLE_ID / PATIENT_ID",
            "identifiers — this file must stay local; never commit or share outside the clinical team",
        ),
        ("label", "5-tier ctDNA label from the v0.0.32 labeler"),
        (
            "max_vaf / mean_vaf",
            "plasma variant allele fractions from genotyping (fraction, not %); sub-threshold values retained",
        ),
        (
            "n_impact_confirmed",
            "plasma variants confirmed against the paired IMPACT tumor",
        ),
        (
            "frag_score",
            "fragmentomics stacking score (tabicl_ft, out-of-fold — never fit on the row itself)",
        ),
        (
            "score_pctl_vs_TN",
            "score percentile against the 3,508 tumor-informed true negatives",
        ),
        (
            "flag_98spec_TN",
            "score above the 98%-specificity threshold (tumor-informed anchor)",
        ),
        (
            "predicted_vaf_pct",
            "PROVISIONAL isotonic score->VAF calibration (percent); research-grade only",
        ),
        (
            "predicted_fraction_band / observed_vaf_band",
            "<1%, 1-5%, 5-10%, >10% bands from prediction vs genotyping",
        ),
        (
            "discord_high_score_low_vaf",
            "review queue A: fragmentomics says >=~5% fraction, genotyping says <1% — clonal evolution / tissue-unrepresented clone / QC?",
        ),
        (
            "discord_low_score_high_vaf",
            "review queue B: genotyping says >=10% VAF, fragmentomics below TN median — CH-driven VAF? copy-number-inflated VAF? sample quality?",
        ),
        (
            "review_status / reviewer_notes / orthogonal_evidence",
            "for the human reviewer",
        ),
    ],
    columns=["column", "meaning"],
)

xls = Path.home() / "Downloads" / "ctdna_quantification_review.xlsx"
with pd.ExcelWriter(xls, engine="openpyxl") as w:
    dd.to_excel(w, "column_dictionary", index=False)
    out.to_excel(w, "all_samples", index=False)
    out[out.discord_high_score_low_vaf].sort_values(
        "frag_score", ascending=False
    ).to_excel(w, "queueA_frag_high_vaf_low", index=False)
    out[out.discord_low_score_high_vaf].sort_values(
        "max_vaf", ascending=False
    ).to_excel(w, "queueB_vaf_high_frag_low", index=False)
print("wrote", xls, "| rows:", len(out))
