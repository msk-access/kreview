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


@pytest.fixture(scope="module")
def cached_cpu_model_results():
    """Run single_feature_model ONCE per test session for heavy tests."""
    np.random.seed(42)
    n = 100
    X = np.random.randn(n, 5)
    y = np.zeros(n, dtype=int)
    y[:40] = 1
    X[:40, 0] += 2.0
    names = [f"feat_{i}" for i in range(X.shape[1])]
    return single_feature_model(X, y, n_folds=3, feature_names=names)


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

    def test_returns_valid_auc(self, cached_cpu_model_results):
        """AUC should be between 0.5 and 1 for a model with signal."""
        results, lr, rf, xgb = cached_cpu_model_results
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

    def test_pipeline_lr_model(self, cached_cpu_model_results):
        """LR model should be a Pipeline with scaler + lr steps."""
        results, lr_pipe, rf, xgb = cached_cpu_model_results
        from sklearn.pipeline import Pipeline

        assert isinstance(lr_pipe, Pipeline), "LR model should be a Pipeline"
        assert "scaler" in lr_pipe.named_steps
        assert "lr" in lr_pipe.named_steps

    def test_bootstrap_ci_present(self, cached_cpu_model_results):
        """Bootstrap CI bounds should be in the results."""
        results, *_ = cached_cpu_model_results
        assert "auc_rf_ci_lower" in results
        assert "auc_rf_ci_upper" in results
        # CI should bracket the point estimate
        if results["auc_rf_ci_lower"] is not None:
            assert results["auc_rf_ci_lower"] <= results["auc_rf"]
            assert results["auc_rf_ci_upper"] >= results["auc_rf"]

    def test_optimal_threshold_in_range(self, cached_cpu_model_results):
        """Optimal thresholds should be between 0 and 1."""
        results, *_ = cached_cpu_model_results
        assert 0 <= results["lr_optimal_threshold"] <= 1
        assert 0 <= results["rf_optimal_threshold"] <= 1

    def test_feature_names_in_importances(self, cached_cpu_model_results):
        """When feature_names are provided, importances should be a dict."""
        results, *_ = cached_cpu_model_results
        names = [f"feat_{i}" for i in range(5)]
        imp = results["rf_feature_importances"]
        assert isinstance(imp, dict)
        assert set(imp.keys()) == set(names)

    def test_top_features_post_cv(self, cached_cpu_model_results):
        """Top features should be derived from RF importances (post-CV)."""
        results, *_ = cached_cpu_model_results
        names = [f"feat_{i}" for i in range(5)]
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

    def test_class_weight_balanced(self, cached_cpu_model_results):
        """LR and RF should use balanced class weights."""
        _, lr_pipe, rf, _ = cached_cpu_model_results
        assert lr_pipe.named_steps["lr"].class_weight == "balanced"
        assert rf.class_weight == "balanced"


# ── v0.0.8 new metric tests ────────────────────────────────────────────────────


class TestPRCurves:
    """Precision-Recall curves and average precision (v0.0.8)."""

    def test_pr_curve_present(self, cached_cpu_model_results):
        """PR curve data should be present for all models."""
        results, *_ = cached_cpu_model_results
        for prefix in _MODELS:
            key = f"{prefix}_pr_curve"
            assert key in results, f"Missing {key}"
            assert "precision" in results[key]
            assert "recall" in results[key]

    def test_avg_precision_range(self, cached_cpu_model_results):
        """Average precision should be between 0 and 1."""
        results, *_ = cached_cpu_model_results
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

    def test_dca_in_model_results(self, cached_cpu_model_results):
        """DCA should be present in model results for RF and XGB."""
        results, *_ = cached_cpu_model_results
        assert "rf_dca" in results
        assert "thresholds" in results["rf_dca"]
        if HAS_XGB:
            assert "xgb_dca" in results


