# Sklearn Models & Metrics

Every feature evaluator undergoes automated ensemble classification to measure how well a cfDNA feature set discriminates ctDNA-positive from ctDNA-negative samples.

Inside `single_feature_model()`, three classifier families are evaluated using stratified cross-validation against a binary label derived from the [ctDNA labeling engine](../biology/ctdna-labeling.md).

---

## The Predictive Ensemble

Three classifier families are trained on every feature set:

```python
# 1. Linear Baseline (Logistic Regression)
lr = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"))
])

# 2. Tree-Based (Random Forest)
rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=5,
    min_samples_leaf=max(1, min(10, len(y) // 10)),
    random_state=42,
    class_weight="balanced",
)

# 3. Gradient Boosting (XGBoost)
xgb = XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    eval_metric="logloss",
    use_label_encoder=False,
)
```

!!! note "Graceful Degradation"
    XGBoost is imported dynamically with a `try/except`. If `xgboost` is unavailable (common in restricted HPC environments), the engine safely falls back to Random Forest and Logistic Regression only.

### Class Imbalance & CV Strategy

Clinical cohorts are typically imbalanced (e.g. 4,000 cancer patients vs 300 healthy controls). To prevent majority-class bias, the pipeline uses **Stratified K-Fold Cross Validation**:

```python
cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
rf_probs = cross_val_predict(rf, X, y, cv=cv, method="predict_proba")
```

The number of folds is dynamically bounded by the minimum class size to prevent `n_splits` errors. All downstream metrics use **out-of-fold predictions** — the model never evaluates samples it trained on.

---

## Metric Categories (9 total)

### 1. ROC-AUC & Bootstrap CIs

The primary scoring metric. To quantify uncertainty, kreview computes **bootstrap 95% confidence intervals** (`n_resamples=1000`) for every AUC score. Results are stored as `auc_rf`, `auc_rf_ci_lower`, `auc_rf_ci_upper`.

### 2. Precision-Recall (PR) Curves

PR curves are more informative than ROC when the positive class is rare. kreview computes precision-recall curves and average precision (AP) for all three models. PR data is stored as `{prefix}_pr_curve` and `{prefix}_avg_precision`.

### 3. Probability Calibration

Tree-based models (RF, XGBoost) tend to produce poorly calibrated probabilities. kreview computes `sklearn` calibration curves (`prob_true` vs `prob_pred`) in 10 uniform bins. Stored as `rf_calibration`.

### 4. Optimal Thresholding (Youden's J)

A continuous probability doesn't translate to a clinical decision. kreview calculates the binary cutoff that maximizes the separation between True Positive Rate and False Positive Rate:

$$J = \max(TPR - FPR)$$

```python
optimal_idx = np.argmax(tpr - fpr)  # Youden's J Statistic
optimal_threshold = float(thresholds[optimal_idx])
```

This threshold generates the `classification_report` and `confusion_matrix` for each model.

### 5. Threshold Sensitivity Sweep

A single optimal threshold may be fragile. kreview evaluates sensitivity, specificity, and PPV across 50 thresholds (0.01–0.99) for the RF model. This helps clinicians choose an operating point based on their risk tolerance. Stored as `rf_threshold_sweep`.

### 6. Decision Curve Analysis (DCA)

DCA computes the **net clinical benefit** of using the model vs treating all or treating none. See the [full DCA methodology guide](decision-curve-analysis.md).

Stored as `rf_dca` and `xgb_dca`.

### 7. Fold-Level AUC Tracking

To assess model stability, kreview runs `cross_val_score` separately and stores per-fold AUC for all three models. A high standard deviation (>0.05) suggests the model is data-sensitive. Stored as `{prefix}_fold_aucs` and `{prefix}_auc_std`.

### 8. SHAP Explainability

For RF and XGBoost, kreview generates **SHAP (SHapley Additive exPlanations)** values using `TreeExplainer`:

- **Beeswarm Plot:** Global feature importance ranked by mean |SHAP|, colored by feature value
- **Dependence Scatter:** Feature value vs SHAP impact, colored by an interacting feature
- **Waterfall Plots:** Per-sample prediction decomposition for the most confident TP and FP

!!! warning "Interpretation"
    SHAP explains how the model decides, not biological causality. A feature with high SHAP impact may reflect a data artifact rather than a biological mechanism.

### 9. Subgroup Analysis (Out-Of-Fold)

After training, the pipeline evaluates model sensitivity across biological subgroups using **out-of-fold predictions** (preventing optimistic bias):

- **Cancer Type Stats:** Sensitivity per cancer type (top 10 by sample count)
- **Assay Stats:** Sensitivity stratified by ACCESS panel version (e.g. ACCESS129 vs ACCESS146)

Serialized into the results JSON under `cancer_type_stats` and `assay_stats`.

---

## QC Metrics

For every feature, `evaluate_feature()` also computes data quality metrics:

| Metric | Field | Purpose |
|--------|-------|---------|
| Missing count | `n_missing` | Number of NaN values |
| Missing percentage | `pct_missing` | Percentage of samples with NaN |
| Zero variance | `is_zero_variance` | Whether `std == 0` (constant feature) |

These are surfaced in the dashboard's **Cohort & QC** page and the statistical ledger.

---

## Feature Stability

To assess whether the same features are consistently ranked as important across different data splits, kreview trains a fresh RF on each CV fold's training set and records which features appear in the top-10 by Gini importance. The result is a score from 0.0 (never in top-10) to 1.0 (always in top-10). Stored as `feature_stability`.

---

## Visualization Themes

!!! tip "CVD-Safe Mode"
    Use the `--cvd-safe` flag to switch from the default neon palette to the Okabe-Ito color scheme, which is accessible for red-green colorblindness. The default palette uses curated colors optimized for dark backgrounds.

---

## JSON Output Schema Summary

`single_feature_model()` produces **44 JSON fields** per feature set:

| Category | Fields | Count |
|----------|--------|-------|
| AUC & CI | `auc_{lr,rf,xgb}`, `auc_*_ci_lower`, `auc_*_ci_upper` | 9 |
| Classification | `*_classification_report`, `*_confusion_matrix` | 6 |
| Thresholds | `*_optimal_threshold` | 3 |
| PR Curves | `*_pr_curve`, `*_avg_precision` | 6 |
| DCA | `rf_dca`, `xgb_dca` | 2 |
| Fold AUCs | `*_fold_aucs`, `*_auc_std` | 6 |
| Calibration | `rf_calibration` | 1 |
| Threshold Sweep | `rf_threshold_sweep` | 1 |
| Feature Stability | `feature_stability` | 1 |
| Training Time | `*_training_time_sec` | 3 |
| Feature Importances | `rf_feature_importances`, `top_features` | 2 |
| AUC Deltas | `auc_delta_rf_lr`, `auc_delta_xgb_rf` | 2 |
| Subgroups | `cancer_type_stats`, `assay_stats` | 2 |
