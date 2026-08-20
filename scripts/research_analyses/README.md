# Research analyses (offline, run against a local copy of a pipeline outdir)

Post-v0.0.32 measurement scripts behind the research-roadmap issue. Each runs
against a local copy of a published outdir (default `~/Downloads/v0.0.32_eval`)
in a venv with `kreview[arfs]` installed. All outputs are aggregates — no
sample identifiers are ever written.

| script | question it answers |
|---|---|
| `stack_granularity.py` | stack evaluator×model columns (156) vs best-per-evaluator (26) vs per-evaluator mean — AUC & sens@100spec-healthy, paired patient-bootstrap CIs |
| `detection_overlap.py` | detection-set complementarity at 100% healthy spec: unique captures, coverage histogram, greedy set-cover, union vs stacking |
| `tn_anchor.py` | re-anchor operating points on tumor-informed true negatives (IMPACT-paired, zero confirmed variants) vs the healthy-donor anchor |
| `tn_anchor2.py` | CIs for the TN-anchored 98/99% operating points + True-ctDNA+-only sensitivity |
| `leadtime_cleansignal.py` | (1) does fragmentomics anticipate genotype conversion at the prior negative draw; (2) clean-label model (True+ vs qualified TN) applied to every tier |
| `assay_effect.py` | assay-version battery: feature fingerprint, cross-assay generalization gap, negative-score threshold shift |
| `lod_audit.py` | VAF-stratified LOD curve at the 98%-spec-TN operating point: detection per burden bin, miss composition, family LODs |

Findings, numbers and interpretation live on the research-roadmap issue —
these scripts exist so every claim there is reproducible.
