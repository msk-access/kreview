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
- **#80 done** on `fix/nextflow-v26-compat`: `nextflow.config` now parses on Nextflow 24+.
  Fixed the three blockers (try/catch around `includeConfig` → nf-core ternary; 5
  `${manifest.version}` → `params.kreview_version`; `${HOME}` → `env('HOME')`), removed 2
  stale `withName:` selectors left by #55, set `nextflowVersion = '!>=25.04.0'`, added a
  `stub` profile + `stub:` blocks on all 17 processes + `scripts/nextflow_stub_test.sh`,
  wired into CI on a 25.04.6/26.04.6 matrix. Verified locally on 25.04.6, 25.10.6, 26.04.6.

## Previously
- Working **#56** (CI container smoke test) on branch `fix/ci-container-smoke-test`.
- Process (per maintainer): **one branch out of develop at a time**; **CI must be green before merge**.

## Next
1. **#79** — reporting-layer redesign (next).
2. **#61** fail-loud, **#58/#59/#60** Nextflow hardening, **#63** tests.
3. Add `model:` pins + sharpened triggers to the `.agents/skills/*` frontmatters.

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
