<!--
Environment-failure log. When a failure is EXTERNAL (Singularity PATH stripping, read-only
/home, unbuilt/stale container, CUDA OOM, missing dependency, cluster node/quota), it is NOT
a code or skill bug. Log it here and fix the environment. Do NOT edit code that was never
broken. Newest at top.

Skeleton:
## [ERR-YYYYMMDD-NNN] <one-line: what failed externally>
- **What happened:** <the external failure>
- **Skill/pipeline involved:** <which ran — confirmed NOT at fault>
- **Environment fix:** <what was wrong outside the harness, and what fixed it>
- **Date:** YYYY-MM-DD
-->

## [ERR-20260622-001] BorutaShap "No module named 'BorutaShapPlus'" on HPC (historical, resolved)
- **What happened:** Multimodal pipeline chain failed on HPC; root cause was the pip package
  `BorutaShapPlus` exposing an importable module named `BorutaShap`, plus a container built
  from a stale state — an environment/packaging issue, not the multimodal code.
- **Skill/pipeline involved:** multimodal_prep + 5 downstream stages — NOT at fault.
- **Environment fix:** correct the import name and rebuild the container from a clean state;
  a CI container smoke-test would have caught it before release.
- **Date:** 2026-06-22 (recorded 2026-07-11 as the canonical example of `environment` cause)
