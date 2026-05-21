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
    """Create two mock *_model_results.json files with known AUCs."""
    # Evaluator A: best AUC = 0.85 (RF)
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
    }
    # Evaluator B: best AUC = 0.91 (XGB)
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
        """Output has expected column set."""
        df = build_scoreboard(mock_results)
        expected = {
            "evaluator", "auc_rf", "auc_lr", "auc_xgb", "best_auc",
            "n_features", "cv_folds", "sensitivity_rf", "specificity_rf",
            "optimal_threshold_rf", "n_samples", "n_positive",
            "selection_method", "n_selected_features", "selection_overlap_pct",
        }
        assert set(df.columns) == expected

    def test_sensitivity_specificity_extracted(self, mock_results):
        """Sensitivity and specificity are correctly extracted from RF report."""
        df = build_scoreboard(mock_results)
        eval_a = df[df["evaluator"] == "EvalA"].iloc[0]
        assert eval_a["sensitivity_rf"] == 0.80
        assert eval_a["specificity_rf"] == 0.90

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
