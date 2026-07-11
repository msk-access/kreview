# v0.0.29 Hardening — drafted GitHub issues

Drafted from the 2026-07-11 deep review. To be created on `msk-access/kreview` as one
tracking issue + 12 children after the harness spine lands. Labels in brackets.

Suggested labels to create: `systemic`, `ci`, `nbdev`, `nextflow`, `eval`, `core`, `deps`,
`tests`, `hygiene`, `bug`. Milestone: `v0.0.29 hardening`.

---

## TRACKING: v0.0.29 hardening — end the release-breakage churn  [systemic]

The 0.0.24→0.0.28 releases were dominated by fixing the prior release's breakage. The deep
review traced almost all of it to 5 systemic root causes + 1 live bug. This tracks the fixes.

Root causes: (1) parallel code paths with no shared source of truth; (2) Nextflow HPC
hardening copy-pasted per-module; (3) CI validates the wrong artifact (never runs the
container, no export-sync check, release not gated on tests); (4) broken nbdev contract
(black vs `black_formatting=False`, stale `_modidx.py`); (5) silent-failure masking
(0.0 metrics, empty frames, exit-0 wrappers, always-skip tests).

- [ ] #1 Collapse monolithic layer to thin orchestrators (unifies multimodal; fixes H1 structurally)
- [ ] #2 CI container smoke test + release gating
- [ ] #3 nbdev reconcile + export-sync/coverage gates
- [ ] #4 Nextflow centralized env/resource
- [ ] #5 Extract shared eval helper (subsumed by #1 for the run() copy; still applies to eval_cpu/gpu)
- [ ] #6 GPU exit-0 wrapper defeats retry
- [ ] #7 combine(by:0) silent evaluator drop
- [ ] #8 Fail-loud instead of 0.0/empty masking
- [ ] #9 Deps hygiene
- [ ] #10 Test coverage + un-skip strategy tests
- [ ] #11 Single source of truth for version
- [ ] #12 Untrack manifest.txt

---

## 1. Collapse the monolithic layer to thin orchestrators over one implementation  [eval][systemic]

**Severity: high.** Root cause #1. Two duplications, retired together:

- **Whole-pipeline:** `kreview run` (cli.py:641-1563, ~920 lines) reimplements the pipeline
  inline instead of delegating. Rewrite it as a **thin orchestrator** that calls the same
  shared functions the sub-commands use (`select_features`, a shared eval helper, the unified
  multimodal orchestrator) — zero logic of its own.
- **Within-multimodal:** `multimodal_eval()` (eval_engine.py:4046) is a second implementation
  of the decomposed `multimodal_prep → single → ablation → merge` (source comment at :4388
  says so). It has two callers — `kreview run` (cli.py:1448) and `kreview eval multimodal run`
  (cli_eval.py:1095). Rewrite `kreview eval multimodal run` to orchestrate the decomposed
  stages in-process, then **delete `multimodal_eval()`**. One multimodal implementation
  (the decomposed one), driven two ways (Nextflow scatter + local single-shot).

**H1 is fixed structurally here** (no standalone patch): the surviving decomposed path is
where the metadata-column bug lives — `multimodal_ablation` (eval_engine.py:4831) drops only
`_label`, while `multimodal_single` (:4665-4667) drops all three metadata columns, so the
ablation matrix keeps string columns → object-dtype → `fit()` raises → swallowed at :4916 →
ablation silently empty + a bogus `_sample` evaluator from the `rsplit` at :4877. Fix: drop
all metadata columns (or read the evaluator→columns map from `prep_metadata.json`).

**Also:** flip the Nextflow default `pipeline_mode` from `monolithic` to `multistage` and mark
monolithic mode deprecated (keep `KREVIEW_RUN` as a thin wrapper; multistage is the real
production path). **Verify:** `test_pipeline_parity.py` becomes trivially green (both paths call
the same functions); add a regression test asserting per-evaluator ablation is non-error on a
v0.0.28 matrix.

## 2. Add container smoke test to CI; gate release on tests; build images before PyPI  [ci][systemic]

**Severity: high.** `test.yml` builds the Docker images but never runs anything inside them,
so a container missing `papermill` or with a bad import passes CI and only fails on HPC — the
direct cause of the 0.0.24→0.0.28 chain. Also `release.yml` publishes to PyPI *before* building
the fragile GPU image and has no `needs:` on tests.

**Fix:** (a) add a `docker run kreview:test-cpu kreview report --help` (and a tiny end-to-end
render) smoke step to CI; (b) build both images before the PyPI publish step, or gate publish
on image-build success; (c) add a `needs:`/`workflow_call` so release runs the test suite first.

## 3. Reconcile nbdev: formatting policy + export-sync & coverage gates  [nbdev][systemic]

**Severity: high.** `black_formatting = False` in `settings.ini` fights `black --check .` in
`lint.yml`, so a fresh `nbdev_export` reverts every committed module; `_modidx.py` is ~7 weeks
stale (39 missing symbols incl. the whole `GPUModelCVAdapter` class). CI has no export-sync
check and no coverage floor.

