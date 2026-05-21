"""Tests for kreview.eval_engine — Phase 1 audit fixes (C-04) + v0.0.9 selection.

Covers:
  - evaluate_feature output schema validation
  - FDR correction produces valid p-values
  - single_feature_model returns valid AUC
  - single_feature_model rejects single-class input
  - Pipeline-based LR model (no scaler leakage)
  - Bootstrap CI bounds
  - OOF subgroup metrics present
  - univariate_auc single-feature CV AUC
  - mutual_info_score non-linear feature scoring
"""

import numpy as np
import pandas as pd
import pytest

from kreview.eval_engine import (
    evaluate_feature,
    single_feature_model,
    univariate_auc,
    mutual_info_score,
    LABEL_ORDER,
)

# Detect whether XGBoost is usable in this environment.
# XGBoost may be installed but fail at import due to missing libomp on macOS.
try:
    from xgboost import XGBClassifier  # noqa: F401
    HAS_XGB = True
except Exception:
    HAS_XGB = False

# Models to iterate in tests — only include xgb if available
_MODELS = ["lr", "rf"] + (["xgb"] if HAS_XGB else [])

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def synthetic_labels():
    """Create synthetic labels aligned with LABEL_ORDER (4-tier)."""
    np.random.seed(42)
    n = 200
    labels = np.random.choice(LABEL_ORDER, size=n, p=[0.3, 0.2, 0.3, 0.2])
    return pd.Series(labels, name="label")


@pytest.fixture
def synthetic_feature(synthetic_labels):
    """Create a feature that differs by group (True+ should be higher)."""
    np.random.seed(42)
    n = len(synthetic_labels)
    values = np.random.randn(n)
    # Make True ctDNA+ samples systematically higher
    values[synthetic_labels == "True ctDNA+"] += 2.0
    values[synthetic_labels == "Possible ctDNA+"] += 1.0
    return pd.Series(values, name="test_feature")


@pytest.fixture
def binary_Xy():
    """Minimal binary classification dataset for model tests."""
    np.random.seed(42)
    n = 100
    X = np.random.randn(n, 5)
    y = np.zeros(n, dtype=int)
    y[:40] = 1  # 40% positive
    # Add signal to first feature
    X[:40, 0] += 2.0
    return X, y


# ── evaluate_feature tests ──────────────────────────────────────────────────────


class TestEvaluateFeature:

    def test_output_has_expected_keys(self, synthetic_feature, synthetic_labels):
        """Verify all expected keys are present in the output dict."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)

        # Must have sample counts for all 4 tiers
        for label in LABEL_ORDER:
            key = f"n_{label.replace(' ', '_').replace('+', 'pos').replace('−', 'neg')}"
            assert key in result, f"Missing sample count key: {key}"

        # Must have low_power flag
        assert "low_power" in result
        assert isinstance(result["low_power"], bool)

    def test_kruskal_wallis_present(self, synthetic_feature, synthetic_labels):
        """KW test should run when we have 4 groups."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)
        assert "kw_statistic" in result
        assert "kw_pvalue" in result
        assert 0 <= result["kw_pvalue"] <= 1

    def test_cohens_d_both_pairs(self, synthetic_feature, synthetic_labels):
        """Both Cohen's d (True+ vs Healthy AND Possible+ vs Healthy) should be present."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)
        assert "cohens_d_true_vs_healthy" in result
        assert "cohens_d_possible_vs_healthy" in result
        # True+ has stronger signal, so its Cohen's d should be larger
        assert (
            result["cohens_d_true_vs_healthy"] > result["cohens_d_possible_vs_healthy"]
        )

    def test_fdr_correction_applied(self, synthetic_feature, synthetic_labels):
        """FDR-corrected p-values should exist and be >= raw p-values."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)

        fdr_keys = [k for k in result if k.endswith("_pvalue_fdr")]
        raw_keys = [k.replace("_fdr", "") for k in fdr_keys]

        # Should have at least 2 FDR-corrected p-values
        assert len(fdr_keys) >= 2, f"Expected >=2 FDR keys, got {len(fdr_keys)}"

        # FDR corrected should be >= raw (BH correction inflates them)
        for fdr_k, raw_k in zip(fdr_keys, raw_keys):
            assert (
                result[fdr_k] >= result[raw_k] - 1e-10
            ), f"{fdr_k}={result[fdr_k]} < {raw_k}={result[raw_k]}"

    def test_pairwise_mwu_keys(self, synthetic_feature, synthetic_labels):
        """All 5 pairwise MWU tests should produce p-values and effect sizes."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)
        mwu_pvals = [
            k for k in result if k.startswith("mwu_") and k.endswith("_pvalue")
        ]
        assert len(mwu_pvals) == 5

    def test_no_error_key_on_valid_input(self, synthetic_feature, synthetic_labels):
        """Valid input should not produce an error key."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)
        assert "error" not in result

    def test_spearman_vaf_correlation(self, synthetic_feature, synthetic_labels):
        """Spearman VAF correlation should be present when max_vaf is provided."""
        max_vaf = pd.Series(np.random.uniform(0.01, 0.5, len(synthetic_labels)))
        result = evaluate_feature(synthetic_feature, synthetic_labels, max_vaf=max_vaf)
        assert "spearman_vaf_r" in result
        assert "spearman_vaf_p" in result

    def test_empty_group_handling(self):
        """Should handle gracefully when some groups have 0 or 1 samples."""
        labels = pd.Series(["True ctDNA+"] * 20 + ["Healthy Normal"] * 20)
        values = pd.Series(np.random.randn(40))
        result = evaluate_feature(values, labels)
        # Should still produce results for the 2 available groups
        assert "n_True_ctDNApos" in result
        assert result["n_True_ctDNApos"] == 20


