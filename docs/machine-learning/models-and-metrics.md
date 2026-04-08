# Sklearn Models & Metrics

Every feature evaluator is pushed linearly from non-parametric statistical checking into a brute-force Machine Learning predictor.

Inside `single_feature_model()`, we orchestrate an automated ensemble tournament to see how well the physical cfDNA feature can classify cancer mathematically.

---

## 🏗️ The Predictive Ensemble

We run three distinctly bounded classification models against every piece of data.

```python
# 1. Linear Baseline (Logistic Regression)
lr = LogisticRegression(max_iter=1000)
X_scaled = scaler.fit_transform(X) # Standardized L2 Regression

# 2. Decision Tree Bounds (Random Forest)
rf = RandomForestClassifier(n_estimators=100, class_weight="balanced")

# 3. Aggressive Boost (XGBoost)
xgb = XGBClassifier(learning_rate=0.1, eval_metric="logloss")
```
_Note: Because XGBoost binaries often break heavily in rigid HPC environments, the Python code explicitly uses a `try / except` to load it dynamically. If `xgboost` fails to import, the engine safely degrades down to `RandomForest`._

### Class Imbalance & CV Strategy
Often, we have 4,000 cancer patient samples, but only 300 healthy normal controls. To prevent our standard `RandomForest` from blindly predicting cancer 100% of the time, we enforce **Stratified K-Fold Cross Validation** (`StratifiedKFold`). 

We define the folds dynamically bounded by the minimum class representation to prevent `n_splits` errors:
```python
cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
rf_probs = cross_val_predict(rf, X, y, cv=cv, method="predict_proba")
```

---

## 📈 Metric Outputs

### 1. ROC-AUC 
The core scoring mechanism is the Area Under the Receiver Operating Characteristic Curve (AUC).

$$ \text{AUC} \rightarrow 1.0 \text{ (Perfect Diagnostics)} $$
$$ \text{AUC} \rightarrow 0.5 \text{ (Random Coin Flip)} $$

We calculate `.auc_lr`, `.auc_rf`, and `.auc_xgb`, and then compute `.auc_delta_rf_lr` to see if a feature significantly benefited from non-linear separation!

### 2. Optimal Thresholding (Youden's J)
A continuous probability threshold doesn't help an oncologist. 

Therefore, we dynamically calculate the perfect binary cutoff threshold by mapping the curve where the derivative between True Positive Rate and False Positive Rate is maximized:
```python
optimal_idx = np.argmax(tpr - fpr) # Youden's J Statistic bounds
optimal_threshold = float(thresholds[optimal_idx])
```

This derived cut-point is then evaluated to print the specific diagnostic `classification_report` and `confusion_matrix`.
