"""Tests for kreview.scoreboard — build_scoreboard aggregation.

Covers:
  - Empty directory returns empty DataFrame
  - Malformed JSON files are skipped with warning (no crash)
  - Two mock result files produce correct ranking
  - Column names match expectations
  - Sorting is by best_auc descending
"""

import json
import numpy as np
import pytest

from kreview.scoreboard import build_scoreboard


@pytest.fixture
def mock_results(tmp_path):
    """Create two mock *_model_results.json files with known AUCs.

    EvalA: best=RF (0.85), includes v0.0.16 sensitivity + holdout keys.
    EvalB: best=XGB (0.91), includes v0.0.16 sensitivity but no holdout.
    """
    # Evaluator A: best AUC = 0.85 (RF), with holdout metrics
    eval_a = {
        "auc_rf": 0.85,
        "auc_lr": 0.78,
        "auc_xgb": 0.82,
        "cv_folds_actual": 5,
        "top_features": ["feat1", "feat2", "feat3"],
        "rf_optimal_threshold": 0.42,
        "rf_classification_report": {
            "1": {"recall": 0.80, "support": 50},
            "0": {"recall": 0.90, "support": 100},
            "weighted avg": {"support": 150},
        },
        "selection_qc": {
            "method": "hybrid_union",
            "n_selected_union": 3,
            "n_overlap_both": 2,
        },
        # v0.0.16: clinical sensitivity metrics
        "rf_sensitivity_at_100spec": 0.62,
        "rf_sensitivity_at_100spec_healthy": 0.58,
        "rf_n_detected_at_100spec": 31,
        "rf_sensitivity_at_95spec": 0.74,
        # v0.0.16: holdout metrics
        "holdout_rf_auc": 0.82,
        "holdout_rf_sensitivity_at_100spec": 0.55,
        "holdout_n_train": 120,
        "holdout_n_test": 30,
    }
    # Evaluator B: best AUC = 0.91 (XGB), no holdout metrics
    eval_b = {
        "auc_rf": 0.88,
        "auc_lr": 0.75,
        "auc_xgb": 0.91,
        "cv_folds_actual": 5,
        "top_features": ["feat4", "feat5"],
        "rf_optimal_threshold": 0.50,
        "rf_classification_report": {
            "1": {"recall": 0.85, "support": 50},
            "0": {"recall": 0.95, "support": 100},
            "weighted avg": {"support": 150},
        },
        # v0.0.16: best model is XGB, so these use xgb prefix
        "xgb_sensitivity_at_100spec": 0.70,
        "xgb_n_detected_at_100spec": 35,
        "xgb_sensitivity_at_95spec": 0.80,
    }

    (tmp_path / "EvalA_model_results.json").write_text(json.dumps(eval_a))
    (tmp_path / "EvalB_model_results.json").write_text(json.dumps(eval_b))
    return tmp_path