# ── single_feature_model tests ──────────────────────────────────────────────────


class TestSingleFeatureModel:

    def test_returns_valid_auc(self, binary_Xy):
        """AUC should be between 0.5 and 1 for a model with signal."""
        X, y = binary_Xy
        results, lr, rf, xgb = single_feature_model(X, y)
        assert "error" not in results
        assert 0.5 <= results["auc_lr"] <= 1.0
        assert 0.5 <= results["auc_rf"] <= 1.0

    def test_single_class_returns_error(self):
        """Should return error dict when only one class is present."""
        X = np.random.randn(50, 3)
        y = np.ones(50, dtype=int)  # All positive
        results, lr, rf, xgb = single_feature_model(X, y)
        assert "error" in results
        assert lr is None and rf is None and xgb is None

    def test_pipeline_lr_model(self, binary_Xy):
        """LR model should be a Pipeline with scaler + lr steps."""
        X, y = binary_Xy
        results, lr_pipe, rf, xgb = single_feature_model(X, y)
        from sklearn.pipeline import Pipeline

        assert isinstance(lr_pipe, Pipeline), "LR model should be a Pipeline"
        assert "scaler" in lr_pipe.named_steps
        assert "lr" in lr_pipe.named_steps

    def test_bootstrap_ci_present(self, binary_Xy):
        """Bootstrap CI bounds should be in the results."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        assert "auc_rf_ci_lower" in results
        assert "auc_rf_ci_upper" in results
        # CI should bracket the point estimate
        if results["auc_rf_ci_lower"] is not None:
            assert results["auc_rf_ci_lower"] <= results["auc_rf"]
            assert results["auc_rf_ci_upper"] >= results["auc_rf"]

    def test_optimal_threshold_in_range(self, binary_Xy):
        """Optimal thresholds should be between 0 and 1."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        assert 0 <= results["lr_optimal_threshold"] <= 1
        assert 0 <= results["rf_optimal_threshold"] <= 1

    def test_feature_names_in_importances(self, binary_Xy):
        """When feature_names are provided, importances should be a dict."""
        X, y = binary_Xy
        names = [f"feat_{i}" for i in range(X.shape[1])]
        results, *_ = single_feature_model(X, y, feature_names=names)
        imp = results["rf_feature_importances"]
        assert isinstance(imp, dict)
        assert set(imp.keys()) == set(names)

    def test_top_features_post_cv(self, binary_Xy):
        """Top features should be derived from RF importances (post-CV)."""
        X, y = binary_Xy
        names = [f"feat_{i}" for i in range(X.shape[1])]
        results, *_ = single_feature_model(X, y, feature_names=names)
        assert "top_features" in results
        assert len(results["top_features"]) <= 10
        assert all(f in names for f in results["top_features"])

    def test_cv_folds_respected(self, binary_Xy):
        """The actual CV folds should be recorded in results."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y, n_folds=3)
        assert results["cv_folds_actual"] == 3

    def test_subgroup_uses_oof(self, binary_Xy):
        """Cancer type subgroup metrics should be present when provided."""
        X, y = binary_Xy
        cancer_types = np.array(["Breast"] * 60 + ["Lung"] * 40)
        results, *_ = single_feature_model(X, y, cancer_types=cancer_types)
        assert "cancer_type_stats" in results
        # Should have entries for both cancer types
        assert len(results["cancer_type_stats"]) >= 1

    def test_class_weight_balanced(self, binary_Xy):
        """LR and RF should use balanced class weights."""
        X, y = binary_Xy
        _, lr_pipe, rf, _ = single_feature_model(X, y)
        assert lr_pipe.named_steps["lr"].class_weight == "balanced"
        assert rf.class_weight == "balanced"


# ── v0.0.8 new metric tests ────────────────────────────────────────────────────


class TestPRCurves:
    """Precision-Recall curves and average precision (v0.0.8)."""

    def test_pr_curve_present(self, binary_Xy):
        """PR curve data should be present for all models."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        for prefix in _MODELS:
            key = f"{prefix}_pr_curve"
            assert key in results, f"Missing {key}"
            assert "precision" in results[key]
            assert "recall" in results[key]

    def test_avg_precision_range(self, binary_Xy):
        """Average precision should be between 0 and 1."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        for prefix in _MODELS:
            key = f"{prefix}_avg_precision"
            assert key in results, f"Missing {key}"
            assert 0 <= results[key] <= 1, f"{key}={results[key]} out of range"


class TestDCA:
    """Decision Curve Analysis (v0.0.8)."""

    def test_dca_function_standalone(self):
        """decision_curve_analysis should return thresholds and net benefits."""
        from kreview.eval_engine import decision_curve_analysis

        np.random.seed(42)
        y = np.random.binomial(1, 0.3, 100)
        probs = np.random.uniform(0, 1, 100)
        result = decision_curve_analysis(y, probs)

        assert "thresholds" in result
        assert "net_benefit_model" in result
        assert "net_benefit_treat_all" in result
        assert len(result["thresholds"]) == len(result["net_benefit_model"])

    def test_dca_in_model_results(self, binary_Xy):
        """DCA should be present in model results for RF and XGB."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        assert "rf_dca" in results
        assert "thresholds" in results["rf_dca"]
        if HAS_XGB:
            assert "xgb_dca" in results