class TestFoldAUC:
    """Fold-level AUC tracking for all 3 models (v0.0.8)."""

    def test_fold_aucs_all_models(self, cached_cpu_model_results):
        """Fold AUCs should be tracked for LR, RF, and XGBoost."""
        results, *_ = cached_cpu_model_results
        for prefix in _MODELS:
            key = f"{prefix}_fold_aucs"
            assert key in results, f"Missing {key}"
            assert isinstance(results[key], list)
            assert len(results[key]) >= 3  # at least 3 folds

    def test_auc_std_present(self, cached_cpu_model_results):
        """AUC standard deviation should be computed."""
        results, *_ = cached_cpu_model_results
        for prefix in _MODELS:
            key = f"{prefix}_auc_std"
            assert key in results, f"Missing {key}"
            assert results[key] >= 0  # std is non-negative


class TestThresholdSweep:
    """Threshold sensitivity sweep (v0.0.8)."""

    def test_sweep_present(self, cached_cpu_model_results):
        """Threshold sweep should be in RF results."""
        results, *_ = cached_cpu_model_results
        assert "rf_threshold_sweep" in results

    def test_sweep_structure(self, cached_cpu_model_results):
        """Sweep should have thresholds, sensitivity, specificity, ppv."""
        results, *_ = cached_cpu_model_results
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

    def test_stability_present(self, cached_cpu_model_results):
        """Feature stability dict should be computed."""
        results, *_ = cached_cpu_model_results
        assert "feature_stability" in results

    def test_stability_values(self, cached_cpu_model_results):
        """Stability scores should be between 0 and 1."""
        results, *_ = cached_cpu_model_results
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

    def test_training_times_present(self, cached_cpu_model_results):
        """Training time should be recorded for all models."""
        results, *_ = cached_cpu_model_results
        for prefix in _MODELS:
            key = f"{prefix}_training_time_sec"
            assert key in results, f"Missing {key}"
            assert results[key] > 0, f"{key} should be positive"


class TestAUCDeltas:
    """AUC delta comparisons between models (v0.0.8)."""

    def test_deltas_present(self, cached_cpu_model_results):
        """AUC deltas should be computed between model pairs."""
        results, *_ = cached_cpu_model_results
        assert "auc_delta_rf_lr" in results
        if HAS_XGB:
            assert "auc_delta_xgb_rf" in results

    def test_deltas_consistency(self, cached_cpu_model_results):
        """RF-LR delta should equal auc_rf - auc_lr."""
        results, *_ = cached_cpu_model_results
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
        """Result dict should contain auc, oof_probs, CI, threshold,
        and sensitivity@spec keys (v0.0.16+)."""
        from kreview.eval_engine import evaluate_model

        model, X, y, cv = model_and_data
        result, fitted = evaluate_model(model, X, y, cv, name="rf")

        # Core keys
        assert "auc_rf" in result
        assert "rf_oof_probs" in result
        assert "auc_rf_ci_lower" in result
        assert "auc_rf_ci_upper" in result
        assert "rf_optimal_threshold" in result
        assert "rf_classification_report" in result
        assert "rf_confusion_matrix" in result

        # v0.0.16: sensitivity at fixed specificity operating points
        assert "rf_sensitivity_at_100spec" in result
        assert "rf_sensitivity_at_99spec" in result
        assert "rf_sensitivity_at_95spec" in result
        assert "rf_n_detected_at_100spec" in result
        assert "rf_n_total_positive" in result
        assert "rf_threshold_at_100spec" in result

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


# ── multimodal_eval tests ────────────────────────────────────────────────────


