# Analysis plan — pre-registered endpoints and standing rules

> Declared **before** each production run is analyzed. Purpose: multiplicity discipline
> (the adversarial-review finding: 156 evaluator×model cells, VAF-bin × histology scans,
> and post-hoc enrichment tests are uninterpretable without a declared primary). Changes
> to this file are made *between* runs, never after seeing a run's results.

## Primary endpoint (confirmatory)

- **Metric**: sensitivity at **98% specificity anchored on qualified true negatives**
  (`Possible ctDNA− AND has_paired_impact AND n_impact_confirmed == 0`), with
  patient-cluster bootstrap CI.
- **Score**: multimodal stacking, **tabicl_ft** (declared a priori; not the argmax of
  the run).
- **Reference values (v0.0.32)**: sens@98spec-TN = 0.483 [0.437, 0.522]; AUC vs
  verified-TN negatives = 0.845.

## Secondary endpoints (confirmatory, reported with CIs)

1. Stacking AUC vs verified-TN negatives, per assay version, and cross-version transfer.
2. sens@99spec-TN.
3. LOD curve (detection per max-VAF bin at the primary operating point) — shape and
   LOD50, stated **in tumor fraction** (TF ≈ 2×VAF) alongside VAF.
4. Weighted κ (linear) for fraction-band prediction.

## Everything else is exploratory

Per-evaluator rankings (winner's curse on best-of-156: report the a-priori primary
family — currently FSCGenomewide — alongside any argmax), subgroup/histology contrasts
(Bonferroni over the number of categories scanned, stated), enrichment scans, and any
new operating points. Exploratory findings graduate to confirmatory only by appearing
here *before* the next run.

## Standing rules

- **Metadata firewall**: clinical/technical metadata (age, treatment status, collection
  site/date, depth) may be used for **evaluation and calibration only** — stratified
  reporting, deconfounding regressions, matched controls, context-conditional
  thresholds. It is **never a model feature**: a model that reads age or treatment
  answers "who gets cancer," not "is tumor DNA present," and masks the fragmentomics
  contribution this project exists to measure.
- **Anchors**: donor-anchored sens@100spec is reported as a **one-sided lower bound
  only** (max-statistic over ~55 donors; symmetric bootstrap CIs for this quantity are
  inconsistent by construction). The TN anchor is the clinical headline.
- **Negative-class transparency**: any pooled-negative AUC is reported alongside the
  verified-TN-only AUC (measured verification bias at v0.0.32: +0.010) and the
  donor-only AUC is never presented as the assay's discrimination (it flatters by ~13
  points: 0.976 vs 0.845 at v0.0.32).
- **Comparability**: holdout numbers before the patient-grouped split (≤ v0.0.29) and
  operating points before the TN anchor (≤ v0.0.32) are not comparable to later runs.
- **PPV framing**: operating points are additionally reported as PPV/NPV at stated
  prevalences (5/10/25% and the cohort rate).

## Current confirmatory questions for the *next* production run

1. Does the primary endpoint reproduce within its v0.0.32 CI?
2. Does per-assay threshold calibration hold realized specificity within [97.5%, 98.5%]
   per version?
3. (When #122 lands) does partialling `n_fragments_total`/`n_fragments_ontarget` out of
   the features change the primary endpoint by more than 0.01 AUC-equivalent?