class TestBuildScoreboard:
    """Tests for build_scoreboard()."""

    def test_empty_directory(self, tmp_path):
        """Empty directory returns empty DataFrame."""
        df = build_scoreboard(tmp_path)
        assert df.empty

    def test_two_evaluators_ranked(self, mock_results):
        """Two result files produce 2-row DataFrame sorted by best_auc."""
        df = build_scoreboard(mock_results)
        assert len(df) == 2
        # EvalB has higher AUC (0.91) so should be first
        assert df.iloc[0]["evaluator"] == "EvalB"
        assert df.iloc[1]["evaluator"] == "EvalA"

    def test_best_auc_computed_correctly(self, mock_results):
        """best_auc should be the max of rf, lr, xgb."""
        df = build_scoreboard(mock_results)
        eval_b = df[df["evaluator"] == "EvalB"].iloc[0]
        assert eval_b["best_auc"] == 0.91  # XGB is highest for B

        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["best_auc"] == 0.85  # RF is highest for A

    def test_column_names(self, mock_results):
        """Output has expected column set (v0.0.16+ with holdout + sensitivity)."""
        df = build_scoreboard(mock_results)
        expected = {
            # Core ranking columns
            "evaluator",
            "best_auc",
            "best_model",
            "n_features",
            "cv_folds",
            "sensitivity",
            "specificity",
            "n_samples",
            "n_positive",
            # Selection QC
            "selection_method",
            "n_selected_features",
            "selection_overlap_pct",
            # v0.0.16: clinical sensitivity at fixed specificity
            "sens_at_100spec",
            "sens_at_100spec_healthy",
            "n_detected_at_100spec",
            "sens_at_95spec",
            # v0.0.16: holdout metrics
            "holdout_auc",
            "holdout_sens_100spec",
            "holdout_n_train",
            "holdout_n_test",
            "auc_drop",
            # Per-model AUC columns (dynamic)
            "auc_rf",
            "auc_lr",
            "auc_xgb",
        }
        assert expected.issubset(
            set(df.columns)
        ), f"Missing columns: {expected - set(df.columns)}"

    def test_sensitivity_specificity_extracted(self, mock_results):
        """Sensitivity and specificity are correctly extracted from RF report."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["sensitivity"] == 0.80
        assert eval_a["specificity"] == 0.90

    def test_selection_qc_metadata(self, mock_results):
        """Selection QC metadata is extracted when present."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["selection_method"] == "hybrid_union"
        assert eval_a["n_selected_features"] == 3

    def test_malformed_json_skipped(self, tmp_path):
        """Malformed JSON file is skipped without crashing."""
        (tmp_path / "BadEval_model_results.json").write_text("NOT JSON")
        # Also add one good file
        good = {"auc_rf": 0.70, "auc_lr": None, "auc_xgb": None, "top_features": []}
        (tmp_path / "GoodEval_model_results.json").write_text(json.dumps(good))

        df = build_scoreboard(tmp_path)
        assert len(df) == 1
        assert df.iloc[0]["evaluator"] == "GoodEval"

    def test_none_auc_handled(self, tmp_path):
        """AUC values of None are handled gracefully."""
        data = {
            "auc_rf": None,
            "auc_lr": None,
            "auc_xgb": 0.65,
            "top_features": ["x"],
        }
        (tmp_path / "Sparse_model_results.json").write_text(json.dumps(data))
        df = build_scoreboard(tmp_path)
        assert len(df) == 1
        assert df.iloc[0]["best_auc"] == 0.65

    def test_all_none_auc(self, tmp_path):
        """When all AUCs are None, best_auc is NaN."""
        data = {
            "auc_rf": None,
            "auc_lr": None,
            "auc_xgb": None,
            "top_features": [],
        }
        (tmp_path / "AllNone_model_results.json").write_text(json.dumps(data))
        df = build_scoreboard(tmp_path)
        assert len(df) == 1
        assert np.isnan(df.iloc[0]["best_auc"])


# ── v0.0.16 clinical sensitivity + holdout extraction tests ─────────────────