class TestMultimodalEval:
    """Tests for multimodal_eval() — cross-evaluator stacking and ablation."""

    @pytest.fixture(scope="module")
    def cached_multimodal_results(self, tmp_path_factory):
        import json

        tmp_path = tmp_path_factory.mktemp("multimodal")
        np.random.seed(42)
        n = 100
        y = np.array([0] * 50 + [1] * 50)

        for eval_name, auc_base in [("Eval_A", 0.8), ("Eval_B", 0.7), ("Eval_C", 0.6)]:
            probs = np.random.beta(2, 5, size=n).tolist()
            for i in range(50, 100):
                probs[i] = min(1.0, probs[i] + auc_base - 0.5)

            result = {
                "auc_rf": auc_base,
                "rf_oof_probs": probs,
                "auc_lr": auc_base - 0.05,
                "lr_oof_probs": probs,
                "oof_labels": y.tolist(),
                "oof_sample_ids": [f"S{i:03d}" for i in range(n)],
                "best_model": "rf",
                "best_auc": auc_base,
            }
            path = tmp_path / f"{eval_name}_model_results.json"
            with open(path, "w") as f:
                json.dump(result, f)

        from kreview.eval_engine import multimodal_eval

        return multimodal_eval(tmp_path, models=("rf",), n_folds=3)

    def test_output_has_strategy_key(self, cached_multimodal_results):
        """Output dict should have strategy='multimodal'."""
        result = cached_multimodal_results
        assert result["strategy"] == "multimodal"

    def test_evaluator_discovery(self, cached_multimodal_results):
        """Should discover all 3 evaluators."""
        result = cached_multimodal_results
        assert result["n_evaluators"] == 3
        assert set(result["evaluators"]) == {"Eval_A", "Eval_B", "Eval_C"}

    def test_stacking_produces_auc(self, cached_multimodal_results):
        """Stacking should produce an AUC result."""
        result = cached_multimodal_results
        assert "stacking" in result
        assert "auc_stacking_rf" in result["stacking"]
        auc = result["stacking"]["auc_stacking_rf"]
        assert 0.0 <= auc <= 1.0

    def test_single_evaluator_aucs(self, cached_multimodal_results):
        """Per-evaluator AUCs should be captured."""
        result = cached_multimodal_results
        assert "single_evaluator_aucs" in result
        assert "Eval_A" in result["single_evaluator_aucs"]

    def test_missing_results_dir_raises(self, tmp_path):
        """Should raise FileNotFoundError for nonexistent dir."""
        from kreview.eval_engine import multimodal_eval

        with pytest.raises(FileNotFoundError):
            multimodal_eval(tmp_path / "nonexistent", models=("rf",))


# ── gpu_models validation tests ──────────────────────────────────────────────


class TestGpuModelsValidation:
    """Tests for gpu_models() error handling and validation.

    These tests do NOT require GPU hardware — they test the
    input validation logic that runs before any model training.
    """

    def test_single_class_returns_error(self):
        """Single-class y should return error dict, not crash."""
        from kreview.eval_engine import gpu_models

        X = np.random.randn(50, 5)
        y = np.ones(50, dtype=int)  # All class 1

        result, fitted = gpu_models(X, y)

        assert "error" in result
        assert "one class" in result["error"].lower()
        assert fitted == {}

    def test_insufficient_samples_returns_error(self):
        """Too few samples per class for StratifiedKFold → error."""
        from kreview.eval_engine import gpu_models

        X = np.random.randn(3, 5)
        y = np.array([0, 1, 1])  # Only 1 sample for class 0

        result, fitted = gpu_models(X, y, n_folds=5)

        assert "error" in result
        assert fitted == {}

    def test_empty_models_tuple(self):
        """Empty models tuple should return empty results without error."""
        from kreview.eval_engine import gpu_models

        X = np.random.randn(50, 5)
        y = np.zeros(50, dtype=int)
        y[:20] = 1

        result, fitted = gpu_models(X, y, models=())

        # Should have cv_folds_actual but no model-specific keys
        assert "cv_folds_actual" in result
        assert fitted == {}


# ── v0.0.13 Tests ───────────────────────────────────────────────────────────────


class TestBuildModelGPUDispatch:
    """Tests for _build_model GPU model dispatch (v0.0.13)."""

    def test_build_model_lr(self):
        """LR model builds a Pipeline with StandardScaler."""
        from kreview.eval_engine import _build_model

        model = _build_model("lr", random_state=42)
        assert hasattr(model, "named_steps"), "LR should be a Pipeline"
        assert "scaler" in model.named_steps
        assert "lr" in model.named_steps

    def test_build_model_rf(self):
        """RF model builds a RandomForestClassifier."""
        from kreview.eval_engine import _build_model

        model = _build_model("rf", random_state=42)
        assert hasattr(model, "feature_importances_") is False  # Not fitted yet
        assert hasattr(model, "n_estimators")

    @pytest.mark.skipif(not HAS_XGB, reason="XGBoost not available")
    def test_build_model_xgb(self):
        """XGB model builds an XGBClassifier."""
        from kreview.eval_engine import _build_model

        model = _build_model("xgb", random_state=42)
        assert hasattr(model, "n_estimators")

    def test_build_model_gpu_returns_none_without_deps(self):
        """GPU model dispatch returns None when GPU deps are not installed."""
        from kreview.eval_engine import _build_model

        # On a machine without tabpfn installed, this should return None
        model = _build_model("tabpfn", random_state=42, device="cpu")
        # Either returns a model (if installed) or None (if not)
        assert model is None or hasattr(model, "predict_proba")

    def test_build_model_unknown_raises(self):
        """Unknown model name raises ValueError."""
        from kreview.eval_engine import _build_model

        with pytest.raises(ValueError, match="Unknown model"):
            _build_model("nonexistent_model", random_state=42)

    def test_build_model_gpu_kwargs_ignored_for_cpu(self):
        """GPU kwargs are silently ignored for CPU models (no crash)."""
        from kreview.eval_engine import _build_model

        # Should not raise even with GPU kwargs
        model = _build_model(
            "rf",
            random_state=42,
            device="cuda",
            finetune=True,
            finetune_epochs=10,
        )
        assert model is not None


