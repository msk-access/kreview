# Report Interpretation Guide

`kreview report` renders **one self-contained HTML page** (`reports/kreview_report.html`)
built from the run's aggregate artifacts — no Quarto, no render-time computation, and
**no sample identifiers anywhere in the file** (enforced by a build-time PHI guard, so the
report is safe to share). Open it in any browser; nothing is fetched from the network.

A machine-readable `report_manifest.json` sits next to the page recording exactly what the
report covers — including evaluators that appear in the scoreboard but lacked model-result
files (`missing_detail`). A partial report is always loud, never silently incomplete.

---

## The four tabs

### 1. Cohort & labels

Sample counts, the 5-tier ctDNA label taxonomy (n and % per tier), cancer-type
composition, and the **train/test split composition** by label tier.

!!! warning "Patient-overlap warning"
    If any patient has samples in **both** train and test, a warning banner reports the
    count. A sample-level split leaks patient biology across the boundary and makes
    holdout metrics optimistically biased — see the patient-grouped-split issue for the
    fix. The banner disappears when `patients_in_both_splits == 0`.

The evaluator AUC overview ranks all evaluators by best-model CV AUC; hover shows the
holdout AUC and sens@95 for each.

### 2. Scoreboard

Sortable/filterable table of every evaluator: status badge (`OK` / `PARTIAL` / `FAILED` /
`NO_RESULTS`), best model, CV AUC, holdout AUC, the **Δ-overfit column** (CV − holdout),
operating-point sensitivities, and selection metadata.

**Click any row** for the deep-dive modal:

| Section | What it tells you |
|---|---|
| Models table | Per-model AUC with 95% CI, fold-AUC mini-bars (spread = CV stability), sens@95/100/100-healthy, holdout AUC |
| ROC / PR | Computed from **out-of-fold** predictions (honest — no refit); PR is baselined at prevalence |
| Calibration | 10-bin reliability: do predicted probabilities match observed rates? Matters because stacking consumes these probabilities as features |
| Decision curve | Net benefit vs threshold, against treat-all/treat-none — the clinical-utility framing of the sensitivity/specificity trade-off |
| Subgroup AUCs | Per cancer type (n ≥ 30 only), from OOF predictions |
| Fold-ablation | Which feature group won each nested-CV outer fold, per model. A group winning most folds = stable selection; a split vote = fold-sensitive signal |

!!! note "sens@100spec~healthy~ is high-variance"
    This operating point thresholds on the **maximum score among the healthy normals** in
    the CV set. With few healthy normals (the modal shows the count), a single atypical
    donor moves the threshold — treat the point estimate cautiously. It remains the right
    headline metric for a screening use case; the caveat is about its uncertainty, not
    its relevance.

### 3. Multimodal

Stacking vs raw-feature AUC per model (dot + 95% CI, with the best-single-evaluator
reference line), stacking precision–recall curves, per-model detail, and — when the run
produced it — the leave-one-evaluator-out ablation. If the ablation stage failed, the tab
says so explicitly instead of rendering blank.

### 4. Run diagnostics

Process outcomes (tasks, failures, retry counts) and the longest tasks, from the Nextflow
execution trace. The trace only exists after the workflow ends, so this tab is empty for
the in-pipeline render — re-run `kreview report` on the published output directory to
fill it in:

```bash
kreview report --outdir /path/to/outdir --out-dir reports \
  --trace /path/to/outdir/pipeline_info/execution_trace.txt
```

---

## Reading the metrics honestly

- **CV vs holdout**: the scoreboard's best model is chosen by max CV AUC across models,
  which is mildly optimistic — read the holdout column and the Δ-overfit before trusting
  a winner.
- **OOF everywhere**: every curve and subgroup metric comes from out-of-fold predictions,
  never refit-on-everything scores.
- **Aggregates only**: subgroup cells have an n ≥ 30 floor for statistical stability, and
  the page carries zero per-sample data by construction.
