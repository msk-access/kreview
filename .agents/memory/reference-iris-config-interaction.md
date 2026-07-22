---
name: reference-iris-config-interaction
description: "The nf-core iris institutional config sets its OWN beforeScript, withLabel resources, errorStrategy and cache — so kreview must keep env in-script and resources in withName, never beforeScript/withLabel."
metadata:
  type: reference
---

The nf-core **iris** institutional config (fetched via the `includeConfig nfcore_custom.config`
ternary on the iris cluster; `raw.githubusercontent.com/nf-core/configs/master/conf/iris.config`)
sets, at process scope:

- **`beforeScript = 'unset R_LIBS; export SINGULARITYENV_TMPDIR=$NXF_SCRATCH; export
  SINGULARITYENV_TMP=$NXF_SCRATCH'`** — real, load-bearing Singularity scratch setup.
- **`withLabel`** resource blocks for `process_low/medium/high/gpu` (dynamic cpus/memory/time)
  and a **dynamic `queue` closure** that can inject a `cpu` partition the account may lack.
- **`errorStrategy = { task.attempt < 4 ? 'retry' : 'ignore' }`** and **`cache = true`**.

Two consequences that constrain how kreview centralizes HPC hardening (#58):

1. **Env exports must stay IN the process `script:` block, never in a kreview `beforeScript`.**
   `beforeScript` is a single, non-additive directive — a kreview `beforeScript` would clobber
   iris's (losing the SINGULARITYENV scratch setup → broken Singularity tmp) or be clobbered by
   it (losing kreview's HOME/TMPDIR/XDG/PYTORCH_CUDA_ALLOC_CONF → the read-only-/home and CUDA
   fragmentation failures return). Centralize env by interpolating one shared config-level
   string into each module's script, not by moving it to `beforeScript`.
2. **Resource ladders must stay in `withName`, never only in `withLabel`.** iris's `withLabel`
   overrides kreview's `withLabel` (later load wins), but `withName` always beats `withLabel`.
   So the per-process `withName` pins (`queue`, `errorStrategy`, `cache = 'lenient'`, the memory
   ladder) are defensive armour against the iris override, not redundant duplication. Dedup them
   by sharing `def` closures referenced from each `withName`, not by demoting them to `withLabel`.

The #58 issue text ("beforeScript per label + collapse ladders into withLabel + solve via
config-load ordering") was written without knowing iris sets its own beforeScript/withLabel;
following it literally would break iris runs. See [[reference-hpc-singularity-gotchas]] and
[[reference-nextflow-support-policy]].
