# CONTINUITY — kreview

**Goal:** Harden kreview against the recurring release-breakage classes surfaced in the
2026-07 deep review, and stand up an enforcing agent harness so the fixes stay fixed.
**Phase:** Harness spine built (Phase 1+2); fixes tracked as GitHub issues, not yet started.

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
- Working **#56** (CI container smoke test) on branch `fix/ci-container-smoke-test`.
- Process (per maintainer): **one branch out of develop at a time**; **CI must be green before merge**.

## Next
1. Finish #56 (smoke-test the built image in CI; build images before PyPI publish in release.yml).
2. **#55** collapse monolithic layer to thin orchestrators (big notebook refactor; keeps
   `kreview run` + `multimodal run` as thin wrappers over ONE impl, deletes `multimodal_eval()`
   + inlined eval block, fixes H1 structurally, flips NF default to multistage) → **#61** fail-loud.
3. **#58/#59/#60** Nextflow (needs a local `nextflow` install or `nf-test` to verify) → **#63** tests.
4. Add `model:` pins + sharpened triggers to the 10 `.agents/skills/*` frontmatters.

## Design decision (monolithic path) — 2026-07-11
Keep `kreview run` and `kreview eval multimodal run` as **thin orchestrators** over a single
shared implementation (not delete them). The target was the duplicated *implementation*, not
the *commands*: once thin (zero logic of their own), there is nothing left to drift, and the
README's local UX is preserved. `multimodal_eval()` and the inlined eval block are deleted as
the duplicates. Nextflow: flip default `pipeline_mode` to `multistage`, deprecate monolithic
mode (keep `KREVIEW_RUN` as a trivial wrapper). H1 is folded into this refactor (no interim patch).

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
- Nextflow verification: no local `nextflow` install — decide whether to install it / add
  `nf-test` for #58/#59/#60, or verify those by review only. — owner: maintainer
