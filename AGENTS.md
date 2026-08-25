# kreview — standing context (canonical, cross-tool)

> Canonical agent rules for this repo. Read by Antigravity, Cursor, Codex, Copilot,
> and (via `CLAUDE.md` import) Claude Code. Every line is read on every turn — keep it
> tight. Depth lives in `.agents/rules/*.md` and is read on demand, not here.

**What this is:** `kreview` — an evaluation engine for cfDNA fragmentomics features for
ctDNA detection (MSKCC / MSK-ACCESS). Labels samples on a 6-tier ctDNA taxonomy, extracts
26 fragmentomics feature families, runs multi-model CV evaluation (CPU + GPU), multimodal
stacking, and Quarto dashboards. Ships as a pip package, CPU/GPU Docker images, and a
Nextflow HPC (SLURM/Singularity) pipeline.

**Architecture:** `nbdev` project. Source of truth is the notebooks in `nbs/`; the
`kreview/*.py` modules are **generated**. There is exactly **one** way to run the pipeline:
the Nextflow multistage DAG (`label → extract → select → ablate → eval cpu/gpu → fuse →
multimodal → scoreboard → report`), which scatters per-evaluator and drives the `kreview`
stage subcommands. Supported Nextflow: **v25–v26**. Full module map:
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
   edit directly): `kreview/reproducibility.py` only (#108 folded scoreboard.py into
   `nbs/07_scoreboard.ipynb`; feature_cards.py was deleted by #79).
   nbdev and black are **pinned exactly** in the `[dev]` extra because they generate
   committed source — install with `pip install -e .[dev]`, never bare `pip install nbdev`.
   Enforced by `.claude/hooks/nbdev-noop-guard.py`.
   See `.agents/skills/nbdev-patterns/SKILL.md`.
2. **One implementation per behaviour.** Never stand up a second code path for work that
   already has one — no "convenience" wrapper that re-implements a stage, no bulk variant
   beside a scattered one. Most historical bugs came from one path being fixed and its twin
   forgotten (sample_labels, best_auc, metadata-column drops, the H1 ablation bug). The
   monolithic `kreview run` and the Gen-1 bulk `.nf` modules were **deleted** for exactly
   this reason (#55); do not reintroduce them. Shared logic lives in a library module and is
   imported wherever it is needed.
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
  published. **`.agents/memory/` is also symlinked in as the Claude memory store, so "saving a
  memory" publishes.** Machine-local facts (absolute paths, env names, cluster/account
  specifics) go in `.agents/memory/private/` (gitignored) — routing rule and rationale in
  `private/README.md`. PHI belongs in **neither** store. Use `P-0000000-T01-XS1` as the
  sample-id placeholder in docs. Enforced by the PHI rules in `.gitleaks.toml` via the
  gitleaks pre-push hook; verify them with `bash scripts/check_phi_guard.sh`.
- **Outward actions ask first:** pushing to shared branches, publishing images, creating
  releases, submitting SLURM jobs that spend the group allocation — confirm, every time.
- **Commits:** conventional-commit format (`type(scope): summary`); never `git add -A` blind.

## Rules index (`.agents/rules/`, load on demand)

- `nbdev-conventions.md` — cell directives, export/sync workflow, notebook↔module map.
- `labeling-hierarchy.md` — the 6-tier ctDNA taxonomy and thresholds.
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