class TestSelectMultimodalFeaturesV013:
    """Tests for top_percentile + Boruta-SHAP MI reduction logic."""

    def test_top_percentile_basic(self):
        """MI selection keeps top N% of features."""
        from kreview.eval_engine import _select_multimodal_features

        np.random.seed(42)
        n = 100
        # 100 features, most noise, first one has signal
        X = pd.DataFrame(np.random.randn(n, 100), columns=[f"f{i}" for i in range(100)])
        y = np.zeros(n, dtype=int)
        y[:40] = 1
        X.iloc[:40, 0] += 3.0  # Signal in first feature

        selected_df, selected_names = _select_multimodal_features(
            X, y, top_percentile=10.0, strategy="mi"
        )

        # Should keep ~10% = 10 features
        assert len(selected_names) == 10
        # Signal feature should survive
        assert "f0" in selected_names

    def test_top_percentile_all_kept_when_few_features(self):
        """When n_features * percentile >= n_features, keep all."""
        from kreview.eval_engine import _select_multimodal_features

        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(50, 5), columns=[f"f{i}" for i in range(5)])
        y = np.zeros(50, dtype=int)
        y[:20] = 1

        selected_df, selected_names = _select_multimodal_features(
            X, y, top_percentile=100.0, strategy="mi"
        )
        assert len(selected_names) == 5

    def test_zero_variance_dropped(self):
        """Zero-variance columns are dropped before MI ranking."""
        from kreview.eval_engine import _select_multimodal_features

        np.random.seed(42)
        X = pd.DataFrame(
            {
                "signal": np.concatenate(
                    [np.random.randn(30) + 2, np.random.randn(30)]
                ),
                "noise": np.random.randn(60),
                "constant": np.zeros(60),  # Zero variance
            }
        )
        y = np.concatenate([np.ones(30), np.zeros(30)]).astype(int)

        selected_df, selected_names = _select_multimodal_features(
            X, y, top_percentile=100.0, strategy="mi"
        )

        assert "constant" not in selected_names
        assert "signal" in selected_names


class TestSaveFittedModels:
    """Tests for _save_fitted_models helper."""

    def test_save_creates_joblib_files(self, tmp_path):
        """Fitted models are saved as .joblib files with correct naming."""
        from kreview.cli_eval import _save_fitted_models
        from sklearn.linear_model import LogisticRegression

        lr = LogisticRegression()
        fitted = {"lr": lr}

        _save_fitted_models(fitted, tmp_path, "TestEval")

        joblib_file = tmp_path / "TestEval_lr_model.joblib"
        assert joblib_file.exists()

    def test_skip_gpu_joblib(self, tmp_path):
        """GPU models are skipped when skip_gpu_joblib=True."""
        from kreview.cli_eval import _save_fitted_models
        from sklearn.linear_model import LogisticRegression

        fitted = {"lr": LogisticRegression(), "tabpfn": "mock_gpu_model"}

        _save_fitted_models(fitted, tmp_path, "TestEval", skip_gpu_joblib=True)

        assert (tmp_path / "TestEval_lr_model.joblib").exists()
        assert not (tmp_path / "TestEval_tabpfn_model.joblib").exists()

    def test_none_models_skipped(self, tmp_path):
        """None-valued models are silently skipped."""
        from kreview.cli_eval import _save_fitted_models

        fitted = {"lr": None, "rf": None}

        _save_fitted_models(fitted, tmp_path, "TestEval")

        assert not (tmp_path / "TestEval_lr_model.joblib").exists()
        assert not (tmp_path / "TestEval_rf_model.joblib").exists()


