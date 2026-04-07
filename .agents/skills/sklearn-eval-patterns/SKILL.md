---
name: sklearn-eval-patterns
description: scikit-learn patterns for single-feature LR and RF evaluation with cross-validation and AUC scoring.
---

# sklearn Evaluation Patterns

## When to use this skill
- Implementing the single-feature modeling pipeline
- Adding new model types to the evaluation
- Debugging CV or AUC computation issues

## Standard Pattern
```python
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

def single_feature_model(X, y, n_folds=5):
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    # LR (needs scaling)
    X_scaled = StandardScaler().fit_transform(X)
    lr_probs = cross_val_predict(
        LogisticRegression(max_iter=1000, random_state=42),
        X_scaled, y, cv=cv, method="predict_proba",
    )[:, 1]

    # RF (no scaling needed)
    rf_probs = cross_val_predict(
        RandomForestClassifier(
            n_estimators=100, max_depth=5, min_samples_leaf=10,
            class_weight="balanced", random_state=42,
        ),
        X, y, cv=cv, method="predict_proba",
    )[:, 1]

    return {
        "auc_lr": roc_auc_score(y, lr_probs),
        "auc_rf": roc_auc_score(y, rf_probs),
    }
```

## Three Standard Comparisons
1. True ctDNA+ vs Healthy Normal (ceiling AUC)
2. Possible ctDNA+ vs Healthy Normal (realistic AUC)
3. (True + Possible ctDNA+) vs Possible ctDNA− (can fragments beat variants?)

## Anti-Patterns
- ❌ Training on the full dataset without CV — always use StratifiedKFold
- ❌ Forgetting `class_weight="balanced"` — groups are heavily imbalanced
- ❌ Not scaling for LR — LR is sensitive to feature scale
- ❌ Using `max_depth=None` for RF — will overfit on small strata
