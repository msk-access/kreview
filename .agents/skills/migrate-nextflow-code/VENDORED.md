# Vendored skill — attribution

Vendored from the official [nextflow-io/agent-skills](https://github.com/nextflow-io/agent-skills)
repository (commit `a19bbe2`), Apache-2.0 (see COPYING). Vendored rather than plugin-installed
so it loads for every tool that reads `.agents/skills/` (the kreview cross-tool convention) and
is versioned with the repo.

Relevant to kreview because the strict-syntax migration class keeps biting: #80 (try/catch,
${manifest.*}, ${HOME}) and #97 (task-in-ternary). `nextflow lint` (26.04+) is the
detection tool this skill is built around. To refresh: re-clone the source repo and re-copy.
