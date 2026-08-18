"""n_iter=10 agreement check vs the n_iter=50 baseline (same draws, cutoff=1)."""

import json
import time
from pathlib import Path
import numpy as np
import pandas as pd
from arfs.feature_selection import GrootCV

v = Path.home() / "Downloads" / "v0.0.29_eval"
vdir = v / "grootcv_validation"
out = vdir / "grootcv_niter10"
out.mkdir(exist_ok=True)
spec = json.loads((vdir / "resample_indices.json").read_text())
sm = pd.read_parquet(v / "models" / "multimodal" / "stacking_matrix.parquet")
y_all = sm["_label"].to_numpy()
X_all = sm.drop(columns=["_label", "_sample_id", "_sample_label"])

for b in [str(i) for i in range(10)] + ["full"]:
    p = out / (f"draw_{b}.json" if b != "full" else "full_train.json")
    if p.exists():
        continue
    idx = np.arange(len(X_all)) if b == "full" else np.asarray(spec["draws"][b])
    X, y = X_all.iloc[idx].reset_index(drop=True), y_all[idx]
    t0 = time.perf_counter()
    sel = GrootCV(objective="binary", cutoff=1, n_folds=5, n_iter=10, silent=True)
    sel.fit(X, y)
    selected = sorted(sel.get_feature_names_out())
    p.write_text(
        json.dumps(
            {
                "strategy": "grootcv_niter10",
                "n_rows": int(len(X)),
                "n_input_features": int(X.shape[1]),
                "n_selected": len(selected),
                "selected": selected,
                "wall_seconds": round(time.perf_counter() - t0, 2),
            }
        )
    )
    print(
        f"[niter10] {b}: {len(selected)} in {time.perf_counter()-t0:.0f}s", flush=True
    )
print("DONE", flush=True)
