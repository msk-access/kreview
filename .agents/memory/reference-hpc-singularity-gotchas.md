---
name: reference-hpc-singularity-gotchas
description: Recurring HPC/Singularity environment traps in the kreview Nextflow pipeline and their standard fixes.
metadata:
  type: reference
---

Standing environment facts for running the kreview Nextflow pipeline on HPC (SLURM +
Singularity). These are `environment`-class issues — fix the wiring, not the code.

- **PATH stripping:** Singularity `env - PATH=$PATH` passes the host PATH, not the container
  PATH. Bare `python3` may be "command not found" (exit 127). Call the `kreview` console
  entrypoint (on `/usr/local/bin` via pip) or use `grep`, not inline `python3`. Note:
  `scoreboard.nf` still uses a `python3` heredoc — latent exit-127.
- **Read-only /home:** export `IPYTHONDIR="$PWD/.ipython"` (and ideally `HOME`, `TMPDIR`,
  `MPLCONFIGDIR`, `XDG_*` to `$PWD/...`) or IPython/Quarto/matplotlib error writing to /home.
- **Quarto EROFS:** Quarto 1.9+ writes a `.quarto/` dir next to the QMD; stage templates to a
  writable `.render_<feat>/` dir before `quarto render`.
- **CUDA OOM on shared nodes:** export `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
  Currently set in only 1 of 5 GPU modules — should be centralized to a shared GPU label.
- **GPFS cache:** pin `cache='lenient'` so the iris institutional config's `cache=true` does
  not break inode hashing.
- **Scheduler minimal env:** cron/SLURM jobs run with a bare PATH; absolute-path critical
  tools. Exit 0 is not proof of success if a failing step was wrapped in try/except.

The right fix for most of these is one shared `beforeScript` per resource label, not a paste
into whichever module last failed. See [[feedback-parallel-paths-one-impl]].