**Fix:** set `black_formatting = True` (so export emits black-clean `.py`), run one reconciling
`nbdev_export` + `nbdev.doclinks` to normalize the tree and regenerate `_modidx.py`; add
`nbdev_export && git diff --exit-code` and `--cov-fail-under=<floor>` to CI; either give
`scoreboard.py`/`feature_cards.py` notebooks or formally exempt them; update CONTRIBUTING to
match reality.

## 4. Centralize Nextflow env + resource ladders into shared labels  [nextflow][systemic]

**Severity: high.** HPC hardening is copy-pasted per module and applied only where a failure
happened. `PYTORCH_CUDA_ALLOC_CONF` is in 1 of 5 GPU modules; `scoreboard.nf:30` still uses a
`python3` heredoc (latent exit-127); `eval_gpu.nf` has zero env hardening; report modules miss
`HOME`/`TMPDIR`/`MPLCONFIGDIR`; resource ladders are duplicated ~10× to out-shout the iris config.

**Fix:** one shared env fragment (`beforeScript` per resource label) + collapse the duplicated
ladders into `withLabel`; apply the OOM/PATH/HOME fixes once, there. Solve the iris override at
config-load ordering rather than re-pinning every field per process.

## 5. Extract shared `_run_evaluator_models` helper (de-dup remaining CLI sites)  [eval][systemic]

**Severity: medium.** The ~60-line per-evaluator CPU/GPU eval block is copy-pasted in
`cli.py` (`run`, ~:1152-1370) and `cli_eval.py` (`eval_cpu` ~:559-681, `eval_gpu` ~:869-1012).
This is where the historical sample_labels / random_state bugs lived. **Fix:** extract one
shared helper returning the results dict incl. oof metadata; call from all sites. Note: #1
removes the `run()` copy (it becomes a thin orchestrator), so after #1 this is the `eval_cpu`
+ `eval_gpu` pair — the helper `run()` delegates to is the same one they use.

## 6. GPU exit-0 wrapper defeats retry/memory ladder  [nextflow]

**Severity: medium.** The GPU "always exit 0 + emit error-JSON" wrapper
(`eval_gpu_single.nf:84-111`, `ablate_gpu_single.nf:58-77`, `multimodal_single.nf:107-128`)
makes the task always succeed, so `errorStrategy='retry'` + the 64→128 GB / partition
escalation never fire for transient CUDA OOM. **Fix:** emit the error-JSON and `exit $CODE`
only when `task.attempt >= maxRetries`; otherwise exit non-zero so the ladder engages.

## 7. `combine(by:0)` silently drops evaluators on ablation ignore  [nextflow]

**Severity: medium.** In `kreview_eval.nf`, ablation runs with `errorStrategy=ignore` and can
`exit 1`; a dropped ablation output makes the `combine(by:0)` inner-join silently remove that
evaluator from both CPU and GPU eval — silent scientific data loss. **Fix:** `join(..,
remainder:true)` with a sentinel, or always emit a valid `NO_BEST_SUBSET` output.

## 8. Fail loud instead of 0.0/empty masking  [core][systemic]

**Severity: medium.** DuckDB reads retry on any exception then return an empty DataFrame
(`core.py:492-515`, `754-786`), so a persistently failing feature silently drops samples with
only a warning; ~6 `return 0.0` sites and 62 broad `except` handlers in `eval_engine.py` let
failures masquerade as low metrics. **Fix:** distinguish transient I/O (retry) from
schema/programming errors (raise); on permanent failure of a required feature, raise; narrow
the excepts around model fitting so an object-dtype matrix (see #1) surfaces.

## 9. Dependency hygiene  [deps]

**Severity: medium.** Unbounded upper version ranges on a stack already burned by NumPy 2.0
(the `np.NaN` shim); `shapiq` unpinned; `[all]` extra excludes `arfs` and `gpu` (so
`kreview[all]` + `--multimodal-strategy leshy` errors); `papermill` in core deps but never
imported (comment is wrong); README's Quarto story contradicts `pyproject`/Dockerfile. **Fix:**
add upper caps / a constraints lock, pin `shapiq`, fix or rename `[all]`, remove/justify
`papermill`, reconcile the README Quarto guidance.

## 10. Test coverage + un-skip multimodal strategy tests  [tests]

**Severity: medium.** Overall coverage 41.8%; `report.py` 0%, `cli.py`/`cli_eval.py` <9%.
Three of four multimodal strategy tests (`boruta_shap`, `leshy`, `grootcv`) always skip in CI
because their deps aren't installed there — "looks protected, isn't." **Fix:** add Typer
`CliRunner` tests for the CLI subcommands and a `report.py` smoke test; add a CI job that
installs `arfs`/BorutaShap so the strategy tests actually run; add an `nf-test -stub-run` for
the eval/label workflows; per-module coverage floor for CLI/report.

## 11. Single source of truth for version  [build]

**Severity: medium.** Version hardcoded in `settings.ini`, `kreview/__init__.py`, and
`nextflow.config:8`, hand-synced; `nextflow.config` pins container tags to `:v${manifest.version}`,
so a lagging manifest pulls a nonexistent image. **Fix:** derive the nextflow version from one
source, or add a CI check that all three literals + the git tag agree.

## 12. Untrack `manifest.txt`  [hygiene]

**Severity: low.** `manifest.txt` is git-tracked despite being gitignored and contains
machine-specific absolute paths. **Fix:** `git rm --cached manifest.txt`.
