# Memory index — kreview

One line per memory, loaded for recall. Four tiers: `user_` (identity/prefs),
`project_` (live state), `reference_` (stable facts), `feedback_` (corrections + why).
Keep this file to index lines only; the content lives in the linked files.

> **This store is COMMITTED to a public repo** — it is symlinked in as the Claude memory
> directory, so writing here publishes. Never record PHI, patient identifiers, or personal
> paths. Enforced by `.gitleaks.toml` and by assertion 5 of `scripts/check_phi_guard.sh`.
>
> **Machine-local facts go in [`private/`](private/README.md)** (gitignored). Routing rule:
> *would this still be true and useful for a teammate on a different machine?* Yes → here.
> No → `private/`. PHI belongs in **neither** — that rule is absolute, not a routing choice.

- [project-kreview-harness.md](project-kreview-harness.md) — the cross-tool agent harness
  layout (AGENTS.md canonical, hooks enforce the review invariants).

- [project-research-roadmap.md](project-research-roadmap.md) — post-v0.0.32 research
  campaign: settled conclusions (modeling saturated, TN-anchored operating points,
  LOD50 4–5% VAF) + open follow-ups; details on issue #121.
- [feedback-isolated-envs-only.md](feedback-isolated-envs-only.md) — every install goes in
  an isolated env (uv/micromamba/mamba/conda); a base-env install broke the `setuptools<81` pin.
- [feedback-nbdev-source-of-truth.md](feedback-nbdev-source-of-truth.md) — never leave
  `kreview/*.py` edited without a matching notebook change; end with `nbdev-export && black` = zero diff (the `-m` forms are no-ops).
- [feedback-parallel-paths-one-impl.md](feedback-parallel-paths-one-impl.md) — monolithic
  and decomposed paths must call one shared function; drift is the top bug source.
- [feedback-terminal-failure-policy.md](feedback-terminal-failure-policy.md) — on terminal
  failure: optional per-evaluator stages degrade AND surface loudly; mandatory stages
  terminate; never silent-drop or silent-substitute.
- [reference-hpc-singularity-gotchas.md](reference-hpc-singularity-gotchas.md) — Singularity
  PATH stripping, read-only /home, CUDA OOM, cache=lenient: the recurring HPC environment traps.
- [reference-iris-config-interaction.md](reference-iris-config-interaction.md) — the nf-core
  iris config sets its own beforeScript/withLabel/errorStrategy; keep kreview env in-script and
  resources in withName (never beforeScript/withLabel) or iris clobbers them.
- [reference-ci-env-repro.md](reference-ci-env-repro.md) — CI-only lint/mypy failures:
  dep-graph edits shift transitively resolved versions (numpy stubs moved the mypy surface);
  reproduce in a python:3.12-slim amd64 container installed exactly as CI.
- [reference-nextflow-support-policy.md](reference-nextflow-support-policy.md) — supports
  Nextflow v25–v26 (floor 25.04.0, enforced); config-syntax rules modern Nextflow enforces;
  smoke-test with `scripts/nextflow_stub_test.sh`, stub run only, no nf-test harness.

## Private (machine-local, gitignored — see `private/README.md`)

Listed here because `MEMORY.md` is the only memory file always loaded; the content stays in
`private/` and is never committed. Keep these lines generic.

- `private/reference-local-nextflow-env.md` — where the Nextflow + JDK 17 conda env lives and
  how to activate it from an agent shell (needed to run the stub test against the v25 floor).
