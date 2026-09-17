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

## How this relates to graphify

Not "ours versus theirs" — they answer different **questions**, and one task can need both.

**graphify** is a comprehension tool over this repo's knowledge graph: how the pieces fit,
what connects to what, where something happens. It earns its place on questions that span
files, where it replaces grep by returning a scoped subgraph. `CLAUDE.md` is explicit that
it is *advisory*, and that it should be skipped for edits, unrelated files and quick
lookups.

**Context7** is a reference lookup against an external surface: what the API is, how it is
configured, what moved between versions. That is a standing rule, not advisory, because
the failure it prevents is silent — a confidently wrong answer from stale training data.

So the two are not alternatives on one axis, and "how do we use DuckDB here" is really two
questions. graphify shows where and how we already call it; Context7 says whether that call
is still current. Reaching for graphify on a third-party API returns our own usage, which
may itself be out of date — that is the failure mode this split exists to prevent.

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
