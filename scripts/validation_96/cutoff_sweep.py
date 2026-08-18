"""#96 GrootCV cutoff sweep — same harness, one knob.

Mirrors _select_multimodal_features' preprocessing + GrootCV call exactly,
but with a configurable cutoff (dispatch hardcodes 1). Output-compatible with
analyze_stability.py / downstream_eval.py (strategy dir = grootcv_cutoff<C>).
Higher cutoff => shadow threshold divided by more => MORE features admitted.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from arfs.feature_selection import GrootCV

META_COLS = ("_label", "_sample_id", "_sample_label")

ap = argparse.ArgumentParser()
ap.add_argument("--data-dir", type=Path, required=True)
ap.add_argument("--cutoff", type=float, required=True)
ap.add_argument("--draws", default="0,1,2,3,4,5,6,7,8,9")
ap.add_argument("--full-train", action="store_true")
args = ap.parse_args()

vdir = args.data_dir / "grootcv_validation"
out_dir = vdir / f"grootcv_cutoff{args.cutoff:g}"
out_dir.mkdir(exist_ok=True)
spec = json.loads((vdir / "resample_indices.json").read_text())
sm = pd.read_parquet(
    args.data_dir / "models" / "multimodal" / "stacking_matrix.parquet"
)
y_all = sm["_label"].to_numpy()
X_all = sm.drop(columns=[c for c in META_COLS if c in sm.columns])


def run(idx, out_path):
    X, y = X_all.iloc[idx].reset_index(drop=True), y_all[idx]
    # dispatch preprocessing: NaN-frac drop / impute are no-ops on this matrix; zero-var:
    v = X.var()
    X = X.drop(columns=v[v <= 0].index.tolist())
    t0 = time.perf_counter()
    sel = GrootCV(
        objective="binary", cutoff=args.cutoff, n_folds=5, n_iter=50, silent=True
    )
    sel.fit(X, y)
    selected = sorted(sel.get_feature_names_out())
    rec = {
        "strategy": f"grootcv_cutoff{args.cutoff:g}",
        "n_rows": int(len(X)),
        "n_input_features": int(X.shape[1]),
        "n_selected": len(selected),
        "selected": selected,
        "wall_seconds": round(time.perf_counter() - t0, 2),
    }
    out_path.write_text(json.dumps(rec, indent=1))
    print(
        f"[cutoff={args.cutoff:g}] {out_path.stem}: {len(selected)} features in {rec['wall_seconds']}s",
        flush=True,
    )


for b in args.draws.split(","):
    p = out_dir / f"draw_{b}.json"
    if not p.exists():
        run(np.asarray(spec["draws"][b]), p)
if args.full_train:
    p = out_dir / "full_train.json"
    if not p.exists():
        run(np.arange(len(X_all)), p)
print("DONE", flush=True)
