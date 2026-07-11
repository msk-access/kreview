# Memory index — kreview

One line per memory, loaded for recall. Four tiers: `user_` (identity/prefs),
`project_` (live state), `reference_` (stable facts), `feedback_` (corrections + why).
Keep this file to index lines only; the content lives in the linked files.

- [feedback-nbdev-source-of-truth.md](feedback-nbdev-source-of-truth.md) — never leave
  `kreview/*.py` edited without a matching notebook change; end with `nbdev_export` = zero diff.
- [feedback-parallel-paths-one-impl.md](feedback-parallel-paths-one-impl.md) — monolithic
  and decomposed paths must call one shared function; drift is the top bug source.
- [reference-hpc-singularity-gotchas.md](reference-hpc-singularity-gotchas.md) — Singularity
  PATH stripping, read-only /home, CUDA OOM, cache=lenient: the recurring HPC environment traps.