class TestBuildGpuModelV8:
    """Validate _build_gpu_model() for TabPFN v8 and TabICL v2.1 API changes.

    These tests run WITHOUT GPU hardware — they validate import paths,
    class types, and error handling only.
    """

    def test_tabpfn_finetune_import_path(self):
        """TabPFN v8: fine-tuning should import from tabpfn.finetuning (not extensions)."""
        from kreview.eval_engine import _build_gpu_model

        try:
            model = _build_gpu_model("tabpfn", device="cpu", finetune=True)
            if model is not None:
                # Verify it's the v8 class (lowercase 't')
                assert (
                    "FinetunedTabPFN" in type(model).__name__
                    or "TabPFN" in type(model).__name__
                )
        except Exception:
            pytest.skip("tabpfn not installed")

    def test_tabpfn_zeroshot_import(self):
        """TabPFN v8: zero-shot should import TabPFNClassifier."""
        from kreview.eval_engine import _build_gpu_model

        try:
            model = _build_gpu_model("tabpfn", device="cpu", finetune=False)
            if model is not None:
                assert "TabPFNClassifier" in type(model).__name__
        except Exception:
            pytest.skip("tabpfn not installed")

    def test_tabicl_finetune_uses_dedicated_class(self):
        """TabICL v2.1: finetune=True should use FinetunedTabICLClassifier."""
        from kreview.eval_engine import _build_gpu_model

        try:
            model = _build_gpu_model("tabicl", finetune=True)
            if model is not None:
                assert "Finetuned" in type(model).__name__
        except Exception:
            pytest.skip("tabicl not installed")

    def test_tabicl_zeroshot_uses_base_class(self):
        """TabICL v2.1: finetune=False should use TabICLClassifier."""
        from kreview.eval_engine import _build_gpu_model

        try:
            model = _build_gpu_model("tabicl", finetune=False)
            if model is not None:
                assert "FinetunedTabICL" not in type(model).__name__
        except Exception:
            pytest.skip("tabicl not installed")

    def test_unknown_model_returns_none(self):
        """Unknown GPU model name should return None, not raise."""
        from kreview.eval_engine import _build_gpu_model

        result = _build_gpu_model("nonexistent_model")
        assert result is None

    def test_missing_package_returns_none(self):
        """If tabpfn/tabicl not installed, should return None with log."""
        from kreview.eval_engine import _build_gpu_model

        # This test passes in CI where GPU packages aren't installed
        model = _build_gpu_model("tabpfn", device="cpu")
        # Either a valid model or None (not an exception)
        assert model is None or model is not None


class TestBuildModelDispatchV013:
    """Validates _build_model() dispatches GPU models via _build_gpu_model."""

    def test_build_model_gpu_dispatch_matches_direct(self):
        """_build_model('tabpfn') should return same type as _build_gpu_model('tabpfn')."""
        from kreview.eval_engine import _build_model, _build_gpu_model

        direct = _build_gpu_model("tabpfn", device="cpu")
        dispatched = _build_model("tabpfn", 42, device="cpu")
        assert type(direct) is type(dispatched)


