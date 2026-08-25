"""Re-test the depth artifact behind the variant-silent flags (review Check 8).

The reviewer's mechanism: fragmentomics flags among genotype-silent samples are
sequencing noise, so flagged samples should be the shallow ones and their apparent
sub-threshold VAF excess should vanish once depth is held fixed.

The original check used a single depth proxy. This runs it against two independent
coverage measurements, and stratifies within quartiles of each.

NOTE ON TRUE DEPTH: `total_fragments_pf` (#122) is not present in a v0.0.32 output
directory -- that run predates the column, which is populated from krewlyzer QC
files via `kreview label --krewlyzer-dir`. Until a re-label, the measurements here
remain coverage-derived, not library size. Both are real measurements, not
constructions; neither is the unique-fragment count the formal gate requires.

    python3 scripts/research_analyses/depth_recheck.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

D = Path.home() / "Downloads" / "v0.0.32_eval"


def coverage_measures() -> pd.DataFrame:
    """Per-sample coverage measurements available in this output directory."""
    out = None
    fsc = D / "matrices" / "raw" / "FSCGenomewide_matrix.parquet"
    if fsc.exists():
        c = pd.read_parquet(
            fsc, columns=["SAMPLE_ID", "n_covered_bins", "n_total_bins"]
        )
        c["covered_frac"] = c["n_covered_bins"] / c["n_total_bins"].replace(0, np.nan)
        out = c[["SAMPLE_ID", "n_covered_bins", "covered_frac"]]
    gene = D / "matrices" / "raw" / "FSC_gene_matrix.parquet"
    if gene.exists():
        g = pd.read_parquet(gene, columns=["SAMPLE_ID", "global_normalized_depth_cv"])
        # coverage evenness: high CV = ragged coverage, the noise-prone regime
        out = g if out is None else out.merge(g, on="SAMPLE_ID", how="outer")
    return out


def main() -> int:
    lb = pd.read_parquet(D / "labels" / "labels.parquet")
    sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
    stk = json.load(
        open(D / "models" / "multimodal" / "stacking_tabicl_ft_results.json")
    )
    sm["score"] = np.asarray(stk["stacking_tabicl_ft_oof_probs"], float)
    m = sm[["_sample_id", "score"]].merge(
        lb, left_on="_sample_id", right_on="SAMPLE_ID"
    )

    cov = coverage_measures()
    m = m.merge(cov, on="SAMPLE_ID", how="left")

    qtn = (
        (m["label"] == "Possible ctDNA−")
        & (m["has_paired_impact"] == True)
        & (m["n_impact_confirmed"] == 0)
    )
    unp = (m["label"] == "Possible ctDNA−") & (m["has_paired_impact"] == False)
    thr = np.sort(m.loc[qtn, "score"])[int(np.ceil(0.98 * qtn.sum())) - 1]
    m["flag"] = m["score"] > thr
    print(
        f"98%-spec-TN threshold {thr:.4f} · {int(qtn.sum())} qualified TN · "
        f"{int(unp.sum())} unpaired negatives"
    )

    measures = [
        c
        for c in ("n_covered_bins", "covered_frac", "global_normalized_depth_cv")
        if c in m.columns and m[c].notna().any()
    ]
    print(f"coverage measurements available: {measures}\n")

    for gname, mask in (("UNPAIRED negatives", unp), ("PAIRED qualified TN", qtn)):
        g = m[mask]
        print(
            f"── {gname}: n={len(g):,}, flagged {int(g['flag'].sum())} "
            f"({g['flag'].mean():.1%}) ──"
        )

        # 1. direction test: is the flag a shallow-sample artifact?
        for meas in measures:
            a, b = g.loc[g.flag, meas].dropna(), g.loc[~g.flag, meas].dropna()
            if len(a) < 10 or len(b) < 10:
                continue
            _, p = mannwhitneyu(a, b, alternative="two-sided")
            direction = "HIGHER" if a.median() > b.median() else "LOWER"
            verdict = (
                "wrong direction for the noise mechanism"
                if (direction == "HIGHER") == (meas != "global_normalized_depth_cv")
                else "consistent with the noise mechanism"
            )
            print(
                f"   {meas:28s} flagged {a.median():12.4f} vs {b.median():12.4f}"
                f"  {direction:6s} p={p:.3g}  ({verdict})"
            )

        # 2. does the sub-threshold VAF excess survive within coverage strata?
        for meas in measures:
            if g[meas].notna().sum() < 200:
                continue
            q = pd.qcut(g[meas], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
            print(f"   sub-threshold plasma max_vaf within {meas} quartiles:")
            for lvl in [x for x in ("Q1", "Q2", "Q3", "Q4") if x in set(q.dropna())]:
                sub = g[(q == lvl) & (g["max_vaf"] > 0)]
                f_, n_ = sub.loc[sub.flag, "max_vaf"], sub.loc[~sub.flag, "max_vaf"]
                if len(f_) < 5 or len(n_) < 5:
                    print(f"      {lvl}  n_flagged={len(f_):3d} — too few to test")
                    continue
                _, p = mannwhitneyu(f_, n_, alternative="greater")
                star = "*" if p < 0.05 else " "
                print(
                    f"      {lvl}  flagged {f_.median()*100:6.3f}% vs "
                    f"{n_.median()*100:6.3f}%  (n={len(f_):3d}/{len(n_):4d})  "
                    f"one-sided p={p:.3g} {star}"
                )
        print()

    print(
        "A noise mechanism predicts flagged samples are the SHALLOW ones and that the"
    )
    print("VAF excess disappears once coverage is held fixed. Read both blocks above")
    print(
        "against that prediction. True unique-fragment depth still requires a re-label"
    )
    print(
        "with --krewlyzer-dir; this is the strongest test the existing outputs support."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
