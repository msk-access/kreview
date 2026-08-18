---
name: reference-ci-env-repro
description: "Reproducing CI-only lint/type failures — rebuild CI's env exactly in a container; dep-graph edits shift transitively resolved versions and move the mypy surface."
metadata: 
  node_type: memory
  type: reference
  originSessionId: dea22cc1-8005-4d46-95c8-4674461adc50
  modified: 2026-08-18T13:19:53.670Z
---

CI lint failures that don't reproduce locally are usually an **environment-resolution
difference, not flakiness**. Two lessons from the #96 migration (2026-08):

- **Removing (or adding) a core dependency changes what CI resolves transitively.**
  Dropping BorutaShapPlus from core lifted its `numpy<=2.0.0` cap, so CI's lint env
  jumped to numpy 2.5.2, whose new type stubs failed `mypy==2.3.1` on 15 *untouched*
  lines (`min(int, ndarray.min())` inferring a SupportsDunder union that poisons dict
  inference). Local envs on older numpy (or older Python — numpy 2.5 needs ≥3.12)
  cannot see these errors at all.

- **The honest repro is CI's env, byte for byte**: run
  `docker run --rm --platform linux/amd64 -v "$PWD":/src -w /src python:3.12-slim
  bash -c "pip install -e '.[dev]' && mypy kreview"` — same Python, same platform
  wheels, same resolution. Fix, then re-verify in the same container before pushing.
  (arm64 containers can diverge: some packages ship no arm64 wheel and source-builds
  fail or resolve differently.)

**How to apply:** whenever a PR touches `pyproject.toml` dependencies, expect the lint
surface to move; run the container repro proactively instead of discovering it in CI.
Also verify each lint tool's exit code separately — `black --check -q | tail` can
swallow a failure while ruff's "All checks passed!" reads as if it were black's. Related:
[[feedback-nbdev-source-of-truth]] (pinned toolchain rationale).