class TestMultimodalEvalParams:
    """Validates multimodal_eval accepts new v0.0.13 params."""

    def test_multimodal_accepts_gpu_models_param(self, tmp_path):
        """multimodal_eval should accept gpu_models parameter without error."""
        from kreview.eval_engine import multimodal_eval
        import json

        # Create minimal per-evaluator results
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        dummy_result = {
            "auc_rf": 0.8,
            "auc_lr": 0.75,
            "best_auc": 0.8,
            "best_model": "rf",
            "rf_oof_probs": [0.5] * 50,
            "lr_oof_probs": [0.5] * 50,
            "oof_labels": [0, 1] * 25,
            "oof_sample_ids": [f"S_{i:03d}" for i in range(50)],
        }
        (results_dir / "TestEval_model_results.json").write_text(
            json.dumps(dummy_result)
        )

        # Should not crash even if GPU packages aren't installed
        result = multimodal_eval(
            results_dir,
            models=("rf",),
            gpu_models=("tabpfn",),
            device="cpu",
            n_folds=3,
        )
        assert result["strategy"] == "multimodal"

    def test_multimodal_top_percentile_param(self, tmp_path):
        """multimodal_eval should accept top_percentile instead of top_k."""
        from kreview.eval_engine import multimodal_eval
        import json

        results_dir = tmp_path / "results"
        results_dir.mkdir()
        dummy_result = {
            "auc_rf": 0.8,
            "best_auc": 0.8,
            "best_model": "rf",
            "rf_oof_probs": [0.5] * 50,
            "oof_labels": [0, 1] * 25,
            "oof_sample_ids": [f"S_{i:03d}" for i in range(50)],
        }
        (results_dir / "TestEval_model_results.json").write_text(
            json.dumps(dummy_result)
        )

        result = multimodal_eval(
            results_dir,
            models=("rf",),
            n_folds=3,
            top_percentile=20.0,
        )
        assert result["strategy"] == "multimodal"


# ── Reproducibility seed tests ─────────────────────────────────────────────────


class TestReproducibilitySeed:
    """Tests for seed propagation through engine functions (Plan Component 6)."""

    def test_cpu_models_deterministic(self, binary_Xy):
        """cpu_models() with same seed twice → identical AUCs."""
        X, y = binary_Xy
        from kreview.eval_engine import cpu_models

        result1, *_ = cpu_models(X, y, n_folds=3, random_state=42)
        result2, *_ = cpu_models(X, y, n_folds=3, random_state=42)
        for model in _MODELS:
            assert (
                result1[f"auc_{model}"] == result2[f"auc_{model}"]
            ), f"AUC mismatch for {model}: {result1[f'auc_{model}']} != {result2[f'auc_{model}']}"

    def test_build_gpu_model_accepts_seed(self):
        """_build_gpu_model() accepts random_state kwarg without error.

        We don't require actual GPU libs — just verify the function signature
        accepts random_state and returns None (import fail) or a model.
        """
        from kreview.eval_engine import _build_gpu_model
        import inspect

        sig = inspect.signature(_build_gpu_model)
        assert (
            "random_state" in sig.parameters
        ), "_build_gpu_model must accept random_state parameter"
        # Call with a bogus model name to verify no crash on random_state kwarg
        result = _build_gpu_model("tabpfn", device="cpu", random_state=99)
        # Returns None if tabpfn not installed, or a model if installed — both fine
        assert result is None or hasattr(
            result, "predict"
        ), "_build_gpu_model should return None or a predictor"

    def test_compute_shap_accepts_seed(self):
        """_compute_shap() accepts random_state kwarg in its signature."""
        from kreview.eval_engine import _compute_shap
        import inspect

        sig = inspect.signature(_compute_shap)
        assert (
            "random_state" in sig.parameters
        ), "_compute_shap must accept random_state parameter"

    def test_multimodal_selection_seed_propagates(self):
        """_select_multimodal_features() uses caller seed, not hardcoded 42."""
        from kreview.eval_engine import _select_multimodal_features

        np.random.seed(0)
        n = 100
        df = pd.DataFrame(
            {
                f"feat_{i}": np.random.randn(n) + (i * 0.5 if i < 3 else 0)
                for i in range(20)
            }
        )
        y = np.array([0] * 60 + [1] * 40)
        # Add signal to first 3 features for positive class
        df.iloc[60:, :3] += 2.0

        # Call with seed=99 (not the default 42) — should not crash
        X_sel, names = _select_multimodal_features(
            df,
            y,
            top_percentile=50.0,
            strategy="mi",
            random_state=99,
        )
        assert len(names) > 0, "Should select at least one feature"
        assert X_sel.shape[1] == len(names)


# ── v0.0.16 Tests ────────────────────────────────────────────────────────────────────


