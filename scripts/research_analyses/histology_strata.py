"""Is the histology detection gap label-tier composition, or detection biology?

Review item 1. The objection: pancreatic "positives" in the 1-5% VAF band may be
Possible ctDNA+ rather than True ctDNA+, so a gap that looks like biology could be
label-tier composition instead. The incidental finding that prompted it — pancreatic
positives in that band having a median of zero IMPACT-confirmed variants — is
incompatible with the True+ definition and deserved the challenge.

This restricts to True+ only and compares histologies **at matched confirmed-variant
count**, because variant count is the confound the objection runs on.

Power discipline: with a median cell of ~15 samples a full histology x stratum grid
would be noise formatted as a table — the same failure as the retinoblastoma odds
ratio the review correctly rejected. Cells below MIN_CELL are reported as
untestable rather than estimated, and the contrasts are pre-specified.

    python3 scripts/research_analyses/histology_strata.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

D = Path.home() / "Downloads" / "v0.0.32_eval"
MIN_CELL = 20
BAND = (0.01, 0.05)

# Pre-specified: the two contrasts already asserted to the reviewer, plus the
# composition check that motivated the objection.
CONTRASTS = [
    ("Non-Small Cell Lung Cancer", "Pancreatic Cancer", "2-3"),
    ("Non-Small Cell Lung Cancer", "Bladder Cancer", "4+"),
    ("Non-Small Cell Lung Cancer", "Pancreatic Cancer", "4+"),
]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


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

    qtn = (
        (m["label"] == "Possible ctDNA−")
        & (m["has_paired_impact"] == True)
        & (m["n_impact_confirmed"] == 0)
    )
    thr = np.sort(m.loc[qtn, "score"])[int(np.ceil(0.98 * qtn.sum())) - 1]
    m["det"] = m["score"] > thr

    band = m[
        (m["max_vaf"] > BAND[0])
        & (m["max_vaf"] <= BAND[1])
        & m["label"].isin(["True ctDNA+", "Possible ctDNA+"])
    ].copy()
    band["vstrat"] = pd.cut(
        band["n_impact_confirmed"],
        [-1, 0, 1, 3, np.inf],
        labels=["0", "1", "2-3", "4+"],
    )
    print(f"98%-spec-TN threshold {thr:.4f} · 1-5% VAF band n={len(band):,}")

    # ── the objection itself: how much does tier composition differ? ──
    print("\n── label-tier composition by histology (the confound under test) ──")
    print(
        f"  {'histology':30s} {'n':>5s} {'True+':>7s} {'median confirmed variants':>26s}"
    )
    comp = []
    for ct, g in sorted(band.groupby("CANCER_TYPE"), key=lambda kv: -len(kv[1]))[:8]:
        t = g[g["label"] == "True ctDNA+"]
        comp.append((ct, len(g), len(t) / len(g)))
        print(
            f"  {ct[:30]:30s} {len(g):5d} {len(t)/len(g):6.1%} "
            f"{g['n_impact_confirmed'].median():25.1f}"
        )

    # ── the answer: matched-stratum contrasts, True+ only ──
    true_pos = band[band["label"] == "True ctDNA+"]
    print("\n── True+ only, matched on confirmed-variant count ──")
    for a, b, strat in CONTRASTS:
        ga = true_pos[(true_pos["CANCER_TYPE"] == a) & (true_pos["vstrat"] == strat)]
        gb = true_pos[(true_pos["CANCER_TYPE"] == b) & (true_pos["vstrat"] == strat)]
        if len(ga) < MIN_CELL or len(gb) < MIN_CELL:
            print(
                f"  {strat:>4s} variants  {a[:28]} vs {b[:28]}: "
                f"UNTESTABLE (n={len(ga)}/{len(gb)}, floor {MIN_CELL})"
            )
            continue
        ka, kb = int(ga["det"].sum()), int(gb["det"].sum())
        la, ha = wilson(ka, len(ga))
        lb_, hb = wilson(kb, len(gb))
        odds, p = fisher_exact([[ka, len(ga) - ka], [kb, len(gb) - kb]])
        sep = "no overlap" if (la > hb or lb_ > ha) else "intervals overlap"
        print(
            f"  {strat:>4s} variants  {a[:26]:26s} {ka:3d}/{len(ga):3d} = {ka/len(ga):5.1%} "
            f"[{la:.1%}, {ha:.1%}]"
        )
        print(
            f"  {'':>4s}            {b[:26]:26s} {kb:3d}/{len(gb):3d} = {kb/len(gb):5.1%} "
            f"[{lb_:.1%}, {hb:.1%}]   OR={odds:.2f} p={p:.3g} · {sep}"
        )

    # ── how many cells the grid would have had to invent ──
    sizes = true_pos.pivot_table(
        index="CANCER_TYPE",
        columns="vstrat",
        values="det",
        aggfunc="size",
        observed=False,
    ).fillna(0)
    tested = int((sizes.values >= MIN_CELL).sum())
    print(
        f"\n  full grid: {tested} of {sizes.size} cells reach n>={MIN_CELL} "
        f"(median cell {int(np.median(sizes.values))}) — reporting the grid as point "
        f"estimates would be mostly noise, so it is not reported"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
