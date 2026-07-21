---
name: reference-nextflow-support-policy
description: "kreview supports Nextflow v25–v26; nextflow.config must parse on both. Testing scope is a stub run only — no nf-test harness."
metadata:
  type: reference
---

**Supported Nextflow range: v25 and v26.** `nextflow/nextflow.config` must parse on v26 and
remain compatible with v25. `manifest.nextflowVersion` should express that range — an
unbounded `!>=22.10.1` is what lets a modern Nextflow fail with a cryptic parse error instead
of a clear "unsupported version" message.

**Testing scope: a stub run only.** A `-stub-run` (or equivalent smoke invocation) proving the
config parses and the DAG wires is sufficient. A full `nf-test` harness — per-process unit
tests, fixture data, a test suite — is explicitly **out of scope** by maintainer decision
(2026-07-21).

Known parse blockers on v24+ (see issue #80): `try/catch` around `includeConfig`; five
`${manifest.version}` references in container tags (`manifest` is not resolvable from
`process`/`profiles` scope); and `${HOME}` / `System.getenv` interpolation, which modern
Nextflow requires as `env('...')`.

Nextflow cannot be validated locally against v23 on a modern JDK — 23.10.1 fails to start on
Java 25 with `Unsupported class file major version 69`. Validate against v25/v26 only.

See [[reference-hpc-singularity-gotchas]].
