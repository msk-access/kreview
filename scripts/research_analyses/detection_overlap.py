"""Detection-set complementarity at 100% healthy specificity (v0.0.32 OOF data).
Counts only — no sample identifiers in any output."""

import json
from pathlib import Path
import numpy as np
import pandas as pd

D = Path.home() / "Downloads" / "v0.0.32_eval"
sm = pd.read_parquet(D / "models" / "multimodal" / "stacking_matrix.parquet")
y = sm["_label"].to_numpy()
healthy = (sm["_sample_label"] == "Healthy Normal").to_numpy()
pos = y == 1
X = sm.drop(
    columns=[c for c in ("_label", "_sample_id", "_sample_label") if c in sm.columns]
)
print(
    f"{int(pos.sum())} positives, {int(healthy.sum())} healthy anchors, {X.shape[1]} evaluator-model columns"
)

SUF = ("lr", "rf", "xgb", "tabpfn", "tabpfn_ft", "tabicl", "tabicl_ft")


def split(c):
    for s in sorted(SUF, key=len, reverse=True):
        if c.endswith("_" + s):
            return c[: -len(s) - 1], s
    return None, None


evals = {}
for c in X.columns:
    e, m = split(c)
    if e:
        evals.setdefault(e, {})[m] = c


def detected(col):
    p = X[col].to_numpy()
    return pos & (p > p[healthy].max())


sb = pd.read_parquet(D / "scoreboard_combined__all.parquet").set_index("evaluator")
best_det = {}
for e, mods in evals.items():
    bm = sb.loc[e, "best_model"] if e in sb.index else None
    col = mods.get(bm) or list(mods.values())[0]
    best_det[e] = detected(col)

M = np.vstack([best_det[e] for e in best_det])  # evaluators x samples
names = list(best_det)
counts = M.sum(1)
cover = M.sum(0)  # per-sample: how many evaluators detect it
n_pos = int(pos.sum())
union = int((cover > 0).sum())
print(
    f"\nUNION of 26 best-model detectors: {union}/{n_pos} positives ({union/n_pos:.1%})"
)
print("coverage histogram (positives detected by k evaluators):")
hist = (
    pd.Series(cover[pos.nonzero()[0] if False else slice(None)])
    .value_counts()
    .sort_index()
)
hist = pd.Series(cover).value_counts().sort_index()
for k, v in hist.items():
    if k == 0:
        print(f"   k=0 (missed by all): {v}")
    elif k <= 5 or k == hist.index.max():
        print(f"   k={k}: {v}")
print(
    f"   (k=6..{hist.index.max()} collapsed: {int(hist[(hist.index>5)&(hist.index<hist.index.max())].sum())})"
)

uni = cover == 1
print("\nunique captures (only that evaluator detects them):")
for i in np.argsort(-(M & uni).sum(1))[:8]:
    u = int((M[i] & uni).sum())
    if u:
        print(f"   {names[i]:26s} detects {int(counts[i]):4d}, unique {u}")

# greedy set cover
sel, covered = [], np.zeros(M.shape[1], bool)
avail = set(range(len(names)))
print("\ngreedy set-cover (marginal new positives per added evaluator):")
for step in range(10):
    gains = {i: int((M[i] & ~covered).sum()) for i in avail}
    i = max(gains, key=gains.get)
    if gains[i] == 0:
        break
    covered |= M[i]
    avail.discard(i)
    sel.append(names[i])
    print(
        f"   {step+1:2d}. {names[i]:26s} +{gains[i]:4d}  cumulative {int(covered.sum()):4d}/{n_pos} ({covered.sum()/n_pos:.1%})"
    )

# model-level within top evaluator: do different models catch different samples?
top = names[int(np.argmax(counts))]
print(f"\nwithin {top}: per-model detected / unique-vs-other-models:")
mods = evals[top]
dm = {m: detected(c) for m, c in mods.items()}
Mm = np.vstack(list(dm.values()))
mnames = list(dm)
cm = Mm.sum(0)
for j, m in enumerate(mnames):
    u = int((Mm[j] & (cm == 1)).sum())
    print(f"   {m:10s} detects {int(Mm[j].sum()):4d}, unique {u}")
print(
    f"   union across {top} models: {int((cm>0).sum())} vs best single model {int(Mm.sum(1).max())}"
)

# stacking detected set vs the union
stk = {}
for f in sorted((D / "models" / "multimodal").glob("stacking_*_results.json")):
    d = json.load(open(f))
    mname = f.stem.replace("stacking_", "").replace("_results", "")
    probs = d.get(f"stacking_{mname}_oof_probs") or d.get("oof_probs")
    if probs and len(probs) == len(y):
        p = np.asarray(probs, float)
        det = pos & (p > p[healthy].max())
        stk[mname] = det
        inter = int((det & (cover > 0)).sum())
        only_stack = int((det & ~(cover > 0)).sum())
        print(
            f"\nstacking[{mname}]: detects {int(det.sum())}/{n_pos} ({det.sum()/n_pos:.1%}) — "
            f"{inter} inside the union, {only_stack} found by NO single evaluator; "
            f"union positives missed by stacking: {int(((cover>0) & ~det).sum())}"
        )
if not stk:
    print(
        "\n(stacking OOF probs not stored in stacking_*_results.json — union comparison at threshold level only)"
    )
