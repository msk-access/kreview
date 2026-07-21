---
name: feedback-parallel-paths-one-impl
description: "Never stand up a second code path for work that already has one — the monolithic kreview run and the Gen-1 bulk .nf modules were deleted for this reason; don't reintroduce them."
metadata:
  type: feedback
---

Never create a second implementation of something the pipeline already does. Shared behaviour
lives in one library function that every caller imports — never copy-pasted inline, and never
behind a "convenience" wrapper that quietly re-implements a stage.

**Why:** nearly every recent data-plumbing bug came from fixing one path and forgetting its
twin: sample_labels not propagated (v0.0.28), best_auc/best_model read from wrong keys
(v0.0.27), duplicate random_state (v0.0.27), and the H1 bug where `multimodal_ablation`
dropped only `_label` while `multimodal_single` dropped all three metadata columns — which
silently discarded **every** evaluator's ablation while reporting success. That bug existed
only in the decomposed path, i.e. the one Nextflow actually runs.

**Resolved (2026-07, #55).** The duplication is gone rather than merely documented:
- `multimodal_eval()` became a thin orchestrator over `prep → single → ablation → merge`, so
  there is one multimodal implementation (#77), guarded by `TestMultimodalEntryPointParity`.
- The monolithic `kreview run` (~924 lines), its Nextflow `KREVIEW_RUN` process, and the
  `pipeline_mode` fork were **deleted**. Nextflow multistage is the only way to run the
  pipeline; a guard test asserts `run` cannot be reintroduced.
- The Gen-1 "bulk" `.nf` modules (`eval_cpu`, `eval_gpu`, `select`, `eval_multimodal`) were
  deleted too. They were included by zero workflows and encoded an **older DAG** that ran
  straight off `EXTRACT`, bypassing `SELECT`/`ABLATE` — fossils, not fallbacks. Re-wiring one
  would have produced different, wrong results.

**How to apply:**
1. Before adding a code path, check whether a sibling already does the job (grep the other
   CLI module / `.nf` modules). Extend the shared function instead of forking it.
2. A module on disk that no workflow `include`s is dead — delete it. Leaving it looks like a
   supported alternative and invites someone to re-enable a stale DAG.
3. Derive evaluator/column sets from the authoritative `prep_metadata.json`, not by
   re-deriving from parquet column names with `rsplit("_", 1)`.

See [[feedback-nbdev-source-of-truth]] and [[reference-nextflow-support-policy]].
