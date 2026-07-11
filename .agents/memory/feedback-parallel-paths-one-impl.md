---
name: feedback-parallel-paths-one-impl
description: Monolithic (kreview run) and decomposed (select/eval/multimodal) paths must call one shared function — never copy-pasted logic.
metadata:
  type: feedback
---

kreview keeps two ways to run the same pipeline: monolithic `kreview run` and the decomposed
Nextflow subcommands (`select`/`eval cpu|gpu`/`multimodal`). Any behaviour they share must
live in one library function imported by both. Never copy-paste the logic inline.

**Why:** Nearly every recent data-plumbing bug came from fixing one path and forgetting its
twin: sample_labels not propagated (v0.0.28), best_auc/best_model read from wrong keys
(v0.0.27), duplicate random_state (v0.0.27), and the live H1 bug where `multimodal_ablation`
drops only `_label` while `multimodal_single` drops all three metadata columns.

**How to apply:**
1. Before editing an eval/select/multimodal code path, check whether a sibling path does the
   same thing (grep the other CLI module). Fix both, or better, extract a shared helper.
2. The ~60-line per-evaluator CPU/GPU block is duplicated across `cli.py` and `cli_eval.py`
   (3 sites) — extract `_run_evaluator_models(...)` and call it from all three.
3. Derive evaluator/column sets from the authoritative `prep_metadata.json`, not by
   re-deriving from parquet column names with `rsplit("_", 1)`.

See [[feedback-nbdev-source-of-truth]].
