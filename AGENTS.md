# kreview — standing context (canonical, cross-tool)

> Canonical agent rules for this repo. Read by Antigravity, Cursor, Codex, Copilot,
> and (via `CLAUDE.md` import) Claude Code. Every line is read on every turn — keep it
> tight. Depth lives in `.agents/rules/*.md` and is read on demand, not here.

**What this is:** `kreview` — an evaluation engine for cfDNA fragmentomics features for
ctDNA detection (MSKCC / MSK-ACCESS). Labels samples on a 5-tier ctDNA taxonomy, extracts
26 fragmentomics feature families, runs multi-model CV evaluation (CPU + GPU), multimodal
stacking, and Quarto dashboards. Ships as a pip package, CPU/GPU Docker images, and a
Nextflow HPC (SLURM/Singularity) pipeline.

**Architecture:** `nbdev` project. Source of truth is the notebooks in `nbs/`; the
`kreview/*.py` modules are **generated**. Two run modes share one library: monolithic
`kreview run` (single machine) and the decomposed Nextflow DAG (`label → extract → select →
ablate → eval cpu/gpu → fuse → multimodal → report`). Full module map:
`.agents/rules/nbdev-conventions.md`.

## Load-bearing invariants (don't break these)

<!-- protected:start reason="these encode the recurring-bug root causes; do not weaken without review" -->
1. **nbdev is the source of truth — and the commands are not the obvious ones.**
   `python3 -m nbdev.export` and `python3 -m nbdev.doclinks` are **silent no-ops** (exit 0,
   write nothing); `nbdev_export`/`nbdev_test` (underscores) **do not exist**. Any
   "zero diff, therefore in sync" check built on those proves nothing — that mistake let
   three PRs and a CI gate report success on no evidence. Use:
   - notebook → `.py`: **`nbdev-export && black kreview/`** (nbdev does not implement
     `black_formatting` — verified absent from both 3.0.12 and 3.3.0 — so black must run
     after export, or `black --check` in CI fails)
   - `.py` → notebook: **`python3 -m nbdev.sync --fname kreview/<mod>.py`** (this one works)
   Never hand-edit `kreview/*.py` and consider it done. Always end with export+black
   producing **zero git diff**. **Never put code above the first `# %% ../nbs/…` marker** —
   that header is regenerated and `nbdev.sync` cannot rescue it. Exceptions (no notebook,
   edit directly): `kreview/scoreboard.py`, `kreview/feature_cards.py`,
   `kreview/reproducibility.py`. nbdev and black are **pinned exactly** in the `[dev]` extra because they generate
   committed source — install with `pip install -e .[dev]`, never bare `pip install nbdev`.
   Enforced by `.claude/hooks/nbdev-noop-guard.py`.
   See `.agents/skills/nbdev-patterns/SKILL.md`.
2. **One implementation per behaviour.** Monolithic (`kreview run`) and decomposed
   (`kreview select`/`eval`/`multimodal`) paths must call the **same** shared library
   function, never copy-pasted logic. Most historical bugs came from one path being fixed
   and its twin forgotten (sample_labels, best_auc, metadata-column drops). New shared
   logic goes in a library module and is imported by both.
3. **Fail loud, not to 0.0.** Do not let a metric default to `0.0`/empty on failure, or a
   report exit `0` when it failed. Distinguish transient I/O (retry) from schema/programming
   errors (raise). A silent degenerate result is worse than a crash in an evaluation engine.
4. **Attribute failures before "fixing".** Most kreview failures are `environment`
   (Singularity PATH, read-only `/home`, unbuilt/stale container, CUDA OOM, missing dep) —
   log these to `.agents/learnings/ERRORS.md`, do **not** edit code that was never broken.
   The BorutaShap outage was misdiagnosed as a container issue for two releases.
5. **HPC hardening is centralized, not per-module.** Env exports (HOME/TMPDIR/XDG/IPYTHONDIR/
   `PYTORCH_CUDA_ALLOC_CONF`) and resource ladders belong in shared Nextflow labels, applied
   once — not pasted into whichever module last failed.
<!-- protected:end -->

## Hard defaults

- **Deletion:** never `rm -rf`; use `trash`. Enforced by a hook.
- **Secrets:** never commit keys/tokens; no `.env` edits. Enforced by hooks + gitleaks pre-push.
- **No PHI or personal data — this repo is PUBLIC.** Never write patient identifiers (MSK
  DMP ids, MRN, SSN, DOB), clinical data, or personal paths/names into any committed file —
  especially `.agents/memory/` and `.agents/learnings/`, which are committed and therefore
  published. Memory holds codebase and process facts only. Use `P-0000000-T01-XS1` as the
  sample-id placeholder in docs. Enforced by the PHI rules in `.gitleaks.toml` via the
  gitleaks pre-push hook; verify them with `bash scripts/check_phi_guard.sh`.
- **Outward actions ask first:** pushing to shared branches, publishing images, creating
  releases, submitting SLURM jobs that spend the group allocation — confirm, every time.
- **Commits:** conventional-commit format (`type(scope): summary`); never `git add -A` blind.

## Rules index (`.agents/rules/`, load on demand)

- `nbdev-conventions.md` — cell directives, export/sync workflow, notebook↔module map.
- `labeling-hierarchy.md` — the 5-tier ctDNA taxonomy and thresholds.
- `fragmentomics-domain.md` — feature families and biology.
- `duckdb-patterns.md` — DuckDB lake, chunked I/O, retry.
- `parquet-only.md` — I/O format convention.
- `code-quality.md` — style, typing, dedup expectations.
- `git-conventions.md` — branching, commit, release flow.

## Skills & memory

- Skills load from `.claude/skills/` (a symlink to `.agents/skills/`) and from `.agents/skills/`
  for other tools. Pin a `model:` and sharp triggers in each skill's frontmatter.
- Durable memory: `.agents/memory/` (four tiers: user/project/reference/feedback).
- Learning loop: `.agents/learnings/` (`LEARNINGS.md` work orders, `ERRORS.md` environment
  failures, `REJECTED.md` vetoed edits). Tactical state: `CONTINUITY.md`.

## Hierarchy

1. User-global `~/AGENTS.md` → 2. Machine-local → 3. this project file. More specific wins.
Facts learned once are **memory**, not rules. Prune this file by relevance-per-turn, not length.
