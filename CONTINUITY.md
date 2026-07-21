# CONTINUITY — kreview

**Goal:** Harden kreview against the recurring release-breakage classes surfaced in the
2026-07 deep review, and stand up an enforcing agent harness so the fixes stay fixed.
**Phase:** Harness enforcing; #55 cleanup landed. Remaining: #80 → #79 → hardening issues.

---

## Done
- Deep review of repo + commit history: 5 systemic root causes + 1 live bug (H1). Drafted
  issues in `.agents/HARDENING_ISSUES.md`.
- Installed graphify knowledge graph (`graphify-out/`, code-only, gitignored).
- Cross-tool harness spine (gbcms-style) — merged to develop (PR #67): `AGENTS.md` canonical +
  `CLAUDE.md` `@AGENTS.md` wrapper, `.claude/skills` → `.agents/skills` symlink, enforcement
  hooks in `.claude/hooks/`, learning-loop + memory in `.agents/`.
- GitHub issues created: tracking **#66** + children **#55–#65**, milestone `v0.0.29 hardening`.
- **Fixes merged to develop (each a CI-green-gated PR):**
  - #65 untrack `manifest.txt` (PR #68)
  - #64 version-consistency CI check (PR #69)
  - #62 deps hygiene — numpy/pandas `<3`, `[all]`+arfs, README Quarto (PR #70)
  - #57 nbdev reconcile — `black_formatting=True` (one-line; review over-stated the drift),
    lint-cleaned the harness files, `reproducibility.py` documented as a 3rd standalone,
    CI export-sync + `--cov-fail-under=38` gates (PR #71)

## Security guard (PHI/PII) — 2026-07-16
- `.gitleaks.toml` adds PHI rules (DMP patient ids, SSN, MRN, DOB) on top of the default
  secret rules; enforced by the pre-push hook and a CI `phi-secret-scan` job.
- `scripts/check_phi_guard.sh` asserts 4 directions (tree clean, every rule fires, placeholder
  allowed, config self-clean). Run it after touching any rule.
- **Two gitleaks blind spots found and closed:** it does not scan commit MESSAGES (the hook
  now scans messages of commits not yet on any remote), and it does not scan its OWN config
  file (assertion 4 covers it — a real id pasted in a comment there would ship unnoticed).
- **Convention:** never write a real identifier into a commit message, PR body, or
  `.gitleaks.toml`. Refer to an offending commit by SHA, never by value.
- Outstanding maintainer decision: a real-looking sample id remains in history (commit
  `0813447d`) and in the message of the commit that redacted it. Scrubbing = history rewrite.

## Now
- **PR-A (#59 + #60) implemented** on `fix/nextflow-fail-loud`, part of the fail-loud sweep.
  Terminal-failure policy recorded (optional stages degrade AND surface loudly; mandatory
  terminate) in `.agents/memory/feedback-terminal-failure-policy.md`.
  - **#59** — GPU eval/ablate/multimodal wrappers now exit non-zero while `task.attempt <=
    task.maxRetries` (climb the 64→256 GB / gpushort→gpu ladder), degrade to error-JSON + exit
    0 only on the terminal attempt (keeps the collect() channel-closing invariant, `698c72e`).
  - **#60** — `combine(by:0)` → `join(by:0, remainder:true)` + `NO_BEST_SUBSET` fallback + loud
    warn on the matrix↔best_subset pairings, so a missing best_subset no longer drops the
    evaluator. Standalone regression test `scripts/test_nextflow_join_dropguard.nf`.
  - Report surfacing — scoreboard gains `status`/`error_detail`, logs degraded evaluators, emits
    a FAILED row instead of dropping on parse error; both `.qmd` templates show status + a
    callout (and their stale `kreview run` text fixed).
  - Verified: full stub test (25.04.6 + 26.04.6, #59/#60 guards), 356 pytest passed / 43.98%
    cov, black/ruff/PHI/version all clean.
- **#80 done** (merged): `nextflow.config` parses on v25–v26; stub test + CI matrix.

## Previously
- Process (per maintainer): **one branch out of develop at a time**; **CI must be green before merge**.

## Next
1. **PR-B (#61)** — Python fail-loud: DuckDB `except→empty` classify transient-vs-schema;
   narrow the 2 masked `return 0.0` excepts (keep the 3 legitimate); correct #61's stale counts.
2. **#79** — reporting-layer redesign.
3. **#58** Nextflow shared labels, **#63** tests.
4. Add `model:` pins + sharpened triggers to the `.agents/skills/*` frontmatters.

## Design decision (monolithic path) — SUPERSEDED 2026-07-21
Originally: keep `kreview run` as a thin orchestrator. **Superseded** once evidence showed the
path was unused (recent Nextflow work touched `run.nf` once vs 9× for `eval_gpu_single`; README
and docs both used multistage; CI never exercised it). It was **deleted** instead, along with
`run.nf`, the `pipeline_mode` fork, and four orphaned bulk `.nf` modules. `kreview eval
multimodal run` is kept as the single-shot multimodal entry point (a thin wrapper over the
decomposed stages, from #77).

---

## Decisions
- Context layout: gbcms cross-tool pattern (AGENTS.md canonical, CLAUDE.md imports it,
  `.claude/skills` symlink) — keeps the existing `.agents/` investment. — 2026-07-11
- Harness scope: spine first (Phases 1+2); defer autonomy layer (SLURM sweep loops,
  nightly heartbeat) to Phase 3. — 2026-07-11
- Issues: draft now, create after the harness spine is in place. — 2026-07-11

## Process decisions — 2026-07-11
- One branch out of develop at a time; CI must be green before merging (poll `gh pr checks --watch`).
- papermill is KEPT (Quarto render-time dep) — the review's "remove papermill" finding was wrong.
- The `.agents/skills/*` are wired (symlinked into `.claude/skills/`) and load as context; the
  `Skill` tool couldn't invoke them only because this session predated the symlink. A fresh
  session makes `/nbdev-patterns` etc. invocable.

## Open questions
- ~~nbdev formatting policy~~ — RESOLVED in #57: `black_formatting = True`.
- ~~`graphify-out/` committed vs gitignored~~ — RESOLVED: gitignored.
- ~~Nextflow verification~~ — RESOLVED in #80: `scripts/nextflow_stub_test.sh` + CI matrix.
  #58/#59/#60 can now be verified by stub run rather than review alone.
- `publishDir` duplicates the output subdirectory (`out/matrices/selected/selected/...`,
  `matrices/fused/fused/`, `matrices/raw/output/`) because the declared output path already
  contains the folder. Cosmetic but confusing; affects real runs too. Surfaced by the stub
  test in #80, filed as #84. — owner: maintainer
