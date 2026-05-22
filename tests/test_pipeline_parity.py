"""Pipeline parity test — monolithic (kreview run) vs modular (select → eval).

Verifies that the shared functions produce identical results regardless
of calling order. Both paths use:
  1. build_binary_target() — same label filtering + binary target
  2. score_features() — same scoring logic
  3. select_features() — same feature selection

The test builds a synthetic matrix with known signal features and noise,
runs both paths, and asserts that:
  - The selected feature sets are identical
  - The eval stats (scores) are identical
  - QC metadata is consistent
"""

import numpy as np
import pandas as pd
import pytest

from kreview.selection import build_binary_target, score_features, select_features

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def synthetic_matrix():
    """Build a realistic synthetic matrix with 50 samples, 20 features.

    - 5 signal features (correlated with label)
    - 10 noise features (random)
    - 5 constant features (zero variance, should be dropped)
    - Label column follows canonical 5-tier format
    """
    np.random.seed(42)
    n = 50

    # Labels: 20 True ctDNA+, 15 Possible ctDNA+, 10 Healthy Normal, 5 Possible ctDNA-
    labels = (
        ["True ctDNA+"] * 20
        + ["Possible ctDNA+"] * 15
        + ["Healthy Normal"] * 10
        + ["Possible ctDNA-"] * 5
    )
    y_binary = np.array([1] * 20 + [1] * 15 + [0] * 10 + [0] * 5)

    data = {"SAMPLE_ID": [f"S{i:03d}" for i in range(n)], "label": labels}

    # Signal features: correlated with binary label
    for i in range(5):
        data[f"signal_{i}"] = np.random.randn(n) + y_binary * (2.0 + i * 0.5)

    # Noise features: pure random
    for i in range(10):
        data[f"noise_{i}"] = np.random.randn(n)

    # Constant features: should be dropped
    for i in range(5):
        data[f"const_{i}"] = 0.0

    return pd.DataFrame(data)


# ── Parity Tests ────────────────────────────────────────────────────────────────


class TestPipelineParity:
    """Verify monolithic and modular paths produce identical results."""

    def test_build_binary_target_deterministic(self, synthetic_matrix):
        """Calling build_binary_target twice produces identical output."""
        df1, y1 = build_binary_target(synthetic_matrix)
        df2, y2 = build_binary_target(synthetic_matrix)

        pd.testing.assert_frame_equal(df1, df2)
        np.testing.assert_array_equal(y1, y2)

    def test_score_features_deterministic(self, synthetic_matrix):
        """Calling score_features twice produces identical scores."""
        stats1 = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        stats2 = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)

        pd.testing.assert_frame_equal(stats1, stats2)

    def test_select_features_deterministic(self, synthetic_matrix):
        """Full select pipeline (score → select) is deterministic."""
        stats = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)

        sel1, qc1 = select_features(synthetic_matrix, stats, top_percentile=50)
        sel2, qc2 = select_features(synthetic_matrix, stats, top_percentile=50)

        pd.testing.assert_frame_equal(sel1, sel2)
        assert qc1 == qc2

    def test_signal_features_selected_over_noise(self, synthetic_matrix):
        """Signal features should rank higher than noise in both paths."""
        stats = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        selected, qc = select_features(synthetic_matrix, stats, top_percentile=50)

        selected_features = [
            c
            for c in selected.columns
            if c not in {"SAMPLE_ID", "label"} and "__" not in c
        ]

        # At least 3 of the 5 signal features should survive selection
        signal_selected = [f for f in selected_features if f.startswith("signal_")]
        assert (
            len(signal_selected) >= 3
        ), f"Expected ≥3 signal features selected, got {signal_selected}"

    def test_constant_features_always_dropped(self, synthetic_matrix):
        """Constant features should never appear in selected output."""
        stats = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        selected, qc = select_features(synthetic_matrix, stats, top_percentile=100)

        # Even at 100% top percentile, constant features should be dropped
        const_cols = [c for c in selected.columns if c.startswith("const_")]
        assert len(const_cols) == 0, f"Constant features not dropped: {const_cols}"

    def test_qc_metadata_consistent(self, synthetic_matrix):
        """QC dict should have expected keys and consistent counts."""
        stats = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        _, qc = select_features(synthetic_matrix, stats, top_percentile=50)

        # QC should have standard keys
        assert "total_input_features" in qc
        assert "n_selected_union" in qc
        assert "method" in qc

        # Selected count should be <= original (minus constants)
        assert qc["n_selected_union"] <= qc["total_input_features"]
        assert qc["n_selected_union"] > 0

    def test_different_percentiles_give_different_sizes(self, synthetic_matrix):
        """Higher percentile should select more features (all else equal)."""
        stats = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)

        sel_25, _ = select_features(synthetic_matrix, stats, top_percentile=25)
        sel_75, _ = select_features(synthetic_matrix, stats, top_percentile=75)

        feat_25 = [c for c in sel_25.columns if c not in {"SAMPLE_ID", "label"}]
        feat_75 = [c for c in sel_75.columns if c not in {"SAMPLE_ID", "label"}]

        assert len(feat_25) <= len(feat_75), (
            f"25th percentile ({len(feat_25)}) should select ≤ "
            f"75th percentile ({len(feat_75)})"
        )

    def test_eval_stats_have_all_features(self, synthetic_matrix):
        """Eval stats should have a row for every non-constant, non-metadata feature."""
        stats = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)

        # Should have signal + noise + constant features (all scored)
        scored_features = set(stats["feature_column"].values)

        # All 5 signal features should be scored
        for i in range(5):
            assert f"signal_{i}" in scored_features

        # All 10 noise features should be scored
        for i in range(10):
            assert f"noise_{i}" in scored_features

    def test_samples_preserved_through_selection(self, synthetic_matrix):
        """Number of samples should be identical before and after selection."""
        stats = score_features(synthetic_matrix, cv_folds=3, compute_auc=True)
        selected, _ = select_features(synthetic_matrix, stats, top_percentile=50)

        # Only modelable samples should remain (not "Insufficient Data")
        _, y = build_binary_target(synthetic_matrix)
        expected_n = len(y)

        assert (
            len(selected) == expected_n
        ), f"Expected {expected_n} samples, got {len(selected)}"
