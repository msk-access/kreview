"""Tests for kreview.selection — shared feature scoring and selection logic."""

import numpy as np
import pandas as pd
import pytest

from kreview.selection import (
    build_binary_target,
    _impute,
    score_features,
    select_features,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_matrix():
    """Synthetic matrix with 50 samples and 20 features + label/metadata columns.

    - 25 positives ("True ctDNA+") and 25 negatives ("Healthy Normal")
    - Features 0-4 are strongly discriminative (shifted means)
    - Features 5-19 are pure noise
    - One feature has NaN values to test imputation
    """
    rng = np.random.RandomState(42)
    n = 50
    n_pos = 25
    n_features = 20

    # Labels
    labels = ["True ctDNA+"] * n_pos + ["Healthy Normal"] * (n - n_pos)

    # Build features: 5 signal + 15 noise
    data = {"SAMPLE_ID": [f"S_{i:03d}" for i in range(n)], "label": labels}

    for i in range(n_features):
        if i < 5:
            # Signal features — positives have higher mean
            vals = np.concatenate(
                [rng.normal(2.0, 0.5, n_pos), rng.normal(0.0, 0.5, n - n_pos)]
            )
        else:
            # Noise features — identical distribution
            vals = rng.normal(0.0, 1.0, n)
        data[f"feat_{i:02d}"] = vals

    # Add a constant feature (should be dropped by variance guard)
    data["feat_constant"] = np.ones(n) * 42.0

    # Add NaN values in one feature
    data["feat_00"][0] = np.nan
    data["feat_00"][1] = np.nan

    # Add metadata columns (should be ignored by scoring)
    data["CANCER_TYPE"] = ["NSCLC"] * n
    data["max_vaf"] = rng.uniform(0.01, 0.2, n)
    data["n_total_somatic_snvs"] = rng.randint(1, 10, n)

    return pd.DataFrame(data)


@pytest.fixture
def small_matrix():
    """Minimal matrix for edge-case testing (10 samples)."""
    rng = np.random.RandomState(99)
    n = 30  # Minimum viable: 20+ samples needed
    data = {
        "SAMPLE_ID": [f"S_{i}" for i in range(n)],
        "label": ["True ctDNA+"] * 15 + ["Healthy Normal"] * 15,
        "feat_a": np.concatenate([rng.normal(1, 0.3, 15), rng.normal(0, 0.3, 15)]),
        "feat_b": rng.normal(0, 1, n),
    }
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# build_binary_target
# ---------------------------------------------------------------------------


class TestBuildBinaryTarget:
    def test_basic(self, synthetic_matrix):
        model_df, y = build_binary_target(synthetic_matrix)
        assert len(model_df) == 50
        assert y.sum() == 25  # 25 positives
        assert (y == 0).sum() == 25  # 25 negatives

    def test_filters_unknown_labels(self):
        df = pd.DataFrame(
            {
                "label": ["True ctDNA+"] * 15
                + ["Healthy Normal"] * 15
                + ["Unknown"] * 5,
                "feat": np.ones(35),
            }
        )
        model_df, y = build_binary_target(df)
        assert len(model_df) == 30  # "Unknown" filtered out

    def test_insufficient_samples(self):
        df = pd.DataFrame({"label": ["True ctDNA+"] * 5, "feat": np.ones(5)})
        with pytest.raises(ValueError, match="Insufficient samples"):
            build_binary_target(df)

    def test_single_class(self):
        df = pd.DataFrame({"label": ["True ctDNA+"] * 25, "feat": np.ones(25)})
        with pytest.raises(ValueError, match="Only one class"):
            build_binary_target(df)


# ---------------------------------------------------------------------------
# _impute
# ---------------------------------------------------------------------------


class TestImpute:
    def test_median(self):
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": [4.0, 5.0, np.nan]})
        result = _impute(df, "median")
        assert result["a"].isna().sum() == 0
        assert result["a"].iloc[1] == 2.0  # median of [1, 3]

    def test_mean(self):
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        result = _impute(df, "mean")
        assert result["a"].iloc[1] == 2.0

    def test_zero(self):
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        result = _impute(df, "zero")
        assert result["a"].iloc[1] == 0.0

    def test_unknown_falls_back_to_zero(self):
        df = pd.DataFrame({"a": [1.0, np.nan, 3.0]})
        result = _impute(df, "nonexistent_strategy")
        assert result["a"].iloc[1] == 0.0


# ---------------------------------------------------------------------------
# score_features
# ---------------------------------------------------------------------------


class TestScoreFeatures:
    def test_returns_expected_columns(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        assert "feature_column" in eval_df.columns
        assert "univariate_auc" in eval_df.columns
        assert "mutual_info" in eval_df.columns

    def test_signal_features_rank_higher(self, synthetic_matrix):
        """Signal features (feat_00 through feat_04) should have higher AUC
        than noise features on average."""
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        signal = eval_df[eval_df["feature_column"].str.startswith("feat_0")]
        noise = eval_df[eval_df["feature_column"].str.match(r"feat_(?:0[5-9]|1\d)")]

        assert signal["univariate_auc"].mean() > noise["univariate_auc"].mean()

    def test_no_auc_when_disabled(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=False)
        assert "univariate_auc" not in eval_df.columns
        assert "mutual_info" in eval_df.columns

    def test_includes_constant_feature(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        assert "feat_constant" in eval_df["feature_column"].values

    def test_excludes_metadata_columns(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        scored_cols = set(eval_df["feature_column"])
        # Metadata columns should NOT be scored
        assert "SAMPLE_ID" not in scored_cols
        assert "label" not in scored_cols
        assert "CANCER_TYPE" not in scored_cols
        assert "max_vaf" not in scored_cols

    def test_empty_features_raises(self):
        df = pd.DataFrame(
            {
                "SAMPLE_ID": [f"S{i}" for i in range(30)],
                "label": ["True ctDNA+"] * 15 + ["Healthy Normal"] * 15,
            }
        )
        with pytest.raises(ValueError, match="No numeric feature columns"):
            score_features(df, cv_folds=3)


# ---------------------------------------------------------------------------
# select_features
# ---------------------------------------------------------------------------


class TestSelectFeatures:
    def test_reduces_feature_count(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        selected, qc = select_features(synthetic_matrix, eval_df, top_percentile=30)

        # Selected matrix should have fewer feature columns
        from kreview.core import LABEL_META_COLS

        orig_feats = [
            c
            for c in synthetic_matrix.select_dtypes(include=np.number).columns
            if c not in LABEL_META_COLS
        ]
        sel_feats = [
            c
            for c in selected.select_dtypes(include=np.number).columns
            if c not in LABEL_META_COLS
        ]
        assert len(sel_feats) < len(orig_feats)

    def test_preserves_metadata_columns(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        selected, _ = select_features(synthetic_matrix, eval_df)
        assert "SAMPLE_ID" in selected.columns
        assert "label" in selected.columns

    def test_drops_constant_feature(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        selected, qc = select_features(
            synthetic_matrix,
            eval_df,
            top_percentile=100,  # keep all — variance guard still applies
        )
        # feat_constant should be dropped by variance guard
        from kreview.core import LABEL_META_COLS

        sel_feats = [
            c
            for c in selected.select_dtypes(include=np.number).columns
            if c not in LABEL_META_COLS
        ]
        assert "feat_constant" not in sel_feats
        assert qc["n_variance_dropped"] >= 1

    def test_qc_dict_structure(self, synthetic_matrix):
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        _, qc = select_features(synthetic_matrix, eval_df)

        required_keys = {
            "method",
            "total_input_features",
            "target_percentile",
            "n_keep_per_metric",
            "n_selected_union",
            "n_after_variance_guard",
            "n_variance_dropped",
            "n_overlap_both",
            "n_auc_only",
            "n_mi_only",
            "impute_strategy",
        }
        assert required_keys.issubset(set(qc.keys()))
        assert qc["method"] == "hybrid_union"

    def test_mi_only_selection(self, synthetic_matrix):
        """When AUC is not computed, selection falls back to MI-only."""
        eval_df = score_features(synthetic_matrix, cv_folds=3, compute_auc=False)
        selected, qc = select_features(synthetic_matrix, eval_df)
        # Should still produce a valid result
        assert qc["n_auc_only"] == 0  # no AUC-based selection

    def test_small_matrix(self, small_matrix):
        eval_df = score_features(small_matrix, cv_folds=3, compute_auc=True)
        selected, qc = select_features(small_matrix, eval_df)
        assert len(selected) > 0
        assert qc["total_input_features"] == 2  # feat_a, feat_b
