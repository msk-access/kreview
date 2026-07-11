# CONTINUITY — kreview

**Goal:** Harden kreview against the recurring release-breakage classes surfaced in the
2026-07 deep review, and stand up an enforcing agent harness so the fixes stay fixed.
**Phase:** Harness spine built (Phase 1+2); fixes tracked as GitHub issues, not yet started.

---

## Done
- Deep review of repo + commit history: 5 systemic root causes + 1 live bug (H1). Findings
  in the review summary and drafted issues (`.agents/HARDENING_ISSUES.md`).
- Installed graphify knowledge graph (`graphify-out/`, code-only build).
- Built the cross-tool harness spine (gbcms-style): `AGENTS.md` (canonical) + `CLAUDE.md`
  (`@AGENTS.md` wrapper), `.claude/skills` → `.agents/skills` symlink, enforcement hooks in
  `.claude/hooks/`, learning-loop + memory scaffolding in `.agents/`.

## Now
- Harness Phase 1+2 in place. graphify hook de-noised (advisory, not a per-tool MANDATORY gate).

## Next
1. Create the drafted GitHub issues on `msk-access/kreview` (tracking issue + 12 children).
2. Start fixes in review-priority order: **#1 collapse monolithic layer to thin orchestrators**
   (keeps `kreview run` + `multimodal run` as thin wrappers over ONE implementation, deletes
   `multimodal_eval()` + inlined eval block, fixes H1 structurally, flips NF default to
   multistage) → **CI container smoke test** → **nbdev black-policy reconcile + export-sync gate**.
3. Add `model:` pins + sharpened triggers to the 10 `.agents/skills/*` frontmatters.

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

## Open questions
- Resolve nbdev formatting policy: set `black_formatting = True` in `settings.ini` (so
  `nbdev_export` emits black-clean `.py`) vs. drop `black --check` on generated `.py`.
  Blocks turning on ruff format-on-save for `kreview/*.py`. — owner: maintainer
- Whether `graphify-out/` should be committed or gitignored. — owner: maintainer
