# Sklearn Models & Metrics

Every feature evaluator is pushed from non-parametric statistical checking into a brute-force Machine Learning predictor.

Inside `single_feature_model()`, we orchestrate an automated ensemble tournament to see how well a physical cfDNA feature can classify cancer mathematically.

---

## 🏗️ The Predictive Ensemble

We run three distinctly bounded classification models against every feature:

```python
# 1. Linear Baseline (Logistic Regression)
lr = LogisticRegression(max_iter=1000, random_state=42)
X_scaled = scaler.fit_transform(X)  # Standardized L2 Regression

# 2. Decision Tree Bounds (Random Forest)
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
    Because XGBoost binaries can occasionally break in rigid HPC environments, the code uses a `try / except` to import it dynamically. If `xgboost` fails to import, the engine safely degrades to Random Forest only.

### Class Imbalance & CV Strategy

Often, we have 4,000 cancer patient samples but only 300 healthy normal controls. To prevent the models from blindly predicting cancer 100% of the time, we enforce **Stratified K-Fold Cross Validation**:

```python
cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
rf_probs = cross_val_predict(rf, X, y, cv=cv, method="predict_proba")
```

The number of folds is dynamically bounded by the minimum class size to prevent `n_splits` errors.

---

## 📈 Metric Outputs

### 1. ROC-AUC 

The core scoring mechanism is the Area Under the ROC Curve:

$$ \text{AUC} \rightarrow 1.0 \text{ (Perfect Diagnostics)} $$
$$ \text{AUC} \rightarrow 0.5 \text{ (Random Coin Flip)} $$

We calculate `.auc_lr`, `.auc_rf`, and `.auc_xgb`, then compute deltas:

- `auc_delta_rf_lr` — Did nonlinear tree splitting help over the linear baseline?
- `auc_delta_xgb_rf` — Did gradient boosting improve over bagging?

### 2. Optimal Thresholding (Youden's J)

A continuous probability threshold doesn't help an oncologist. We dynamically calculate the binary cutoff that maximizes the separation between True Positive Rate and False Positive Rate:

```math
J = \max(TPR - FPR)
```

```python
optimal_idx = np.argmax(tpr - fpr)  # Youden's J Statistic
optimal_threshold = float(thresholds[optimal_idx])
```

This threshold is then used to generate the `classification_report` and `confusion_matrix`.

### 3. SHAP Explainability

For both RF and XGB, `kreview` generates **SHAP (SHapley Additive exPlanations)** visualizations:

- **Beeswarm Plot:** Shows the global importance of each sub-metric and how it pushes predictions positive or negative.
- **Dependence Scatter:** Shows how a single feature interacts with color-coded label groups.
- **Waterfall Plots:** Side-by-side visualization of the highest True Positive and highest False Positive patients, revealing exactly which sub-metrics drove the model's decision.

The dashboard renders RF and XGB in sequential full-width rows for maximum readability.

### 4. Subgroup Analysis

After training, the pipeline evaluates model sensitivity across biological subgroups:

- **Cancer Type Stats:** Sensitivity per cancer type (top 10 by sample count), for both RF and XGB.
- **Assay Stats:** Sensitivity stratified by ACCESS panel version (e.g., ACCESS129 vs ACCESS146).

These are serialized into the `stats.json` output under `cancer_type_stats` and `assay_stats`.
