"""Variant-silent flag validation workbook: the 72 flagged unpaired samples,
matched unflagged controls, blinded review sheet + key. LOCAL ONLY (sample ids)."""

import json
from pathlib import Path
import numpy as np
import pandas as pd

D = Path.home() / "Downloads" / "v0.0.32_eval"
lb = pd.read_parquet(D / "labels" / "labels.parquet")
lb["tp"] = lb["SAMPLE_ID"].str.extract(r"-T(\d+)-")[0].astype(float)
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
unp = m[(m["label"] == "Possible ctDNA−") & (m["has_paired_impact"] == False)].copy()
unp["flagged"] = unp["frag_score"] > thr98
first_pos = (
    m[m["label"].isin(["True ctDNA+", "Possible ctDNA+"])]
    .groupby("PATIENT_ID")["tp"]
    .min()
    .rename("first_pos_tp")
)
unp = unp.merge(first_pos, on="PATIENT_ID", how="left")
unp["patient_later_genotype_pos"] = unp["first_pos_tp"].notna() & (
    unp["first_pos_tp"] > unp["tp"]
)

flagged = unp[unp.flagged].copy()
print("flagged unpaired:", len(flagged))

# matched controls: same cancer type, nearest timepoint, unflagged, one per flagged sample
rng = np.random.RandomState(42)
pool = unp[~unp.flagged].copy()
controls = []
for _, r in flagged.iterrows():
    c = pool[
        (pool.CANCER_TYPE == r.CANCER_TYPE)
        & (~pool.SAMPLE_ID.isin([x["SAMPLE_ID"] for x in controls]))
    ]
    if len(c) == 0:
        c = pool[~pool.SAMPLE_ID.isin([x["SAMPLE_ID"] for x in controls])]
    c = c.iloc[(c["tp"] - r.tp).abs().argsort()]
    controls.append(c.iloc[0].to_dict())
controls = pd.DataFrame(controls)
print("matched controls:", len(controls))

cols = [
    "SAMPLE_ID",
    "PATIENT_ID",
    "CANCER_TYPE",
    "CANCER_TYPE_DETAILED",
    "access_version",
    "tp",
    "frag_score",
    "max_vaf",
    "mean_vaf",
    "patient_later_genotype_pos",
]
flagged_out, controls_out = flagged[cols + ["flagged"]], controls[cols + ["flagged"]]

# blinded sheet: both groups shuffled, NO score/flag columns
blind = (
    pd.concat([flagged_out, controls_out], ignore_index=True)
    .sample(frac=1, random_state=7)
    .reset_index(drop=True)
)
key = blind[["SAMPLE_ID", "flagged", "frag_score"]].copy()
blind_cols = [
    "SAMPLE_ID",
    "PATIENT_ID",
    "CANCER_TYPE",
    "CANCER_TYPE_DETAILED",
    "access_version",
    "tp",
]
blind_sheet = blind[blind_cols].copy()
for c in (
    "disease_status_at_draw",
    "imaging_within_90d",
    "tumor_markers",
    "treatment_status",
    "progression_within_12mo",
    "why_unpaired",
    "chart_verdict",
    "notes",
):
    blind_sheet[c] = ""

proto = pd.DataFrame(
    [
        (
            "Purpose",
            "Validate the fragmentomics flag on variant-silent (IMPACT-unpaired) samples: 72 flagged + 72 matched unflagged controls (same cancer type, nearest timepoint), reviewed BLINDED to flag status.",
        ),
        (
            "Step 1 — blinded chart review",
            "For each row in blinded_review: disease status at draw (imaging/RECIST, tumor markers — AFP/HCG for GCT, etc.), treatment status, clinical progression within 12 months, and why the sample is unpaired (no tissue vs failed panel). Fill chart_verdict: evidence-of-disease / no-evidence / indeterminate.",
        ),
        (
            "Step 2 — unblind and score",
            "Only after all verdicts are recorded, join the key sheet. Success criterion: evidence-of-disease rate in flagged vs control (Fisher exact). Flag validated if enrichment is significant and clinically meaningful (target: flagged rate at least 2x control).",
        ),
        (
            "Step 3 — orthogonal assay (optional, on remaining plasma/BAMs)",
            "ichorCNA copy-number tumor fraction runs on the EXISTING BAMs (no new plasma needed) and is the cheapest orthogonal fraction estimate above ~3 percent — recommended for all 144 before or alongside chart review. Deeper targeted sequencing / methylation where material exists.",
        ),
        (
            "Discipline",
            "Do not open the key sheet until Step 2. This file contains identifiers: local/clinical use only, never into the public repo.",
        ),
    ],
    columns=["item", "detail"],
)

xls = Path.home() / "Downloads" / "variant_silent_flag_validation.xlsx"
with pd.ExcelWriter(xls, engine="openpyxl") as w:
    proto.to_excel(w, "protocol", index=False)
    blind_sheet.to_excel(w, "blinded_review", index=False)
    flagged_out.to_excel(w, "flagged_72_unblinded", index=False)
    controls_out.to_excel(w, "controls_72_unblinded", index=False)
    key.to_excel(w, "KEY_do_not_open_first", index=False)
print("wrote", xls)
print("flagged histology:", flagged.CANCER_TYPE.value_counts().head(5).to_dict())
print(
    "flagged already future-genotype+:", int(flagged.patient_later_genotype_pos.sum())
)
