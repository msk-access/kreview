# Dashboard Interpretation Guide

The kreview dashboard uses a **progressive disclosure** design: information flows from high-level clinical summaries to granular technical detail. This page explains each section, what it shows, and why.

---

## Design Philosophy

Traditional bioinformatics reports present engineering metrics (AUC, confusion matrices) without translating them into clinical decisions. The kreview dashboard addresses this by structuring information into six pages, ordered by cognitive priority:

1. **Executive Summary** — Is this feature useful? (1-minute answer)
2. **Model Validation** — How robust are the classifiers? (5-minute deep-dive)
3. **Feature Explanation** — Which sub-features drive predictions and why?
4. **Biomarker Yield** — What are the strongest individual signals?
5. **Cohort & QC** — Is the data trustworthy?
6. **Data Explorer** — Full access to the raw matrix

This mirrors clinical decision-making: start with a verdict, then inspect the evidence.

---

## Page 1: Executive Summary

### What it shows

| Component | Data Source | Purpose |
|-----------|-----------|---------|
| Cohort Size | Matrix row count | Establishes sample power |
| Positive Rate | Label distribution | Shows class balance and clinical prevalence |
| Best AUC [95% CI] | `auc_{best_m}`, `auc_{best_m}_ci_lower/upper` | Key discriminative metric with uncertainty (dynamically selected best model) |
| Sensitivity @ Optimal | `{best_m}_classification_report["1"]["recall"]` | True positive detection rate at optimal cutoff |
| Specificity @ Optimal | `{best_m}_classification_report["0"]["recall"]` | True negative rejection rate at optimal cutoff |
| Sens @ 100% Spec | `{best_m}_sensitivity_at_100spec` | Sensitivity at zero false-positive rate (v0.0.16+) |
| Holdout AUC | `holdout_{best_m}_auc` | AUC on unseen 20% test set with CV–holdout delta (v0.0.16+) |
| Verdict | AUC threshold logic | Quick interpretation (Strong ≥0.80, Moderate ≥0.70, Weak <0.70) |
| Nested CV | `nested_cv` flag | Whether ablation-based nested CV was used for feature selection (v0.0.20+) |

### Why these metrics

- **AUC with CI** prevents over-interpreting point estimates. A single AUC of 0.85 tells you nothing about whether 0.78–0.92 or 0.84–0.86 — the confidence interval reveals this.
- **Sensitivity and specificity** are shown at the Youden's J optimal threshold because raw AUC doesn't tell clinicians what happens at a specific decision boundary.
- **Sens @ 100% Spec** is the most clinically relevant metric for ctDNA screening: how many cancers are detected when zero healthy controls are called positive? The detection count is shown alongside sensitivity.
- **Holdout AUC** reveals generalization: if the CV AUC is 0.90 but holdout is 0.75, the model is overfitting. The value box color dynamically adapts to the AUC drop severity (green < 0.05, yellow < 0.10, red ≥ 0.10).
- **Verdict** uses conservative thresholds — an AUC below 0.70 has limited clinical utility for binary classification.

### ROC Sparkline + Calibration

The mini-ROC curve provides a visual sanity check. The calibration reliability diagram (all discovered models) shows whether predicted probabilities are trustworthy — tree-based models tend to push probabilities toward 0.5.

### Scoreboard

If multiple evaluators have been run, the scoreboard table surfaces the top performers for cross-evaluator comparison. Columns include `best_model`, `best_auc`, `holdout_auc`, `auc_drop`, `sensitivity`, `specificity`, `sens_at_100spec`, `sens_at_95spec`, `best_sens_100spec_healthy`, `selection_method`, `n_features`, `best_subset_size`, `nested_cv`, `n_samples`, `holdout_n_train`, and `holdout_n_test`. Columns that are absent from the scoreboard DataFrame (e.g., pre-v0.0.16 results) are automatically hidden.

---

## Page 2: Model Validation

Eleven tabs, each answering a specific validation question:

### Performance Metrics
**Question**: How do the trained models compare on clinical metrics?

- Grouped bar chart comparing Precision, Sensitivity, Specificity, F1, and Accuracy across LR, RF, and XGBoost (plus GPU models — TabPFN, TabPFN-FT, TabICL, TabICL-FT — when available)
- Model summary table with AUC, Youden J threshold, training time, plus v0.0.16 clinical metrics: Sens@100%Spec, Sens@95%Spec, and Holdout AUC (auto-discovered per model, including GPU models when GPU eval was run)
- AUC deltas (pairwise differences) and training times

