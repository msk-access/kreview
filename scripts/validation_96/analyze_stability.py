"""#96 stability analysis — pairwise Jaccard + Nogueira index per strategy.

Reads the draw_*.json files produced by run_selection_arm.py and prints a
comparison table. Nogueira et al. (JMLR 2018) stability:

    phi = 1 - mean_f(s_f^2) / (kbar/d * (1 - kbar/d))

where s_f^2 = M/(M-1) * p_f (1 - p_f) over the M draws, p_f = selection
frequency of feature f, d = number of candidate features, kbar = mean
selected-set size. phi = 1 means identical sets every draw; 0 means no better
than random sets of the same size.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np


def load_sets(d: Path) -> list[set[str]]:
    return [
        set(json.loads(f.read_text())["selected"])
        for f in sorted(d.glob("draw_*.json"), key=lambda p: int(p.stem.split("_")[1]))
    ]


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 1.0


def nogueira(sets: list[set[str]], d: int) -> float:
    M = len(sets)
    feats = sorted(set().union(*sets))
    Z = np.array([[f in s for f in feats] for s in sets], dtype=float)
    p = Z.mean(axis=0)
    s2 = M / (M - 1) * p * (1 - p)
    kbar = Z.sum(axis=1).mean()
    denom = (kbar / d) * (1 - kbar / d)
    # features never selected contribute s_f^2 = 0, so summing over observed is exact
    return 1 - (s2.sum() / d) / denom


def main() -> None:
    vdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    spec = json.loads((vdir / "resample_indices.json").read_text())
    strategies = [p.name for p in vdir.iterdir() if p.is_dir() and list(p.glob("draw_*.json"))]

    print(f"{'strategy':12s} {'draws':>5s} {'mean k':>7s} {'jaccard mean±sd':>16s} {'nogueira':>9s} {'mean s/draw':>11s}")
    for strat in sorted(strategies):
        sets = load_sets(vdir / strat)
        recs = [json.loads(f.read_text()) for f in sorted((vdir / strat).glob("draw_*.json"))]
        d = recs[0]["n_input_features"]
        jac = [jaccard(a, b) for a, b in itertools.combinations(sets, 2)]
        walls = [r["wall_seconds"] for r in recs]
        print(
            f"{strat:12s} {len(sets):5d} {np.mean([len(s) for s in sets]):7.1f} "
            f"{np.mean(jac):8.3f}±{np.std(jac):.3f} {nogueira(sets, d):9.3f} {np.mean(walls):11.1f}"
        )

    # selection frequency profile per strategy (top features by consistency)
    for strat in sorted(strategies):
        sets = load_sets(vdir / strat)
        feats = sorted(set().union(*sets))
        freq = sorted(((sum(f in s for s in sets) / len(sets), f) for f in feats), reverse=True)
        always = [f for p, f in freq if p == 1.0]
        print(f"\n[{strat}] {len(always)} features selected in 100% of draws; top 15 by frequency:")
        for p, f in freq[:15]:
            print(f"   {p:5.0%}  {f}")


if __name__ == "__main__":
    main()
