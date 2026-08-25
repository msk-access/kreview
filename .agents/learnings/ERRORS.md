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

## [ERR-20260825-001] `docker (gpu)` CI build fails at `add-apt-repository ppa:deadsnakes/ppa`
- **What happened:** the GPU image build failed on a pure-Python PR with
  `lazr.restfulclient.errors.ServerError: HTTP Error 500` and `GPGKeyTemporarilyNotFoundError`,
  raised while `add-apt-repository` fetched the deadsnakes PPA signing key from Launchpad.
  The CPU image, lint, both Nextflow stubs and the PHI scan all passed on the same commit.
- **Skill/pipeline involved:** none — the `docker (gpu)` job is **build-only** (no tests run
  inside it), and the failing step is the Dockerfile's apt layer, before any kreview code is
  installed. The diff touched only `report_data`, the report template and tests.
- **Environment fix:** wait and re-run. The error class names itself *Temporarily*; Launchpad's
  API had returned 500. Nothing in the repository can prevent it while the GPU stage depends on
  a third-party PPA at build time.
- **How to tell it apart from a real bug:** the traceback is inside `add-apt-repository` /
  `lazr`, the failing layer is `#14` (the apt layer), and the CPU image — which shares the
  builder stage and installs the same wheel — passes on the same commit.
- **Standing weakness worth fixing separately:** the GPU stage runs on
  `nvidia/cuda:12.4.1-runtime-ubuntu22.04`, whose distro python is 3.10, so every GPU build
  reaches out to deadsnakes for 3.12. A CUDA base on Ubuntu 24.04 ships 3.12 natively and would
  remove this external dependency from the release container's build path.
- **Date:** 2026-08-25

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
