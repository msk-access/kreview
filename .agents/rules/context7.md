---
description: When to reach for Context7 instead of memory or web search
alwaysApply: true
---

# Context7 — library and API documentation

## The rule

Use Context7 to fetch current documentation **whenever the work touches a library,
framework, SDK, API, CLI tool, or cloud service** — without being asked. That includes
API syntax, configuration, version migration, library-specific debugging, setup steps,
and CLI usage.

**Use it even when you think you know the answer.** Training data lags releases, and this
repo has already lost time to exactly that failure mode:

- `arfs` 2.4 against LightGBM 4.7 breaks GrootCV (ERR-20260824-001) — an API that moved.
- A base-env install pulled `setuptools` past 81 and removed `pkg_resources`, which is why
  the `setuptools<81` pin exists.
- nbdev's real commands are not the obvious ones: `python3 -m nbdev.export` is a silent
  no-op and `nbdev_export` does not exist. Three PRs and a CI gate reported success on that
  mistake.

Prefer Context7 over web search for library documentation.

## Where it does not apply

Refactoring, writing scripts from scratch, debugging business logic, code review, and
general programming concepts. These are reasoning tasks, not lookup tasks.

**And it is not for this codebase.** Questions about kreview's own architecture, modules or
file relationships go to `graphify query` / `graphify explain` (see `CLAUDE.md`), which
returns a scoped subgraph of *this* repo. Context7 covers third-party surfaces only. The
split is: graphify for what we wrote, Context7 for what we import.

## How

1. Start with `resolve-library-id`, passing the library name plus what you need from its
   docs. Skip this only when given an exact `/org/project` id.
2. Pick the best match on exact name, description relevance, snippet count, source
   reputation, and benchmark score. Use a version-specific id when a version is named. If
   the results look wrong, try an alternate spelling (`next.js`, not `nextjs`).
3. Call `query-docs` with that id and a phrase, not a single word, scoped to **one**
   concept. Several distinct concepts means several calls with the same id — combined
   queries dilute ranking and return shallow results for each topic. Combine only when the
   question is about how the concepts interact.
4. Answer from the fetched docs.

## Availability

Context7 is an MCP server and is configured per tool, not in this repository. When it is
not connected, say so and fall back to web search rather than answering from memory on a
versioned API. Surfaces where this matters most here: nbdev, pandas, DuckDB,
scikit-learn, plotly, typer, Nextflow, Singularity, LightGBM/arfs, TabPFN/TabICL.