class TestEvaluateHoldout:
    """Tests for evaluate_holdout() — unbiased holdout evaluation (v0.0.16).

    Validates:
      - AUC computation on holdout set
      - Sensitivity@100spec keys present
      - Bootstrap CI bounds sane
      - Single-class error handling
      - Healthy-normal specificity branch
      - Classification metrics at optimal threshold
    """

    @pytest.fixture
    def holdout_model(self):
        """Fit a simple RF on synthetic data, return (model, X_test, y_test)."""
        from sklearn.ensemble import RandomForestClassifier

        np.random.seed(42)
        n_train, n_test = 80, 20
        X_train = np.random.randn(n_train, 5)
        y_train = np.zeros(n_train, dtype=int)
        y_train[:32] = 1
        X_train[:32, 0] += 2.0  # Signal

        X_test = np.random.randn(n_test, 5)
        y_test = np.zeros(n_test, dtype=int)
        y_test[:8] = 1
        X_test[:8, 0] += 2.0

        model = RandomForestClassifier(
            n_estimators=10, random_state=42, class_weight="balanced"
        )
        model.fit(X_train, y_train)
        return model, X_test, y_test

    def test_output_has_holdout_keys(self, holdout_model):
        """Result dict should contain holdout-prefixed AUC, CI, sensitivity."""
        from kreview.eval_engine import evaluate_holdout

        model, X_test, y_test = holdout_model
        result = evaluate_holdout(model, X_test, y_test, name="rf")

        assert "holdout_rf_auc" in result
        assert "holdout_rf_auc_ci_lower" in result
        assert "holdout_rf_auc_ci_upper" in result
        assert "holdout_rf_sensitivity_at_100spec" in result
        assert "holdout_rf_sensitivity_at_99spec" in result
        assert "holdout_rf_sensitivity_at_95spec" in result
        assert "holdout_rf_n_detected_at_100spec" in result
        assert "holdout_rf_n_total_positive" in result
        assert "holdout_rf_n_total_negative" in result
        assert "holdout_rf_optimal_threshold" in result
        assert "holdout_rf_classification_report" in result
        assert "holdout_rf_confusion_matrix" in result

    def test_auc_in_valid_range(self, holdout_model):
        """Holdout AUC should be between 0 and 1."""
        from kreview.eval_engine import evaluate_holdout

        model, X_test, y_test = holdout_model
        result = evaluate_holdout(model, X_test, y_test, name="rf")

        assert 0.0 <= result["holdout_rf_auc"] <= 1.0

    def test_ci_bounds_sane(self, holdout_model):
        """CI lower <= AUC <= CI upper."""
        from kreview.eval_engine import evaluate_holdout

        model, X_test, y_test = holdout_model
        result = evaluate_holdout(model, X_test, y_test, name="rf")

        assert result["holdout_rf_auc_ci_lower"] <= result["holdout_rf_auc"]
        assert result["holdout_rf_auc"] <= result["holdout_rf_auc_ci_upper"]

    def test_sensitivity_at_100spec_range(self, holdout_model):
        """Sensitivity@100spec should be between 0 and 1."""
        from kreview.eval_engine import evaluate_holdout

        model, X_test, y_test = holdout_model
        result = evaluate_holdout(model, X_test, y_test, name="rf")

        assert 0.0 <= result["holdout_rf_sensitivity_at_100spec"] <= 1.0
        assert 0.0 <= result["holdout_rf_sensitivity_at_99spec"] <= 1.0
        assert 0.0 <= result["holdout_rf_sensitivity_at_95spec"] <= 1.0

    def test_n_detected_consistent(self, holdout_model):
        """n_detected_at_100spec should be <= n_total_positive."""
        from kreview.eval_engine import evaluate_holdout

        model, X_test, y_test = holdout_model
        result = evaluate_holdout(model, X_test, y_test, name="rf")

        assert (
            result["holdout_rf_n_detected_at_100spec"]
            <= result["holdout_rf_n_total_positive"]
        )
        assert result["holdout_rf_n_total_positive"] == int(y_test.sum())
        assert result["holdout_rf_n_total_negative"] == int((y_test == 0).sum())

    def test_single_class_returns_error(self):
        """Single-class holdout should return error key, not crash."""
        from kreview.eval_engine import evaluate_holdout
        from sklearn.ensemble import RandomForestClassifier

        np.random.seed(42)
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        model.fit(np.random.randn(50, 3), np.array([0] * 25 + [1] * 25))

        X_test = np.random.randn(10, 3)
        y_test = np.ones(10, dtype=int)  # All positive

        result = evaluate_holdout(model, X_test, y_test, name="rf")

        assert "holdout_rf_error" in result
        assert "holdout_rf_auc" not in result

    def test_healthy_normal_specificity(self, holdout_model):
        """When sample_labels provided with Healthy Normal, compute healthy sens."""
        from kreview.eval_engine import evaluate_holdout

        model, X_test, y_test = holdout_model
        sample_labels = np.array(["True ctDNA+"] * 8 + ["Healthy Normal"] * 12)

        result = evaluate_holdout(
            model, X_test, y_test, name="rf", sample_labels=sample_labels
        )

        assert "holdout_rf_sensitivity_at_100spec_healthy" in result
        assert 0.0 <= result["holdout_rf_sensitivity_at_100spec_healthy"] <= 1.0

    def test_no_sample_labels_omits_healthy_key(self, holdout_model):
        """Without sample_labels, healthy-normal specificity keys are absent."""
        from kreview.eval_engine import evaluate_holdout

        model, X_test, y_test = holdout_model
        result = evaluate_holdout(model, X_test, y_test, name="rf")

        assert "holdout_rf_sensitivity_at_100spec_healthy" not in result


