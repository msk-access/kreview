# Report Interpretation Guide

`kreview report` renders **one self-contained HTML page** (`reports/kreview_report.html`)
built from the run's aggregate artifacts — no Quarto, no render-time computation, and
**no sample identifiers anywhere in the file** (enforced by a build-time PHI guard, so the
report is safe to share). Open it in any browser; nothing is fetched from the network.

A machine-readable `report_manifest.json` sits next to the page recording exactly what the
report covers — including evaluators that appear in the scoreboard but lacked model-result
files (`missing_detail`). A partial report is always loud, never silently incomplete.

---

## The five tabs

### 1. Cohort & labels

Opens on the **pre-registered primary endpoint** — sensitivity at 98% specificity against
verified true negatives — with its patient-clustered interval, the burden-response curve
behind it, and the stacking lift over the best single evaluator.

Then sample counts, the 6-tier ctDNA label taxonomy (n and % per tier; four modelled, with
`Undetermined` and `Insufficient Data` excluded), cancer-type composition, and the
**train/test split composition** by label tier.

!!! important "Which negatives the headline was scored against"
    The **verification-bias ladder** shows the same model on the same positives against four
    different negative classes: verified within-patient negatives, all negatives pooled,
    unpaired negatives, and healthy donors. On the v0.0.32 cohort those span **13.1 AUC
    points** — more than any modelling decision in the campaign. The verified-TN rung is the
    defensible one; the donor rung is not less trustworthy so much as a different question
    (between people rather than within a patient), and it is the comparison most screening
    literature reports.

The operating-points panel states both anchors, and its intervals come from a patient-clustered
bootstrap with the threshold re-estimated inside every resample. Two things inflate that width
and they are reported separately, because they are not the same size: clustering contributes a
design effect of ~1.26, estimating the threshold from a finite negative set contributes ~11×.

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

Subgroup AUCs in the modal carry a **per-class floor** — at least 30 positives *and* 30
negatives, so a group cannot qualify on its negatives alone — a patient-clustered interval
(computed for the pre-registered primary evaluator; every other subgroup table is
exploratory), and the share of each group's positives that are tumour-confirmed, which
ranges from about half to over ninety percent across histologies. Read the AUC against that
share: a group whose positives are largely the ambiguous tier is discriminating a less
certain set.

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

Opens on the **pipeline run map** — the Nextflow DAG drawn with this run's task counts on
each node. A node standing for several processes reports how many it covers rather than
summing their task counts, and clicking it opens those processes with their failures,
slowest task and peak RSS. A stage with no trace row reads *no trace*, never green.

Below it, process outcomes (tasks, failures, retry counts) and the longest tasks, from the
Nextflow execution trace. The trace only exists after the workflow ends, so this tab is empty for
the in-pipeline render — re-run `kreview report` on the published output directory to
fill it in:

```bash
kreview report --outdir /path/to/outdir --out-dir reports \
  --trace /path/to/outdir/pipeline_info/execution_trace.txt
```

### 5. Methods & interpretation

The same DAG in structure form (two densities, no run status), the label definitions, how
each operating point is derived, and the glossary terms behind the info icons that appear
throughout the other tabs.

---

## Reading the metrics honestly

- **CV vs holdout**: the scoreboard's best model is chosen by max CV AUC across models,
  which is mildly optimistic — read the holdout column and the Δ-overfit before trusting
  a winner.
- **OOF everywhere**: every curve and subgroup metric comes from out-of-fold predictions,
  never refit-on-everything scores.
- **Aggregates only**: subgroup cells have an n ≥ 30 floor for statistical stability, and
  the page carries zero per-sample data by construction.
- **Patient grouping**: the train/test split is patient-grouped (no patient spans splits),
  so the holdout column is the honest headline. Eval-stage CV is deliberately *not*
  patient-grouped: the inflation was measured on real data at ≤ ~0.001 AUC — an order of
  magnitude below fold-to-fold noise — and documented in
  [#101](https://github.com/msk-access/kreview/issues/101). Holdout numbers from runs
  before the grouped split (≤ v0.0.29) are not comparable to later runs (shifts of
  ~0.005–0.02 from test-set re-composition).