class TestScoreboardV016:
    """Tests for v0.0.16 scoreboard columns: sensitivity@spec, holdout, auc_drop."""

    def test_sensitivity_at_100spec_extracted(self, mock_results):
        """sens_at_100spec should be extracted for the best model."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["sens_at_100spec"] == 0.62

    def test_sensitivity_at_95spec_extracted(self, mock_results):
        """sens_at_95spec should be extracted for the best model."""
        df = build_scoreboard(mock_results)
        eval_b = df[df["evaluator"] == "EvalB"].iloc[0]
        assert eval_b["sens_at_95spec"] == 0.80

    def test_holdout_auc_extracted(self, mock_results):
        """holdout_auc should be extracted from holdout_{best}_auc."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["holdout_auc"] == 0.82

    def test_holdout_missing_gives_nan(self, mock_results):
        """EvalB has no holdout metrics → holdout_auc should be NaN."""
        df = build_scoreboard(mock_results)
        eval_b = df[df["evaluator"] == "EvalB"].iloc[0]
        assert np.isnan(eval_b["holdout_auc"])

    def test_auc_drop_computed(self, mock_results):
        """auc_drop = best_auc - holdout_auc (positive = overfit)."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        expected_drop = 0.85 - 0.82  # 0.03
        assert abs(eval_a["auc_drop"] - expected_drop) < 1e-10

    def test_auc_drop_nan_when_no_holdout(self, mock_results):
        """auc_drop should be NaN when holdout_auc is missing."""
        df = build_scoreboard(mock_results)
        eval_b = df[df["evaluator"] == "EvalB"].iloc[0]
        assert np.isnan(eval_b["auc_drop"])

    def test_holdout_split_sizes(self, mock_results):
        """holdout_n_train and holdout_n_test should be extracted."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["holdout_n_train"] == 120
        assert eval_a["holdout_n_test"] == 30

    def test_n_detected_at_100spec_extracted(self, mock_results):
        """n_detected_at_100spec should be extracted from best model."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["n_detected_at_100spec"] == 31


# ── GPU model naming tests ──────────────────────────────────────────────────


class TestScoreboardGPUModels:
    """Tests for scoreboard with 4-model GPU naming convention."""

    @pytest.fixture
    def gpu_results(self, tmp_path):
        """Create mock results with CPU + GPU (including _ft variants)."""
        # CPU results for EvalA
        cpu = {
            "auc_rf": 0.82,
            "auc_lr": 0.75,
            "auc_xgb": 0.80,
            "cv_folds_actual": 5,
            "top_features": ["feat1", "feat2"],
        }
        (tmp_path / "EvalA_model_results.json").write_text(json.dumps(cpu))

        # GPU results for EvalA (all 4 variants)
        gpu = {
            "auc_tabpfn": 0.88,
            "auc_tabpfn_ft": 0.92,  # Best overall
            "auc_tabicl": 0.86,
            "auc_tabicl_ft": 0.90,
        }
        (tmp_path / "EvalA_gpu_model_results.json").write_text(json.dumps(gpu))

        return tmp_path

    def test_gpu_auc_columns_discovered(self, gpu_results):
        """Scoreboard should discover auc_tabpfn, auc_tabpfn_ft, etc."""
        df = build_scoreboard(gpu_results)
        assert len(df) == 1
        cols = set(df.columns)
        for model in ["tabpfn", "tabpfn_ft", "tabicl", "tabicl_ft"]:
            assert f"auc_{model}" in cols, f"Missing auc_{model}"

    def test_best_auc_includes_gpu(self, gpu_results):
        """best_auc should consider GPU models too."""
        df = build_scoreboard(gpu_results)
        row = df.iloc[0]
        # tabpfn_ft has the highest AUC (0.92)
        assert row["best_auc"] == 0.92

    def test_best_model_gpu(self, gpu_results):
        """best_model should name the GPU model when it wins."""
        df = build_scoreboard(gpu_results)
        row = df.iloc[0]
        assert row["best_model"] == "tabpfn_ft"

    def test_gpu_only_evaluator(self, tmp_path):
        """Evaluator with only GPU results (no CPU) should still work."""
        gpu_only = {
            "auc_tabpfn": 0.80,
            "auc_tabpfn_ft": 0.85,
        }
        (tmp_path / "GpuOnly_gpu_model_results.json").write_text(json.dumps(gpu_only))
        df = build_scoreboard(tmp_path)
        assert len(df) == 1
        assert df.iloc[0]["best_auc"] == 0.85
        assert df.iloc[0]["best_model"] == "tabpfn_ft"

    def test_mixed_cpu_gpu_ranking(self, tmp_path):
        """CPU-only and CPU+GPU evaluators should rank correctly together."""
        cpu_only = {
            "auc_rf": 0.90,
            "auc_lr": 0.80,
            "auc_xgb": 0.85,
            "top_features": ["a"],
        }
        (tmp_path / "CpuOnly_model_results.json").write_text(json.dumps(cpu_only))

        # GPU evaluator with higher AUC
        cpu_b = {"auc_rf": 0.75, "auc_lr": 0.70}
        gpu_b = {"auc_tabpfn_ft": 0.95}
        (tmp_path / "GpuEval_model_results.json").write_text(json.dumps(cpu_b))
        (tmp_path / "GpuEval_gpu_model_results.json").write_text(json.dumps(gpu_b))

        df = build_scoreboard(tmp_path)
        assert len(df) == 2
        # GpuEval (0.95) should be ranked first
        assert df.iloc[0]["evaluator"] == "GpuEval"
        assert df.iloc[0]["best_auc"] == 0.95
