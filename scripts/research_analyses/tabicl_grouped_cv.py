"""The headline arm under both CV schemes (review open item 3).

`grouped_cv_check.py` compared sample-level and patient-grouped inner CV within the
CPU model classes. The headline number comes from TabICL, which that check could not
run -- and in-context learners are the models where same-patient rows in the context
window are the most plausible leakage route, since neighbouring rows are literally
visible at inference.

Runs on a patient-level subsample: patients are sampled whole, so within-patient
multiplicity (and therefore the exposure being tested) is preserved. Sampling
samples instead would destroy the thing under test.

    python3 scripts/research_analyses/tabicl_grouped_cv.py [--n 4000] [--epochs 5] [--zero-shot-only]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold

D = Path.home() / "Downloads" / "v0.0.32_eval"
SEED, FOLDS, BOOT = 42, 5, 300
rng = np.random.default_rng(SEED)


def device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    return "mps" if torch.backends.mps.is_available() else "cpu"


def subsample(patients: np.ndarray, y: np.ndarray, target: int) -> np.ndarray:
    """Whole patients until the sample budget is met -- multiplicity preserved."""
    uniq = rng.permutation(np.unique(patients))
    idx_by_patient = {p: np.flatnonzero(patients == p) for p in uniq}
    keep: list[int] = []
    for p in uniq:
        if len(keep) >= target:
            break
        keep.extend(idx_by_patient[p].tolist())
    sel = np.array(sorted(keep))
    return sel


def exposure(patients: np.ndarray, cv, X, y) -> float:
    leaked = 0
    for tr, te in cv.split(X, y):
        leaked += int(np.isin(patients[te], np.unique(patients[tr])).sum())
    return leaked / len(y)


def oof(make_model, X: np.ndarray, y: np.ndarray, splits) -> np.ndarray:
    """Manual OOF loop: the GPU classifiers are not sklearn-clonable everywhere."""
    p = np.zeros(len(y), float)
    for k, (tr, te) in enumerate(splits, 1):
        t0 = time.time()
        m = make_model()
        m.fit(X[tr], y[tr])
        p[te] = m.predict_proba(X[te])[:, 1]
        print(
            f"      fold {k}/{len(splits)}  {len(tr):,} train → {len(te):,} scored"
            f"  [{time.time()-t0:.0f}s]",
            flush=True,
        )
    return p


def sens_at_spec(y, p, tn, spec=0.98) -> float:
    if tn.sum() < 20:
        return float("nan")
    return float((p[y == 1] > np.quantile(p[tn], spec)).mean())


def paired_delta(y, a, b, patients, tn):
    uniq = np.unique(patients)
    idx = {q: np.flatnonzero(patients == q) for q in uniq}
    da, ds = [], []
    for _ in range(BOOT):
        pick = np.concatenate(
            [idx[q] for q in rng.choice(uniq, len(uniq), replace=True)]
        )
        yy = y[pick]
        if yy.sum() in (0, len(yy)):
            continue
        da.append(roc_auc_score(yy, b[pick]) - roc_auc_score(yy, a[pick]))
        ds.append(
            sens_at_spec(yy, b[pick], tn[pick]) - sens_at_spec(yy, a[pick], tn[pick])
        )

    def ci(v):
        return float(np.nanquantile(v, 0.025)), float(np.nanquantile(v, 0.975))

    return ci(da), ci(ds)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--n", type=int, default=4000, help="sample budget (patients kept whole)"
    )
    ap.add_argument(
        "--epochs", type=int, default=5, help="fine-tune epochs (production uses 50)"
    )
    ap.add_argument("--zero-shot-only", action="store_true")
    args = ap.parse_args()

    dev = device()
    print(f"device: {dev}")

    lb = pd.read_parquet(D / "labels" / "labels.parquet")
    sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
    keep = [
        "SAMPLE_ID",
        "PATIENT_ID",
        "label",
        "has_paired_impact",
        "n_impact_confirmed",
    ]
    m = sm.merge(lb[keep], left_on="_sample_id", right_on="SAMPLE_ID", how="left")

    y_all = m["_label"].to_numpy().astype(int)
    pat_all = m["PATIENT_ID"].fillna(m["_sample_id"]).to_numpy()
    tn_all = (
        (m["label"] == "Possible ctDNA−")
        & (m["has_paired_impact"] == True)
        & (m["n_impact_confirmed"] == 0)
    ).to_numpy()
    drop = set(keep) | {"_label", "_sample_id", "_sample_label"}
    X_all = (
        m[[c for c in m.columns if c not in drop]].astype(float).fillna(0.0).to_numpy()
    )

    sel = subsample(pat_all, y_all, args.n)
    X, y, pat, tn = X_all[sel], y_all[sel], pat_all[sel], tn_all[sel]
    npat = len(np.unique(pat))
    print(
        f"subsample: {len(y):,} samples · {npat:,} patients ({len(y)/npat:.2f}/patient)"
        f" · {int(y.sum()):,} positives · {int(tn.sum()):,} verified TN · {X.shape[1]} features"
    )

    ung_cv = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    grp_cv = StratifiedGroupKFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    ung = list(ung_cv.split(X, y))
    grp = list(grp_cv.split(X, y, pat))
    print(
        f"same-patient exposure — sample-level {exposure(pat, ung_cv, X, y):.1%} · grouped 0.0%"
    )

    from tabicl import FinetunedTabICLClassifier, TabICLClassifier

    arms = [
        ("tabicl (zero-shot)", lambda: TabICLClassifier(random_state=SEED, device=dev))
    ]
    if not args.zero_shot_only:
        arms.append(
            (
                "tabicl_ft (fine-tuned)",
                lambda: FinetunedTabICLClassifier(
                    epochs=args.epochs,
                    learning_rate=1e-5,
                    random_state=SEED,
                    device=dev,
                ),
            )
        )

    for name, factory in arms:
        print(f"\n=== {name} ===")
        print("   sample-level CV")
        p_ung = oof(factory, X, y, ung)
        print("   patient-grouped CV")
        p_grp = oof(factory, X, y, grp)
        a_u, a_g = roc_auc_score(y, p_ung), roc_auc_score(y, p_grp)
        s_u, s_g = sens_at_spec(y, p_ung, tn), sens_at_spec(y, p_grp, tn)
        (la, ha), (ls, hs) = paired_delta(y, p_ung, p_grp, pat, tn)
        print(
            f"   AUC            {a_u:.4f} → {a_g:.4f}   Δ {a_g-a_u:+.4f}  [{la:+.4f}, {ha:+.4f}]"
        )
        print(
            f"   sens@98spec-TN {s_u:.4f} → {s_g:.4f}   Δ {s_g-s_u:+.4f}  [{ls:+.4f}, {hs:+.4f}]"
        )
        np.savez(
            D / f".cache_tabicl_{name.split()[0]}.npz",
            ung=p_ung,
            grp=p_grp,
            y=y,
            tn=tn,
            pat=pat,
        )

    print(
        f"\nSubsample of {len(y):,} of 12,975 train samples; fine-tuning ran "
        f"{args.epochs} epochs against production's 50. Absolute values are therefore not the "
        f"production numbers -- the comparison is within-arm, same data, same settings, "
        f"only the CV scheme differing."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
