<!--
Environment-failure log. When a failure is EXTERNAL (Singularity PATH stripping, read-only
/home, unbuilt/stale container, CUDA OOM, missing dependency, cluster node/quota), it is NOT
a code or skill bug. Log it here and fix the environment. Do NOT edit code that was never
broken. Newest at top.

Skeleton:
## [ERR-YYYYMMDD-NNN] <one-line: what failed externally>
- **What happened:** <the external failure>
- **Skill/pipeline involved:** <which ran — confirmed NOT at fault>
- **Environment fix:** <what was wrong outside the harness, and what fixed it>
- **Date:** YYYY-MM-DD
-->

## [ERR-20260824-001] GrootCV tests fail locally: `train() got an unexpected keyword argument 'categorical_feature'`
- **What happened:** `tests/test_selection.py::TestMultimodalFeatureSelection::test_grootcv_*`
  (2 tests) fail on a developer machine with a `TypeError` raised from inside LightGBM's
  `train()`. They pass in CI. The same two tests fail identically on a clean `develop`
  checkout, so nothing in the working tree is responsible.
- **Skill/pipeline involved:** GrootCV selection — NOT at fault. The call comes from `arfs`,
  and the failing signature belongs to LightGBM.
- **Environment fix:** the local base environment carried **arfs 2.4.0 against LightGBM 4.7**.
  arfs 2.4 passes `categorical_feature=` to `lgb.train()`, which LightGBM removed; this is the
  exact incompatibility the project's `arfs>=3.0.0` pin exists to prevent (#91 — "3.0: works
  with modern sklearn/lightgbm (2.4 did not)"). CI installs `.[arfs]` and therefore resolves
  3.x. Fix a local checkout with an isolated env — `bash scripts/make_research_env.sh` then
  `pip install -e '.[arfs]'` — rather than editing selection code that was never broken.
- **How to tell it apart from a real bug:** the traceback bottoms out in `lightgbm/engine.py`,
  never in `kreview/`, and `python -c "import arfs; print(arfs.__version__)"` shows < 3.
- **Date:** 2026-08-24

## [ERR-20260622-001] BorutaShap "No module named 'BorutaShapPlus'" on HPC (historical, resolved)
- **What happened:** Multimodal pipeline chain failed on HPC; root cause was the pip package
  `BorutaShapPlus` exposing an importable module named `BorutaShap`, plus a container built
  from a stale state — an environment/packaging issue, not the multimodal code.
- **Skill/pipeline involved:** multimodal_prep + 5 downstream stages — NOT at fault.
- **Environment fix:** correct the import name and rebuild the container from a clean state;
  a CI container smoke-test would have caught it before release.
- **Date:** 2026-06-22 (recorded 2026-07-11 as the canonical example of `environment` cause)
