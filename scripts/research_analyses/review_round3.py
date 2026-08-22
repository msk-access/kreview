"""Reporting-precision items from the consolidated review record.

Covers the four reporting fixes and two of the analysis requests that are
computable against a local v0.0.32 output directory:

  * patient multiplicity, stated correctly (the "1.51 samples/patient" line
    understates how many samples sit in multi-sample patients)
  * the grouped-CV delta rescaled to the subset actually exposed to leakage
  * the resolution floor of the sens@98spec comparison
  * flag counts and Wilson intervals per histology, instead of odds ratios that
    are unstable at small n
  * label-tier composition (True+ vs Possible+) of the 1-5% VAF band by histology

OOF predictions are cached, so re-runs are cheap.

    python3 scripts/research_analyses/review_round3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import (
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_val_predict,
)

D = Path.home() / "Downloads" / "v0.0.32_eval"
# cache beside the data it derives from, never in the repo working tree
CACHE = D / ".cache_review_round3.npz"
SEED, FOLDS, BOOT = 42, 5, 500
rng = np.random.default_rng(SEED)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def load_frames():
    lb = pd.read_parquet(D / "labels" / "labels.parquet")
    sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
    stk = json.load(
        open(D / "models" / "multimodal" / "stacking_tabicl_ft_results.json")
    )
    sm["score"] = np.asarray(stk["stacking_tabicl_ft_oof_probs"], float)
    return lb, sm


def item_11(lb: pd.DataFrame) -> None:
    print("\n=== 11. patient multiplicity, stated correctly ===")
    tr = lb[lb["split"] == "train"]
    per = tr.groupby("PATIENT_ID").size()
    singles = per[per == 1]
    print(
        f"  train: {len(tr):,} samples · {len(per):,} patients · mean {len(tr)/len(per):.2f}"
    )
    print(
        f"  singleton patients      {len(singles):,} ({len(singles)/len(per):.1%} of patients)"
    )
    print(
        f"  samples in singletons   {len(singles):,} ({len(singles)/len(tr):.1%} of samples)"
    )
    print(
        f"  samples in multi-sample {len(tr)-len(singles):,} "
        f"({1 - len(singles)/len(tr):.1%} of samples)  <- the exposable population"
    )
    print(
        f"  largest patient carries {int(per.max())} samples; "
        f"90th pct {int(per.quantile(0.90))}"
    )


def oof_pair(name: str, X: pd.DataFrame, y: np.ndarray, patients: np.ndarray) -> dict:
    """OOF probabilities under both CV schemes, cached."""
    cached = dict(np.load(CACHE, allow_pickle=True)) if CACHE.exists() else {}
    ku, kg = f"{name}_ung", f"{name}_grp"
    if ku in cached and kg in cached:
        return {"ung": cached[ku], "grp": cached[kg]}
    mdl = RandomForestClassifier(
        n_estimators=500,
        max_depth=8,
        class_weight="balanced",
        random_state=SEED,
        n_jobs=-1,
    )
    ung = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    grp = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    p_ung = cross_val_predict(mdl, X, y, cv=ung, method="predict_proba")[:, 1]
    p_grp = cross_val_predict(
        mdl, X, y, cv=grp.split(X, y, patients), method="predict_proba"
    )[:, 1]
    cached[ku], cached[kg] = p_ung, p_grp
    np.savez(CACHE, **cached)
    return {"ung": p_ung, "grp": p_grp}


def item_10_12(sm: pd.DataFrame, lb: pd.DataFrame) -> None:
    print(
        "\n=== 10 + 12. delta rescaled to the exposed subset, and the resolution floor ==="
    )
    keep = [
        "SAMPLE_ID",
        "PATIENT_ID",
        "label",
        "has_paired_impact",
        "n_impact_confirmed",
    ]
    m = sm.merge(lb[keep], left_on="_sample_id", right_on="SAMPLE_ID", how="left")
    y = m["_label"].to_numpy().astype(int)
    pat = m["PATIENT_ID"].fillna(m["_sample_id"]).to_numpy()
    tn = (
        (m["label"] == "Possible ctDNA−")
        & (m["has_paired_impact"] == True)
        & (m["n_impact_confirmed"] == 0)
    ).to_numpy()
    drop = set(keep) | {"_label", "_sample_id", "_sample_label", "score"}
    X = m[[c for c in m.columns if c not in drop]].astype(float).fillna(0.0)

    # which samples could actually leak: patient present in another fold's training set
    ung = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    exposed = np.zeros(len(y), dtype=bool)
    for tr_i, te_i in ung.split(X, y):
        exposed[te_i] = np.isin(pat[te_i], np.unique(pat[tr_i]))
    print(f"  exposed {exposed.sum():,}/{len(y):,} ({exposed.mean():.1%})")

    p = oof_pair("stack_rf", X, y, pat)
    for label, mask in (
        ("all scored samples", np.ones(len(y), bool)),
        ("exposed subset only", exposed),
    ):
        a, b = roc_auc_score(y[mask], p["ung"][mask]), roc_auc_score(
            y[mask], p["grp"][mask]
        )
        d = []
        uniq = np.unique(pat[mask])
        idx = {q: np.flatnonzero(mask & (pat == q)) for q in uniq}
        for _ in range(BOOT):
            pick = np.concatenate(
                [idx[q] for q in rng.choice(uniq, len(uniq), replace=True)]
            )
            if y[pick].sum() in (0, len(pick)):
                continue
            d.append(
                roc_auc_score(y[pick], p["grp"][pick])
                - roc_auc_score(y[pick], p["ung"][pick])
            )
        lo, hi = np.quantile(d, [0.025, 0.975])
        print(
            f"  {label:20s} AUC {a:.4f} → {b:.4f}   Δ {b-a:+.4f}  [{lo:+.4f}, {hi:+.4f}]"
        )

    # resolution floor of the sensitivity comparison, measured rather than assumed
    thr_u = np.quantile(p["ung"][tn], 0.98)
    thr_g = np.quantile(p["grp"][tn], 0.98)
    s_u = (p["ung"][y == 1] > thr_u).mean()
    s_g = (p["grp"][y == 1] > thr_g).mean()
    ds = []
    uniq = np.unique(pat)
    idx = {q: np.flatnonzero(pat == q) for q in uniq}
    for _ in range(BOOT):
        pick = np.concatenate(
            [idx[q] for q in rng.choice(uniq, len(uniq), replace=True)]
        )
        yy, tt = y[pick], tn[pick]
        if tt.sum() < 20 or yy.sum() == 0:
            continue
        a = (p["ung"][pick][yy == 1] > np.quantile(p["ung"][pick][tt], 0.98)).mean()
        b = (p["grp"][pick][yy == 1] > np.quantile(p["grp"][pick][tt], 0.98)).mean()
        ds.append(b - a)
    se = float(np.std(ds, ddof=1))
    print(f"  sens@98spec-TN {s_u:.4f} → {s_g:.4f}  Δ {s_g-s_u:+.4f}")
    print(
        f"  bootstrap SE of that delta {se:.4f} → smallest resolvable shift "
        f"{1.96*se:.4f} (report as 'no shift detectable at this resolution')"
    )


def item_5_1(sm: pd.DataFrame, lb: pd.DataFrame) -> None:
    m = sm[["_sample_id", "score"]].merge(
        lb, left_on="_sample_id", right_on="SAMPLE_ID"
    )
    qtn = (
        (m["label"] == "Possible ctDNA−")
        & (m["has_paired_impact"] == True)
        & (m["n_impact_confirmed"] == 0)
    )
    thr = np.sort(m.loc[qtn, "score"])[int(np.ceil(0.98 * qtn.sum())) - 1]
    m["flag"] = m["score"] > thr
    silent = m[(m["label"] == "Possible ctDNA−")]

    print("\n=== 5. histology flag counts with Wilson intervals (not odds ratios) ===")
    base = silent["flag"].mean()
    print(f"  base flag rate among genotype-silent samples {base:.2%}")
    rows = []
    for ct, g in silent.groupby("CANCER_TYPE"):
        k, n = int(g["flag"].sum()), len(g)
        if n < 20:
            continue
        lo, hi = wilson(k, n)
        rows.append((ct, k, n, k / n, lo, hi, n * base))
    rows.sort(key=lambda r: -r[3])
    print(
        f"  {'histology':34s} {'k/n':>10s} {'rate':>7s} {'95% Wilson':>18s} {'expected':>9s}"
    )
    for ct, k, n, r, lo, hi, exp in rows[:6] + rows[-4:]:
        print(
            f"  {ct[:34]:34s} {f'{k}/{n}':>10s} {r:6.2%} "
            f"[{lo:5.2%}, {hi:5.2%}]  {exp:8.1f}"
        )

    print("\n=== 1. label-tier composition of the 1-5% VAF band, by histology ===")
    band = m[
        (m["max_vaf"] > 0.01)
        & (m["max_vaf"] <= 0.05)
        & m["label"].isin(["True ctDNA+", "Possible ctDNA+"])
    ]
    print(
        f"  band n={len(band):,}  True+ {int((band['label']=='True ctDNA+').sum()):,} "
        f"({(band['label']=='True ctDNA+').mean():.1%})"
    )
    print(
        f"  {'histology':30s} {'n':>5s} {'True+':>7s} {'det(all)':>9s} {'det(True+)':>11s}"
    )
    for ct, g in sorted(band.groupby("CANCER_TYPE"), key=lambda kv: -len(kv[1]))[:8]:
        t = g[g["label"] == "True ctDNA+"]
        det_all = (g["score"] > thr).mean()
        det_true = (t["score"] > thr).mean() if len(t) else float("nan")
        print(
            f"  {ct[:30]:30s} {len(g):5d} {len(t)/len(g):6.1%} {det_all:8.1%} {det_true:10.1%}"
        )


def main() -> int:
    lb, sm = load_frames()
    item_11(lb)
    item_10_12(sm, lb)
    item_5_1(sm, lb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
