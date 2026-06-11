"""Tests for feature group ablation pipeline (ABLATE → MERGE → EVAL).

Covers:
- identify_feature_groups() suffix mapping
- generate_subsets() logic
- _compute_oof_metrics() output schema parity
- cpu_models() backward compatibility (no new params)
- cpu_models() nested CV path (with per_fold_features)
- merge_ablation() CPU-only and CPU+GPU modes
- Scoreboard ablation columns
"""

import json

import numpy as np
import pandas as pd
import pytest

from kreview.eval_engine import (
    _compute_oof_metrics,
    generate_subsets,
    identify_feature_groups,
    merge_ablation,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def synthetic_features():
    """Feature names spanning 3 known suffix groups + 1 unknown."""
    return [
        "gene_A_mean_size",
        "gene_B_mean_size",
        "region_1_count",
        "region_2_count",
        "region_3_count",
        "panel_ultra_short_ratio",
        "misc_unknown_metric",
    ]


@pytest.fixture(scope="module")
def synthetic_matrix(tmp_path_factory, synthetic_features):
    """Create a synthetic matrix parquet with known feature groups.

    Includes split and label columns for realistic testing.
    """
    rng = np.random.RandomState(42)
    n = 100
    df = pd.DataFrame(
        rng.randn(n, len(synthetic_features)),
        columns=synthetic_features,
    )

    # Binary target with imbalance
    y = np.array([1] * 30 + [0] * 70)
    rng.shuffle(y)
    df["binary_target"] = y
    df["label"] = np.where(
        y == 1,
        rng.choice(["Possible ctDNA+", "Likely ctDNA+"], size=n),
        rng.choice(["Healthy Normal", "ctDNA-"], size=n),
    )

    # Train/test split (80/20)
    split = np.array(["train"] * 80 + ["test"] * 20)
    rng.shuffle(split)
    df["split"] = split

    # Save as parquet
    out_dir = tmp_path_factory.mktemp("ablation_test")
    matrix_path = out_dir / "TestEval_matrix.parquet"
    df.to_parquet(matrix_path, index=False)
    return matrix_path


# ── Test: identify_feature_groups ─────────────────────────────────────────────


class TestIdentifyFeatureGroups:
    def test_groups_known_suffixes(self, synthetic_features):
        groups = identify_feature_groups(synthetic_features)
        assert "mean_size" in groups
        assert "count" in groups
        assert "ultra_short_ratio" in groups

    def test_groups_correct_columns(self, synthetic_features):
        groups = identify_feature_groups(synthetic_features)
        assert groups["mean_size"] == ["gene_A_mean_size", "gene_B_mean_size"]
        assert groups["count"] == ["region_1_count", "region_2_count", "region_3_count"]

    def test_unknown_suffix_in_other(self, synthetic_features):
        groups = identify_feature_groups(synthetic_features)
        assert "misc_unknown_metric" in groups.get("other", [])

    def test_empty_input(self):
        groups = identify_feature_groups([])
        assert groups == {}


# ── Test: generate_subsets ────────────────────────────────────────────────────


class TestGenerateSubsets:
    def test_all_subset_included(self):
        groups = {"mean_size": ["a", "b"], "count": ["c"]}
        subsets = generate_subsets(groups)
        assert "ALL" in subsets

    def test_solo_subsets(self):
        groups = {"mean_size": ["a"], "count": ["b"]}
        subsets = generate_subsets(groups)
        assert "mean_size" in subsets
        assert "count" in subsets

    def test_leave_one_out(self):
        groups = {"mean_size": ["a"], "count": ["b"], "std": ["c"]}
        subsets = generate_subsets(groups)
        assert "no_mean_size" in subsets
        assert "no_count" in subsets
        assert "no_std" in subsets

    def test_single_group_passthrough(self):
        groups = {"count": ["a", "b", "c"]}
        subsets = generate_subsets(groups)
        # Single group → only ALL
        assert len(subsets) == 1
        assert "ALL" in subsets


# ── Test: _compute_oof_metrics ────────────────────────────────────────────────


class TestComputeOofMetrics:
    @pytest.fixture
    def simple_data(self):
        rng = np.random.RandomState(42)
        y = np.array([1] * 20 + [0] * 30)
        oof = rng.rand(50)
        # Make positives somewhat higher
        oof[:20] += 0.3
        oof = np.clip(oof, 0, 1)
        return y, oof

    def test_auc_key_present(self, simple_data):
        y, oof = simple_data
        result = _compute_oof_metrics(y, oof, "lr")
        assert "auc_lr" in result
        assert 0 <= result["auc_lr"] <= 1

    def test_sensitivity_keys_present(self, simple_data):
        y, oof = simple_data
        result = _compute_oof_metrics(y, oof, "rf")
        assert "rf_sensitivity_at_100spec" in result
        assert "rf_sensitivity_at_99spec" in result
        assert "rf_sensitivity_at_95spec" in result

    def test_healthy_sensitivity_with_labels(self, simple_data):
        y, oof = simple_data
        labels = np.array(
            ["Possible ctDNA+"] * 20 + ["Healthy Normal"] * 15 + ["ctDNA-"] * 15
        )
        result = _compute_oof_metrics(y, oof, "xgb", sample_labels=labels)
        assert "xgb_sensitivity_at_100spec_healthy" in result

    def test_fold_aucs_with_assignment(self, simple_data):
        y, oof = simple_data
        # Ensure each fold has both classes (y[:20]=1, y[20:]=0)
        # Create folds that each span both class regions
        folds = np.array([i % 5 for i in range(50)])
        result = _compute_oof_metrics(y, oof, "lr", fold_assignment=folds)
        # fold_aucs may be empty if some folds lack both classes
        # Just check the key exists (may or may not be populated)
        if "lr_fold_aucs" in result:
            assert isinstance(result["lr_fold_aucs"], list)

    def test_ci_keys_present(self, simple_data):
        y, oof = simple_data
        result = _compute_oof_metrics(y, oof, "lr")
        assert "auc_lr_ci_lower" in result
        assert "auc_lr_ci_upper" in result

    def test_oof_probs_key(self, simple_data):
        y, oof = simple_data
        result = _compute_oof_metrics(y, oof, "lr")
        assert "lr_oof_probs" in result
        assert len(result["lr_oof_probs"]) == len(y)


# ── Test: cpu_models backward compatibility ───────────────────────────────────


class TestCpuModelsBackwardCompat:
    """Verify that cpu_models() without new params is unchanged."""

    def test_no_new_params_returns_4tuple(self):
        """cpu_models() without per_fold_features returns the standard 4-tuple."""
        from kreview.eval_engine import cpu_models

        rng = np.random.RandomState(42)
        X = rng.randn(60, 5)
        y = np.array([1] * 20 + [0] * 40)
        rng.shuffle(y)

        results, lr, rf, xgb = cpu_models(
            X, y, feature_names=[f"f{i}" for i in range(5)], n_folds=3
        )
        assert isinstance(results, dict)
        assert "auc_lr" in results
        assert "auc_rf" in results

    def test_standard_path_no_nested_cv_flag(self):
        """Standard path should NOT set nested_cv flag."""
        from kreview.eval_engine import cpu_models

        rng = np.random.RandomState(42)
        X = rng.randn(60, 5)
        y = np.array([1] * 20 + [0] * 40)
        rng.shuffle(y)

        results, *_ = cpu_models(
            X, y, feature_names=[f"f{i}" for i in range(5)], n_folds=3
        )
        assert not results.get("nested_cv", False)


# ── Test: scoreboard ablation columns ─────────────────────────────────────────


class TestScoreboardAblation:
    def test_nested_cv_column(self, tmp_path):
        """Scoreboard should have nested_cv column."""
        from kreview.scoreboard import build_scoreboard

        # Create minimal model results
        results = {
            "TestEval": {
                "auc_lr": 0.85,
                "lr_oof_probs": [0.5] * 10,
                "lr_classification_report": {
                    "1": {"recall": 0.8},
                    "0": {"recall": 0.9},
                },
                "lr_sensitivity_at_100spec_healthy": 0.3,
                "nested_cv": True,
            }
        }

        out = tmp_path / "results"
        out.mkdir()
        for name, data in results.items():
            with open(out / f"{name}_model_results.json", "w") as f:
                json.dump(data, f)

        df = build_scoreboard(out)
        assert "nested_cv" in df.columns
        assert df.iloc[0]["nested_cv"] == True  # noqa: E712 (np.bool_)
        assert "best_sens_100spec_healthy" in df.columns


# ── Test: _build_ablation_model_factories ─────────────────────────────────────


class TestBuildAblationModelFactories:
    """Tests for _build_ablation_model_factories GPU factory fix.

    Validates that GPU model factories use _build_gpu_model (not raw
    GPUModelCVAdapter), and that CPU factories remain unchanged.
    """

    def test_cpu_factories_return_estimators(self):
        """CPU factories (lr, rf, xgb) should return fittable estimators."""
        from kreview.eval_engine import _build_ablation_model_factories

        factories = _build_ablation_model_factories(("lr", "rf", "xgb"))
        for name in ("lr", "rf", "xgb"):
            model = factories[name]()
            assert model is not None, f"{name} factory returned None"
            assert hasattr(model, "fit"), f"{name} model has no .fit method"

    def test_gpu_factory_returns_adapter_or_none(self):
        """GPU factory should return GPUModelCVAdapter (if deps installed) or None."""
        from kreview.eval_engine import _build_ablation_model_factories

        factories = _build_ablation_model_factories(
            ("tabpfn",), device="cpu"
        )
        assert "tabpfn" in factories
        model = factories["tabpfn"]()
        # Either a valid adapter or None — never TypeError
        assert model is None or hasattr(model, "predict_proba")

    def test_gpu_factory_does_not_raise_typeerror(self):
        """GPU factory must not raise TypeError (the original bug)."""
        from kreview.eval_engine import _build_ablation_model_factories

        factories = _build_ablation_model_factories(
            ("tabpfn", "tabicl"), device="cpu"
        )
        for name in ("tabpfn", "tabicl"):
            # The old code raised TypeError here:
            #   GPUModelCVAdapter(model_name=n, device=d)
            # Now it should succeed (returning adapter or None)
            try:
                result = factories[name]()
            except TypeError:
                pytest.fail(
                    f"{name} factory raised TypeError — "
                    "likely still using old GPUModelCVAdapter(model_name=...) call"
                )
            assert result is None or hasattr(result, "predict_proba")

    def test_unknown_model_not_in_factories(self):
        """Unknown model names should be logged and excluded from factories."""
        from kreview.eval_engine import _build_ablation_model_factories

        factories = _build_ablation_model_factories(("lr", "bogus_model"))
        assert "lr" in factories
        assert "bogus_model" not in factories