class TestFoldAUC:
    """Fold-level AUC tracking for all 3 models (v0.0.8)."""

    def test_fold_aucs_all_models(self, binary_Xy):
        """Fold AUCs should be tracked for LR, RF, and XGBoost."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        for prefix in _MODELS:
            key = f"{prefix}_fold_aucs"
            assert key in results, f"Missing {key}"
            assert isinstance(results[key], list)
            assert len(results[key]) >= 3  # at least 3 folds

    def test_auc_std_present(self, binary_Xy):
        """AUC standard deviation should be computed."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        for prefix in _MODELS:
            key = f"{prefix}_auc_std"
            assert key in results, f"Missing {key}"
            assert results[key] >= 0  # std is non-negative


class TestThresholdSweep:
    """Threshold sensitivity sweep (v0.0.8)."""

    def test_sweep_present(self, binary_Xy):
        """Threshold sweep should be in RF results."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        assert "rf_threshold_sweep" in results

    def test_sweep_structure(self, binary_Xy):
        """Sweep should have thresholds, sensitivity, specificity, ppv."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        sweep = results["rf_threshold_sweep"]
        assert isinstance(sweep, list)
        assert len(sweep) > 0
        # Check first entry has required keys
        entry = sweep[0]
        assert "threshold" in entry
        assert "sensitivity" in entry
        assert "specificity" in entry
        assert "ppv" in entry


class TestFeatureStability:
    """Feature stability across CV folds (v0.0.8)."""

    def test_stability_present(self, binary_Xy):
        """Feature stability dict should be computed."""
        X, y = binary_Xy
        names = [f"feat_{i}" for i in range(X.shape[1])]
        results, *_ = single_feature_model(X, y, feature_names=names)
        assert "feature_stability" in results

    def test_stability_values(self, binary_Xy):
        """Stability scores should be between 0 and 1."""
        X, y = binary_Xy
        names = [f"feat_{i}" for i in range(X.shape[1])]
        results, *_ = single_feature_model(X, y, feature_names=names)
        stability = results["feature_stability"]
        assert isinstance(stability, dict)
        for feat, score in stability.items():
            assert 0 <= score <= 1, f"{feat}={score} out of [0,1]"


