---
name: reference-nextflow-support-policy
description: "kreview supports Nextflow v25–v26 (floor 25.04.0, enforced); the DAG is smoke-tested with scripts/nextflow_stub_test.sh — a stub run only, no nf-test harness."
metadata:
  type: reference
---

**Supported Nextflow range: v25–v26.** `manifest.nextflowVersion = '!>=25.04.0'` — a hard
floor, so an unsupported version fails with a clear message instead of a cryptic parse error
further down the file. Verified against 25.04.6, 25.10.6 and 26.04.6 (#80, 2026-07-21).

**Testing scope: a stub run only** — `bash scripts/nextflow_stub_test.sh [nextflow-path]`.
Every process declares a `stub:` block creating just its declared outputs, and a `stub` profile
clamps resources, so `-stub-run -profile stub` wires the whole DAG in seconds with no data or
containers. CI runs it on both ends of the range. A full `nf-test` harness is explicitly **out
of scope** by maintainer decision (2026-07-21). Run the script after any `.nf` or
`nextflow.config` change.

**Config-syntax rules that modern Nextflow enforces** (all three bit us in #80):
- `try`/`catch` **and** `if` statements are rejected around `includeConfig`. Use the nf-core
  ternary: `includeConfig cond ? "path" : "/dev/null"`.
- `manifest` is **not resolvable** from `process`/`profiles` scope. Container tags read
  `params.kreview_version` instead, and the manifest reads that param back — one literal.
  `scripts/check_version_consistency.py` anchors to that param by name.
- `${HOME}` interpolation is rejected; use `env('HOME')` (added in Nextflow 24.11, hence the
  25.04 floor).
- A named `withName:` selector outranks the generic `process` scope, so the `stub` profile
  clamps resources via `withName: '.*'`.

**Gotchas learned by actually running it:**
- A `withName:` selector naming a deleted process is only a *warning* — silent config rot. The
  stub test fails on it deliberately.
- The console format is version-specific (v26 prints `[SUCCESS] completed=N`, v25 does not).
  Assert on `pipeline_info/execution_trace.txt` (col 4 = process, col 7 = status), never on
  stdout.
- Nextflow ≤25.04 will not start on JDK 25 (`Unsupported class file major version 69`). Use a
  JDK 17 to test the floor version locally; CI pins Java 17.

See [[reference-hpc-singularity-gotchas]] and [[feedback-parallel-paths-one-impl]].
