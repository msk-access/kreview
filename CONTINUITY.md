# CONTINUITY — kreview

**Goal (current phase):** the hardening campaign is COMPLETE (tracker #66 closed); the
project has shifted to **evaluation science**: honest operating points, quantification,
and the variant-silent value case. Engineering ships in small, CI-gated PRs as before.

---

## Shipped (releases v0.0.30 → v0.0.32, 2026-08-17..18)

- **v0.0.30** — #79 single-page PHI-guarded report (Quarto path deleted); #101
  patient-grouped train/test split (holdout numbers before it are NOT comparable —
  documented on #101); #97 multimodal-ablation GPU fallback + routing; #98
  partial-publish manifest.
- **v0.0.31** — #96 GrootCV migration: arfs 3.0, measured defaults (`cutoff=3`,
  `n_iter=10`), LightGBM feature-name sanitization, BorutaShapPlus → `[legacy-boruta]`
  (mutually uninstallable with arfs 3.0), containers ship `[arfs]`.
- **v0.0.32** — #107/#108 scoreboard rebuilt on an explicit versioned contract
  (sourced values or explicit unknowns + `missing_fields`; QC sidecars staged;
  `nbs/07_scoreboard.ipynb` — standalone exceptions now `reproducibility.py` only).
- **Post-v0.0.32 merged to develop (unreleased):** #96 closeout — `multimodal_selection`
  default `mi` → `grootcv` (#118); five report fixes + LOO-ablation panel + per-tab
  methodology blocks + automatic findings engine (#119); phantom-ablation-evaluator fix
  (52→26 LOO ablations, halves that stage's GPU cost).

## The v0.0.32 iris run (first full-stack production confirmation)

Clean end-to-end: 26/26 evaluators, TabPFN included, grootcv in production (77 raw
features incl. the chr:coord names), 0 patients across splits, honest scoreboard.
Headline: best single FSCGenomewide 0.807 CV / 0.815 holdout; stacking tabicl_ft 0.856.

## Research campaign (findings + full numbers on issue #121; scripts in
`scripts/research_analyses/`, reproducible against a local outdir copy)

1. **Modeling layer saturated** — every knob (selector, meta-learner, stacking
   granularity) moves ≤0.01 AUC. Stop optimizing it.
2. **Healthy anchor (68 donors) cannot support clinical claims** (sens@100spec CI 22pp
   wide). **Tumor-informed true negatives** (Possible ctDNA− + `has_paired_impact` +
   `n_impact_confirmed==0`; 4,414 samples) give the powered MRD operating point:
   **sens@98spec-TN = 0.48 [0.44, 0.52]**; 100%-spec is unattainable in patients.
3. **LOD audit: physics, not feature gap** — sigmoid detection curve, LOD50 ≈ 4–5% VAF,
   >93% above 10% VAF, <5% below 1% VAF. No fragmentation-silent tumor subgroup.
4. **Labels vindicated** — clean-label training does not beat noisy (no label-noise
   ceiling); Possible+ scores identically to True+ under a model never trained on it.
5. **Lead-time null** (accession-order timepoints): fragmentomics tracks current
   shedding, does not anticipate genotype conversion.
6. **Assay effects**: features → assay version AUC 1.000 (fingerprint), but cross-assay
   generalization gap only ~0.01; the real impact is threshold calibration
   (98% global threshold → 98.2%/97.5% realized per version). Fix at decision layer.
7. **Variant-silent value case**: fragmentomics flags among IMPACT-unpaired negatives are
   corroborated by sub-threshold VAF (p=4e-05) and enrich ~12× in Germ Cell Tumor + CUP —
   the niches where variant assays fail structurally.
8. **Quantification**: score ↔ VAF Spearman 0.78, isotonic calibration r=0.81,
   93.6% within-one-band — ordinal fraction-band reporting is near-deliverable.

## In flight / next

- **PR #120** (this branch): all analysis scripts + scripts README + this file — merge.
- **Blinded chart review**: 72 flagged variant-silent samples + 72 matched controls
  (workbook prepared locally, maintainer-side; outputs with identifiers stay OFF-repo).
- **Cluster-side pilots**: (a) off-target genome coverage check (gates the
  CNVkit→ichorCNA hybrid tumor-fraction pipeline; buffy coat as per-patient germline
  control); (b) krewlyzer on ~50 buffy coats (fingerprint-collapse normalization pilot).
- **Engineering issues to file when shifting back to shipping**: `True ctDNA−` labeler
  tier + dual-anchor operating points in report/findings engine; per-assay threshold
  calibration; then a v0.0.33 cut to ship the merged report fixes.

## Standing cautions

- Memory/learnings dirs are PUBLIC (committed); clinical workbooks with sample ids live
  only on the maintainer's machine, never in the repo.
- Pre-#101 holdout numbers are not comparable to grouped-split runs.
- CI-only lint failures: reproduce in `python:3.12-slim` amd64 installed exactly as CI
  (`.agents/memory/reference-ci-env-repro.md`).