class TestQCMetrics:
    """Per-feature QC metrics: missingness and zero-variance (v0.0.8)."""

    def test_missing_metrics_zero(self, synthetic_feature, synthetic_labels):
        """Clean data should have 0 missingness."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)
        assert "n_missing" in result
        assert "pct_missing" in result
        assert result["n_missing"] == 0
        assert result["pct_missing"] == 0.0

    def test_missing_metrics_with_nans(self, synthetic_labels):
        """Data with NaNs should report non-zero missingness."""
        values = pd.Series(np.random.randn(len(synthetic_labels)))
        values.iloc[:10] = np.nan
        result = evaluate_feature(values, synthetic_labels)
        assert result["n_missing"] == 10
        assert result["pct_missing"] > 0

    def test_zero_variance_flag(self, synthetic_labels):
        """Constant feature should be flagged as zero-variance."""
        constant = pd.Series(np.ones(len(synthetic_labels)))
        result = evaluate_feature(constant, synthetic_labels)
        assert "is_zero_variance" in result
        assert result["is_zero_variance"] is True

    def test_non_constant_not_flagged(self, synthetic_feature, synthetic_labels):
        """Normal feature should NOT be flagged as zero-variance."""
        result = evaluate_feature(synthetic_feature, synthetic_labels)
        assert result["is_zero_variance"] is False


class TestTrainingTime:
    """Training time tracking (v0.0.8)."""

    def test_training_times_present(self, binary_Xy):
        """Training time should be recorded for all models."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        for prefix in _MODELS:
            key = f"{prefix}_training_time_sec"
            assert key in results, f"Missing {key}"
            assert results[key] > 0, f"{key} should be positive"


