---
name: feedback-terminal-failure-policy
description: "On terminal failure (retries exhausted): optional per-evaluator stages degrade AND surface loudly in the report; mandatory stages terminate. Never silent-drop, never silent-substitute."
metadata:
  type: feedback
---

When a pipeline stage fails **after its retry ladder is exhausted**, the behaviour is decided
by stage criticality, not by whatever `errorStrategy` happened to be inherited (maintainer
decision, 2026-07-21):

- **Mandatory stages** (`KREVIEW_LABEL`, `KREVIEW_FUSE`) → `terminate`. The run cannot produce
  a valid result without them, so aborting is correct. Already pinned this way.
- **Optional per-evaluator stages** (GPU eval, CPU eval, ablation, per-evaluator select) →
  **degrade AND surface loudly**. The pipeline continues so one bad evaluator does not throw
  away a multi-hour 26-evaluator HPC batch, BUT the failure is recorded and rendered as a
  prominent "N evaluators failed: …" manifest in the final report. Continuing is fine; hiding
  is not.

**Why:** this reconciles invariant 3 (fail loud, not to 0.0/empty) with real HPC economics.
The two failure modes that keep biting are the *silent* ones:
- **silent drop** — an evaluator vanishes from results entirely (the #60 `combine(by:0)` inner
  join dropping an evaluator whose ablation was `ignore`d).
- **silent substitute / masked success** — a failure becomes a plausible-looking low number or
  a NaN row (the GPU exit-0 error-JSON rendered as blank metrics; DuckDB `except → empty df`;
  `except → return 0.0`).
Degradation is acceptable *only* when it is visible. "Continue" must always be paired with a
loud, aggregated report of what was dropped or fell back.

**How to apply:**
1. Never let a per-evaluator `errorStrategy='ignore'` silently remove work — pair it with a
   join that keeps the evaluator (`join(remainder:true)` + sentinel) and a logged fallback.
2. On terminal GPU/optional failure, keep the exit-0 channel-closing invariant (see the
   collect() deadlock history, #59) but only *after* the retry ladder has genuinely climbed —
   emit error-JSON and exit 0 on the final attempt, exit non-zero before it.
3. Any error record that reaches the report must be detected and rendered as a failure, not
   merged in as if it were a result.

See [[feedback-parallel-paths-one-impl]] and [[reference-nextflow-support-policy]].
Related issues: #59, #60, #61.