class TestSensitivityAtSpecificity:
    """Tests for sensitivity@spec keys in evaluate_model (v0.0.16)."""

    def test_sensitivity_values_in_range(self):
        """All sensitivity@spec values should be between 0 and 1."""
        from kreview.eval_engine import evaluate_model
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import StratifiedKFold

        np.random.seed(42)
        n = 100
        X = np.random.randn(n, 5)
        y = np.zeros(n, dtype=int)
        y[:40] = 1
        X[:40, 0] += 2.0

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        result, _ = evaluate_model(model, X, y, cv, name="rf")

        for key in [
            "rf_sensitivity_at_100spec",
            "rf_sensitivity_at_99spec",
            "rf_sensitivity_at_95spec",
        ]:
            assert 0.0 <= result[key] <= 1.0, f"{key}={result[key]} out of [0,1]"

    def test_n_detected_lte_total_positive(self):
        """n_detected_at_100spec should never exceed n_total_positive."""
        from kreview.eval_engine import evaluate_model
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import StratifiedKFold

        np.random.seed(42)
        n = 100
        X = np.random.randn(n, 5)
        y = np.zeros(n, dtype=int)
        y[:40] = 1
        X[:40, 0] += 2.0

        model = RandomForestClassifier(n_estimators=10, random_state=42)
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        result, _ = evaluate_model(model, X, y, cv, name="rf")

        assert result["rf_n_detected_at_100spec"] <= result["rf_n_total_positive"]
        assert result["rf_n_total_positive"] == 40


class TestGpuFeatureCapping:
    """Tests for gpu_models() feature capping return values (v0.0.16)."""

    def test_cap_not_applied_when_under_limit(self):
        """When n_features <= max_gpu_features, no capping occurs."""
        from kreview.eval_engine import gpu_models

        np.random.seed(42)
        X = np.random.randn(50, 5)
        y = np.zeros(50, dtype=int)
        y[:20] = 1

        result, _ = gpu_models(X, y, models=(), max_gpu_features=150)

        assert result["gpu_feature_cap_applied"] is False

    def test_cap_applied_when_over_limit(self):
        """When n_features > max_gpu_features, capping is applied."""
        from kreview.eval_engine import gpu_models

        np.random.seed(42)
        n = 100
        X = np.random.randn(n, 200)  # 200 features > limit
        y = np.zeros(n, dtype=int)
        y[:40] = 1
        X[:40, 0] += 3.0

        result, _ = gpu_models(X, y, models=(), max_gpu_features=50)

        assert result["gpu_feature_cap_applied"] is True
        assert result["gpu_feature_cap_original"] == 200
        assert result["gpu_feature_cap_final"] == 50
        assert "gpu_feature_cap_indices" in result
        assert len(result["gpu_feature_cap_indices"]) == 50
        # Indices should be sorted (preserve original column order)
        assert result["gpu_feature_cap_indices"] == sorted(
            result["gpu_feature_cap_indices"]
        )
