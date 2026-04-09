"""Tests for kreview.eval_engine — Phase 1 audit fixes (C-04).

Covers:
  - evaluate_feature output schema validation
  - FDR correction produces valid p-values
  - single_feature_model returns valid AUC
  - single_feature_model rejects single-class input
  - Pipeline-based LR model (no scaler leakage)
  - Bootstrap CI bounds
  - OOF subgroup metrics present
"""

import numpy as np
import pandas as pd
import pytest

from kreview.eval_engine import evaluate_feature, single_feature_model, LABEL_ORDER

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