### ROC Curves with CI
**Question**: Is the discriminative power robust?

- Full ROC curves with 95% bootstrap confidence intervals in the legend
- Compare model families on the same axes

### Precision-Recall (PR)
**Question**: Does the model perform well under class imbalance?

- PR curves are more informative than ROC when the positive class is rare
- The horizontal dashed line shows prevalence — any model performing near prevalence is no better than random
- Average Precision (AP) summarizes PR performance as a single number

### Decision Curve Analysis (DCA)
**Question**: At what probability thresholds does the model provide net clinical benefit?

- Shows net benefit of using the model vs treating all patients or treating none
- A model is clinically useful at thresholds where its curve exceeds both reference lines
- Computed as: `net_benefit = TP/N - FP/N × (threshold / (1 - threshold))`

### Threshold Sensitivity
**Question**: How sensitive are clinical metrics to threshold choice?

- Plots sensitivity, specificity, and PPV across 50 thresholds (0.01–0.99)
- The optimal Youden's J threshold is marked with a dashed line
- Allows clinicians to choose an operating point based on their risk tolerance
- The classification report also uses this Youden's J threshold (consistent with confusion matrices)

### Fold Variability
**Question**: How stable is AUC across cross-validation folds?

- Box plot of per-fold AUC for all models
- A high standard deviation (>0.05) suggests the model is data-sensitive
- Fold AUC tracking uses `cross_val_score` with `StratifiedKFold`

### Confusion Matrices
**Question**: What are the raw prediction counts at the optimal threshold?

- Side-by-side heatmaps for all trained models (LR, RF, XGB, and GPU models when available)
- All predictions are out-of-fold (unbiased)
- Helps identify whether errors are dominated by false positives or false negatives

### Cancer Type Yield / Assay Yield
**Question**: Does this feature generalize across cancer types and assay panels?

- Horizontal bar charts showing sensitivity per subgroup
- Uses out-of-fold predictions to prevent optimistic bias
- Identifies tissue-specific vs pan-cancer features

### Classification Report
**Question**: Full sklearn-style precision/recall/f1 breakdown?

- Standard classification report table for all trained models
- Includes support (sample count) per class

### Feature Importances
**Question**: Which sub-features does the best model (by AUC) consider most informative?

- Top 20 features by Gini importance from the fitted model with highest AUC
- Models are sorted by AUC descending; the first model supporting feature importances is shown
- Complements SHAP by showing a simpler, non-interaction-aware view

---

## Page 3: Feature Explanation (SHAP)

### Why SHAP

SHAP (SHapley Additive exPlanations) decomposes each prediction into per-feature contributions. Unlike feature importances (which are global), SHAP shows *direction* — whether a feature pushes predictions toward positive or negative.

!!! warning "Interpretation discipline"
    SHAP explains **how the model decides**, not biological causality. A feature with high SHAP impact in a Random Forest may reflect a data artifact rather than a biological mechanism.

### Beeswarm
Global view: each dot is one sample×feature. Position on x-axis = SHAP impact, color = feature value. Features are ranked by mean absolute SHAP value.

### Feature Dependence
Shows how the top-1 feature's SHAP value changes as the feature value increases, colored by a second interacting feature.

### Prediction Traces (Waterfalls)
Side-by-side waterfall diagrams for the highest-confidence True Positive and the highest-confidence False Positive, revealing which features drove each decision.

### Feature Cards
Auto-generated metadata cards for the top-5 features, sourced from the evaluator registry:

