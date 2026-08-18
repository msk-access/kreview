# #96 validation harness — boruta_shap vs grootcv/leshy

Measures selection **stability** (pairwise Jaccard + Nogueira index over 30
patient-grouped subsample draws) and **downstream stacking performance**
(pipeline-protocol 10-fold CV + paired patient-bootstrap CIs) for kreview's
multimodal all-relevant selection strategies, driving the real
`_select_multimodal_features` dispatch. Results: issue #96 (2026-08-17 comment).

The two arms need two environments (BorutaShapPlus pins numpy<=2.0.0, arfs 3.0
needs numpy>=2.0.2 — mutually uninstallable):

```bash
# grootcv / leshy arm — clean venv
python3 -m venv /tmp/arfs3 && /tmp/arfs3/bin/pip install -e . && \
  /tmp/arfs3/bin/pip uninstall -y BorutaShapPlus && \
  /tmp/arfs3/bin/pip install "arfs==3.0.0" "lightgbm>=4"

# boruta_shap arm — the shipped image (native pinned deps)
docker run --rm --platform linux/amd64 --entrypoint python3 \
  -v <outdir>:/data ghcr.io/msk-access/kreview:v0.0.29 \
  /data/grootcv_validation/run_selection_arm.py --data-dir /data --strategy boruta_shap --draws all
```

Order: generate resample indices (see run_selection_arm.py docstring; fixed
seed 96), run each arm, then `analyze_stability.py`, `downstream_eval.py`,
`paired_ci.py`. All outputs are feature names/counts/timings — no sample ids.