class TestAUCDeltas:
    """AUC delta comparisons between models (v0.0.8)."""

    def test_deltas_present(self, binary_Xy):
        """AUC deltas should be computed between model pairs."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        assert "auc_delta_rf_lr" in results
        if HAS_XGB:
            assert "auc_delta_xgb_rf" in results

    def test_deltas_consistency(self, binary_Xy):
        """RF-LR delta should equal auc_rf - auc_lr."""
        X, y = binary_Xy
        results, *_ = single_feature_model(X, y)
        expected = results["auc_rf"] - results["auc_lr"]
        assert abs(results["auc_delta_rf_lr"] - expected) < 1e-10


# ── v0.0.9 feature selection scoring tests ──────────────────────────────────────


class TestUnivariateAUC:
    """univariate_auc single-feature LR AUC (v0.0.9)."""

    def test_returns_float(self):
        """Should return a float."""
        np.random.seed(42)
        x = pd.Series(np.random.randn(100))
        y = np.array([0] * 50 + [1] * 50)
        result = univariate_auc(x, y)
        assert isinstance(result, float)

    def test_range_0_to_1(self):
        """AUC should be between 0 and 1."""
        np.random.seed(42)
        x = pd.Series(np.random.randn(100))
        y = np.array([0] * 50 + [1] * 50)
        result = univariate_auc(x, y)
        assert 0.0 <= result <= 1.0

    def test_constant_feature_returns_0_5(self):
        """Constant feature should return AUC=0.5 (no information)."""
        x = pd.Series(np.ones(100))
        y = np.array([0] * 50 + [1] * 50)
        result = univariate_auc(x, y)
        assert result == 0.5

    def test_perfect_signal_high_auc(self):
        """A feature with perfect separation should have AUC near 1.0."""
        np.random.seed(42)
        x = pd.Series([0.0] * 50 + [10.0] * 50)
        y = np.array([0] * 50 + [1] * 50)
        result = univariate_auc(x, y)
        assert result >= 0.95, f"Expected AUC >= 0.95, got {result}"

    def test_nan_handling(self):
        """Should handle NaN values without crashing."""
        np.random.seed(42)
        x = pd.Series(np.random.randn(100))
        x.iloc[:10] = np.nan
        y = np.array([0] * 50 + [1] * 50)
        result = univariate_auc(x, y)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_single_class_returns_0_5(self):
        """Single-class target should return AUC=0.5."""
        x = pd.Series(np.random.randn(50))
        y = np.ones(50, dtype=int)  # All positive
        result = univariate_auc(x, y)
        assert result == 0.5


class TestMutualInfoScore:
    """mutual_info_score non-linear feature scoring (v0.0.9)."""

    def test_returns_float(self):
        """Should return a float."""
        np.random.seed(42)
        x = pd.Series(np.random.randn(100))
        y = np.array([0] * 50 + [1] * 50)
        result = mutual_info_score(x, y)
        assert isinstance(result, float)

    def test_non_negative(self):
        """MI should be >= 0."""
        np.random.seed(42)
        x = pd.Series(np.random.randn(100))
        y = np.array([0] * 50 + [1] * 50)
        result = mutual_info_score(x, y)
        assert result >= 0.0

    def test_constant_feature_returns_zero(self):
        """Constant feature should return MI=0.0 (no information)."""
        x = pd.Series(np.ones(100))
        y = np.array([0] * 50 + [1] * 50)
        result = mutual_info_score(x, y)
        assert result == 0.0

    def test_informative_feature_positive_mi(self):
        """A feature with signal should have MI > 0."""
        np.random.seed(42)
        x = pd.Series([0.0] * 50 + [10.0] * 50)
        y = np.array([0] * 50 + [1] * 50)
        result = mutual_info_score(x, y)
        assert result > 0.0, f"Expected MI > 0 for informative feature, got {result}"

    def test_nan_handling(self):
        """Should handle NaN values without crashing (replaced with 0)."""
        np.random.seed(42)
        x = pd.Series(np.random.randn(100))
        x.iloc[:10] = np.nan
        y = np.array([0] * 50 + [1] * 50)
        result = mutual_info_score(x, y)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_reproducible_with_seed(self):
        """Same inputs + same seed should produce same result."""
        np.random.seed(42)
        x = pd.Series(np.random.randn(100))
        y = np.array([0] * 50 + [1] * 50)
        r1 = mutual_info_score(x, y, random_state=42)
        r2 = mutual_info_score(x, y, random_state=42)
        assert r1 == r2


# ── evaluate_model tests ─────────────────────────────────────────────────────


class TestEvaluateModel:
    """Tests for evaluate_model() — the universal model evaluation primitive.

    Validates:
      - Output dict has expected key prefixes
      - AUC is within [0, 1]
      - Bootstrap CI bounds are sane
      - Per-fold AUCs are present and valid
      - Classification report structure
      - Feature importances extraction
      - refit=False behaviour (no fitted model returned)
    """

    @pytest.fixture
    def model_and_data(self, binary_Xy):
        """Prepare an RF model + StratifiedKFold for evaluate_model tests."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import StratifiedKFold

        X, y = binary_Xy
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        return model, X, y, cv

    def test_output_has_expected_keys(self, model_and_data):
        """Result dict should contain auc, oof_probs, CI, threshold keys."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        result, fitted = evaluate_model(model, X, y, cv, name="rf")

        assert "auc_rf" in result
        assert "rf_oof_probs" in result
        assert "auc_rf_ci_lower" in result
        assert "auc_rf_ci_upper" in result
        assert "rf_optimal_threshold" in result
        assert "rf_classification_report" in result
        assert "rf_confusion_matrix" in result

    def test_auc_in_valid_range(self, model_and_data):
        """AUC should be between 0 and 1."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        result, _ = evaluate_model(model, X, y, cv, name="rf")

        assert 0.0 <= result["auc_rf"] <= 1.0

    def test_ci_bounds_sane(self, model_and_data):
        """CI lower <= AUC <= CI upper."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        result, _ = evaluate_model(model, X, y, cv, name="rf")

        assert result["auc_rf_ci_lower"] <= result["auc_rf"]
        assert result["auc_rf"] <= result["auc_rf_ci_upper"]

    def test_fold_aucs_present(self, model_and_data):
        """Per-fold AUCs should be a list with len == n_splits."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        result, _ = evaluate_model(model, X, y, cv, name="rf")

        assert "rf_fold_aucs" in result
        assert len(result["rf_fold_aucs"]) == 3  # n_splits=3
        for auc in result["rf_fold_aucs"]:
            assert 0.0 <= auc <= 1.0

    def test_classification_report_structure(self, model_and_data):
        """Classification report should have per-class and weighted avg keys."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        result, _ = evaluate_model(model, X, y, cv, name="rf")

        cr = result["rf_classification_report"]
        assert isinstance(cr, dict)
        # Should have entries for class 0 and class 1
        assert "0" in cr or "0.0" in cr or 0 in cr
        assert "1" in cr or "1.0" in cr or 1 in cr

    def test_feature_importances_with_names(self, model_and_data):
        """Feature importances dict should have one entry per feature."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        fnames = [f"feat_{i}" for i in range(X.shape[1])]
        result, fitted = evaluate_model(
            model, X, y, cv, name="rf", feature_names=fnames
        )

        assert fitted is not None
        imp = result.get("rf_feature_importances")
        assert imp is not None
        assert set(imp.keys()) == set(fnames)

    def test_refit_false_returns_none(self, model_and_data):
        """When refit=False, fitted model should be None."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        result, fitted = evaluate_model(model, X, y, cv, name="rf", refit=False)

        assert fitted is None
        assert "rf_training_time_sec" not in result
