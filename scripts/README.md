# scripts/ — index

One line per script so nothing here goes undocumented. Details live in each file's
header docstring (and in the subdirectory READMEs).

## Guards & CI gates

| script | purpose |
|---|---|
| `check_phi_guard.sh` | asserts the gitleaks PHI/secret rules actually fire (tree clean, rules fire, placeholder allowed, config clean, memory store free of personal paths) — run after touching `.gitleaks.toml` |
| `check_version_consistency.py` | the triple version pin (`settings.ini` / `kreview/__init__.py` / `nextflow.config`) must agree — CI gate |
| `nextflow_stub_test.sh` | stub-run smoke test: config parses on v25+v26, all profiles resolve, 16-process DAG wires, plus structural regression guards (#59/#60/#84/#97/#98, GPU report staging) |
| `test_nextflow_join_dropguard.nf` | standalone channel-logic test: the matrix↔best_subset join must not drop evaluators (#60) |

## Operations

| script | purpose |
|---|---|
| `run_hpc.sh` | the production iris (SLURM/Singularity) launcher — pins `KREVIEW_VERSION`, builds the manifest, enables GPU/ablation/multimodal (grootcv), gates TabPFN on `TABPFN_TOKEN` |

## Analysis suites (offline, run against a local outdir copy)

| directory | purpose |
|---|---|
| [`validation_96/`](validation_96/README.md) | the #96 GrootCV-migration validation harness: selection stability (Jaccard/Nogueira), downstream stacking CV, paired patient-bootstrap CIs, cutoff sweep, n_iter agreement |
| [`research_analyses/`](research_analyses/README.md) | the post-v0.0.32 research campaign (10 scripts): stacking granularity, detection-set complementarity, tumor-informed true-negative anchoring, lead-time, clean-label tier profiling, assay-effect battery, LOD audit, variant-silent flags, quantification + blinded-study builders. Findings on the research-roadmap issue (#121). **Some outputs contain sample identifiers and must stay local** — see that README |