- **Tier** and **Category** from the `FeatureEvaluator` class
- **Univariate AUC + Mutual Information** scores (with legacy Cohen's d fallback)
- **Feature stability** — percentage of CV folds where this feature appeared in the top 10
- **LR coefficient direction** — whether the feature is positively or negatively associated with ctDNA+
- **Derived feature types** — detected via source code introspection (entropy, spectral, bimodality, etc.)

### Probability Densities
KDE density plot of the best model's predicted probabilities by ctDNA label. Indicates label separation — a discriminative model shows non-overlapping peaks.

---

## Page 4: Biomarker Yield

### Volcano Plot
Univariate AUC on x-axis vs statistical significance (−log10 Kruskal-Wallis p-value) on y-axis. The best features appear in the upper-right quadrant (high AUC + significant). Legacy reports may show Cohen's d on the x-axis instead.

- Dashed lines at AUC=0.6 and p=0.01 mark conventional thresholds for "useful discrimination" and "significant"
- The top feature (by AUC) is highlighted

### Feature Selection QC Scatter
Scatter plot of Univariate AUC (x-axis) vs Mutual Information (y-axis) for all features. Each point is color-coded by its selection category:

| Color | Category | Meaning |
|-------|----------|---------|
| 🟢 Green | Selected (Both) | Top X% in *both* AUC and MI |
| 🔵 Blue | Selected (AUC Only) | Top X% in AUC but not MI |
| 🟠 Orange | Selected (MI Only) | Top X% in MI but not AUC |
| ⚪ Gray | Dropped | Below threshold in both metrics |

This plot provides a visual audit trail for the selection method. Under `hybrid_union`, it shows exact 4-way overlaps (Both/AUC-only/MI-only/Dropped). Under `mrmr`, all selected features are colored cyan with a disclaimer noting that the AUC/MI axes are observational (mRMR internally uses F-statistic for relevance and Pearson correlation for redundancy).

### Feature #1 Violin
Distribution of the single best feature (by Univariate AUC, with Cohen's d fallback for legacy results) across the four ctDNA labels. Box plot overlay shows medians and IQR.

### VAF Scatter (Tumor Burden Independence)
Scatter plot of the top feature vs max VAF on log scale, colored by label. A LOWESS trendline reveals whether the feature independently predicts ctDNA status or simply tracks mutation burden. Features strongly correlated with VAF (Spearman r > 0.5) may be confounded.

### Statistical Ledger
Full table of all per-feature statistics: Univariate AUC, Mutual Information, Cohen's d, K-W p-value, Mann-Whitney U effect size, Spearman correlations, missingness, and zero-variance flags. Sorted by Univariate AUC (descending) by default.

---

## Page 5: Cohort & QC

### Why QC matters
A model with AUC=0.95 is meaningless if 30% of features are missing or if label balance is 99:1. The QC page surfaces data quality issues that could invalidate results.

### Components

| Visualization | Purpose |
|--------------|---------|
| Class Balance | Bar chart with percentage labels — identifies severe imbalance |
| Label × Cancer Type Sunburst | Nested breakdown showing which tumor types contribute to each label |
| Cancer Type Distribution | Top-15 cancer types — identifies cohort composition |
| Panel/Assay Distribution | Sequencing panel version distribution — identifies technical batch effects |
| Feature Missingness | Bar chart of features with >0% missing values — sorted by severity |
| Zero-Variance Alert | Value box counting features with zero variance — red if any exist |
| Per-Sample Feature Coverage | Histogram of % non-null features per sample — identifies low-quality samples |
| Per-Chromosome Features | If available, shows chromosome-level feature means — identifies genomic biases |

---

## Page 6: Data Explorer

### Two views

1. **great_tables grouped view**: Auto-detects feature families from column name prefixes and renders column spanners. Dark-themed to match the dashboard. Shows first 200 rows for rendering performance.

2. **itables searchable view**: Full dataset with pagination, search box, and CSV/Excel/copy export buttons.

---

## Sidebar: Glossary

Concise definitions of the five ctDNA labels used in analysis, plus the `Undetermined` label (excluded from ML). Also documents the 80/20 train/test split for holdout evaluation. Kept minimal to avoid cognitive overload.

---

## Multimodal Dashboard (v0.0.20+)

The multimodal template extends the single-evaluator dashboard with:

- **Title**: "Kreview Multimodal Intelligence Dashboard" (distinct from single-evaluator)
- **Selection Strategy** value box showing whether `mi` or `boruta_shap` was used
- **Stacking vs Raw comparison chart**: grouped bar chart comparing `stacking_*` vs `raw_*` model AUCs with Δ annotations showing the lift from stacking
- **Extended model discovery**: dynamically discovers `stacking_lr`, `stacking_rf`, `raw_lr`, `raw_xgb`, etc.
- **Nested CV indicator**: shows whether ablation-based nested CV was used

---

## Accessibility

- **CVD-safe mode**: Use `--cvd-safe` flag to switch to Okabe-Ito palette for red-green colorblind accessibility
- **Print mode**: `@media print` CSS rules switch to white background/dark text for PDF export
- **Marker shapes**: Scatter plots use both color and symbol to encode categories
