---
name: feedback-isolated-envs-only
description: "Never pip-install into the base/system interpreter — create an isolated environment (uv, micromamba, mamba or conda) for every install, including throwaway experiments."
metadata:
  type: feedback
---

Every package install goes into an **isolated environment**. Never install into the base or
system interpreter, not even for a one-off experiment, and never assume a scratch directory is
a venv — check for `pyvenv.cfg` and confirm `sys.prefix` points inside it before installing.

Acceptable tools: **uv** (fastest), **micromamba**, **mamba**, **conda**. Any of them is fine;
the requirement is isolation, not a particular tool.

**Why:** installing `torch`/`tabicl`/`transformers` for a one-off benchmark went into the base
interpreter because the target path had no `pyvenv.cfg` and its `python` resolved to the base
install. Beyond ~2GB of unwanted packages, pip **upgraded `setuptools` past 81**, which removes
`pkg_resources` — the exact breakage this project pins `setuptools<81` to avoid (see the `arfs`
extra in `pyproject.toml`). A benchmark that was supposed to touch nothing silently changed the
dependency that the selection stage needs.

**How to apply:**

- Before any install, verify isolation:
  `python -c "import sys; print(sys.prefix)"` must be inside the env directory, and
  `test -f <env>/pyvenv.cfg` must pass for a venv-style env.
- Create one per task, e.g. `uv venv <dir> && <dir>/bin/python -m pip install …`, or
  `mamba create -p <dir> python=3.12 …`.
- Heavy GPU/ML stacks (torch, tabicl, tabpfn) belong in a dedicated env — or on the cluster,
  where the containers already carry them (see [[reference-hpc-singularity-gotchas]]).
- If something did land in the base env, remove exactly what was added and restore any version
  the project pins, then re-run the test suite before moving on.
