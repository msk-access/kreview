"""#96 validation driver — one arm of the boruta_shap vs grootcv/leshy comparison.

Runs kreview's real ``_select_multimodal_features`` dispatch (no reimplementation)
over pre-generated patient-grouped resamples of the v0.0.29 stacking-matrix train
split, recording the selected feature set + wall time per draw.

Designed to run unchanged in BOTH environments:
  - grootcv/leshy arm: local venv with arfs 3.0 (BorutaShapPlus removed)
  - boruta_shap arm:   inside ghcr.io/msk-access/kreview:v0.0.29 (its native deps)

Both arms consume the same resample_indices.json so they see identical draws.
Outputs contain feature names, counts, and timings only — no sample identifiers.

Usage:
  python run_selection_arm.py --data-dir <v0.0.29_eval> --strategy grootcv \
      [--draws 0,1,2 | --draws all] [--full-train]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

META_COLS = ("_label", "_sample_id", "_sample_label")


def load_train(data_dir: Path) -> tuple[pd.DataFrame, np.ndarray]:
    sm = pd.read_parquet(data_dir / "models" / "multimodal" / "stacking_matrix.parquet")
    y = sm["_label"].to_numpy()
    X = sm.drop(columns=[c for c in META_COLS if c in sm.columns])
    return X, y


def run_draw(X, y, idx, strategy: str, out_path: Path) -> dict:
    from kreview.eval_engine import _select_multimodal_features

    Xd = X.iloc[idx].reset_index(drop=True)
    yd = y[idx]
    t0 = time.perf_counter()
    _, selected = _select_multimodal_features(
        Xd, yd, strategy=strategy, random_state=42
    )
    elapsed = time.perf_counter() - t0
    rec = {
        "strategy": strategy,
        "n_rows": int(len(Xd)),
        "n_input_features": int(Xd.shape[1]),
        "n_selected": len(selected),
        "selected": sorted(selected),
        "wall_seconds": round(elapsed, 2),
    }
    out_path.write_text(json.dumps(rec, indent=1))
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument(
        "--strategy", choices=["boruta_shap", "grootcv", "leshy", "mi"], required=True
    )
    ap.add_argument("--draws", default="all", help='"all", or comma list like "0,1,2"')
    ap.add_argument(
        "--full-train",
        action="store_true",
        help="also run on the full train split (for phase 2)",
    )
    args = ap.parse_args()

    vdir = args.data_dir / "grootcv_validation"
    out_dir = vdir / args.strategy
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = json.loads((vdir / "resample_indices.json").read_text())
    X, y = load_train(args.data_dir)
    assert (
        len(X) == spec["n_rows"]
    ), f"matrix rows {len(X)} != indices spec {spec['n_rows']}"

    todo = (
        sorted(spec["draws"], key=int) if args.draws == "all" else args.draws.split(",")
    )
    for b in todo:
        out_path = out_dir / f"draw_{b}.json"
        if out_path.exists():
            print(f"[{args.strategy}] draw {b}: exists, skipping", flush=True)
            continue
        rec = run_draw(X, y, np.asarray(spec["draws"][b]), args.strategy, out_path)
        print(
            f"[{args.strategy}] draw {b}: {rec['n_selected']} features in {rec['wall_seconds']}s",
            flush=True,
        )

    if args.full_train:
        out_path = out_dir / "full_train.json"
        if not out_path.exists():
            rec = run_draw(X, y, np.arange(len(X)), args.strategy, out_path)
            print(
                f"[{args.strategy}] full train: {rec['n_selected']} features in {rec['wall_seconds']}s",
                flush=True,
            )

    print(f"[{args.strategy}] DONE", flush=True)


if __name__ == "__main__":
    main()
