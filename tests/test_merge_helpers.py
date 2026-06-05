"""Tests for kreview.eval_engine merge helpers.

Covers:
  - load_model_results() with CPU-only, GPU-only, and CPU+GPU JSON files
  - load_all_model_results() directory scanning with mixed naming
  - GPU key merge correctness (GPU keys override, metadata preserved)
  - Error handling for malformed JSON, missing directory
"""

import json
import pytest

from kreview.eval_engine import load_model_results, load_all_model_results

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def cpu_gpu_dir(tmp_path):
    """Directory with both CPU and GPU result files for two evaluators."""
    # Evaluator FSCOnTarget: CPU + GPU
    cpu_data = {
        "evaluator": "FSCOnTarget",
        "matrix_path": "/path/to/FSCOnTarget_matrix.parquet",
        "auc_lr": 0.85,
        "auc_rf": 0.88,
        "auc_xgb": 0.82,
        "oof_labels": [0, 1, 0, 1],
        "lr_oof_probs": [0.1, 0.9, 0.2, 0.8],
        "rf_oof_probs": [0.15, 0.85, 0.25, 0.75],
        "top_features": ["feat1", "feat2"],
    }
    gpu_data = {
        "evaluator": "FSCOnTarget",
        "matrix_path": "/path/to/FSCOnTarget_matrix.parquet",
        "auc_tabpfn": 0.92,
        "tabpfn_oof_probs": [0.05, 0.95, 0.1, 0.9],
        "tabpfn_training_time_sec": 12.5,
        "oof_labels": [0, 1, 0, 1],
    }
    (tmp_path / "FSCOnTarget_model_results.json").write_text(json.dumps(cpu_data))
    (tmp_path / "FSCOnTarget_gpu_model_results.json").write_text(json.dumps(gpu_data))

    # Evaluator NPS: CPU-only
    nps_data = {
        "evaluator": "NPS",
        "auc_lr": 0.70,
        "auc_rf": 0.72,
        "oof_labels": [0, 1, 0],
        "top_features": ["nps1"],
    }
    (tmp_path / "NPS_model_results.json").write_text(json.dumps(nps_data))

    return tmp_path


# ── load_model_results() ────────────────────────────────────────────────────


class TestLoadModelResults:
    """Tests for single-evaluator load with merge."""

    def test_cpu_only(self, cpu_gpu_dir):
        """CPU-only evaluator returns CPU data unmodified."""
        result = load_model_results(cpu_gpu_dir, "NPS")
        assert result is not None
        assert result["auc_lr"] == 0.70
        assert "auc_tabpfn" not in result

    def test_cpu_gpu_merge(self, cpu_gpu_dir):
        """CPU+GPU merge includes both CPU and GPU AUCs."""
        result = load_model_results(cpu_gpu_dir, "FSCOnTarget")
        assert result is not None
        # CPU keys preserved
        assert result["auc_lr"] == 0.85
        assert result["auc_rf"] == 0.88
        # GPU keys merged
        assert result["auc_tabpfn"] == 0.92
        assert result["tabpfn_oof_probs"] == [0.05, 0.95, 0.1, 0.9]

    def test_metadata_from_cpu(self, cpu_gpu_dir):
        """Metadata keys (evaluator, matrix_path) come from CPU, not GPU."""
        result = load_model_results(cpu_gpu_dir, "FSCOnTarget")
        assert result["evaluator"] == "FSCOnTarget"
        assert result["matrix_path"] == "/path/to/FSCOnTarget_matrix.parquet"

    def test_gpu_only(self, tmp_path):
        """GPU-only evaluator (no CPU file) returns GPU data."""
        gpu_data = {"auc_tabpfn": 0.91, "oof_labels": [0, 1]}
        (tmp_path / "OnlyGPU_gpu_model_results.json").write_text(json.dumps(gpu_data))
        result = load_model_results(tmp_path, "OnlyGPU")
        assert result is not None
        assert result["auc_tabpfn"] == 0.91

    def test_missing_evaluator(self, cpu_gpu_dir):
        """Non-existent evaluator returns None."""
        result = load_model_results(cpu_gpu_dir, "DoesNotExist")
        assert result is None

    def test_malformed_cpu_json(self, tmp_path):
        """Malformed CPU JSON is handled gracefully."""
        (tmp_path / "Bad_model_results.json").write_text("NOT JSON")
        result = load_model_results(tmp_path, "Bad")
        assert result is None

    def test_malformed_gpu_json_keeps_cpu(self, tmp_path):
        """Malformed GPU JSON keeps CPU results intact."""
        cpu_data = {"auc_lr": 0.80}
        (tmp_path / "Mixed_model_results.json").write_text(json.dumps(cpu_data))
        (tmp_path / "Mixed_gpu_model_results.json").write_text("BAD GPU JSON")
        result = load_model_results(tmp_path, "Mixed")
        assert result is not None
        assert result["auc_lr"] == 0.80


# ── load_all_model_results() ────────────────────────────────────────────────


class TestLoadAllModelResults:
    """Tests for directory-wide scan with merge."""

    def test_discovers_all_evaluators(self, cpu_gpu_dir):
        """Finds all evaluators from both CPU and GPU files."""
        results = load_all_model_results(cpu_gpu_dir)
        assert "FSCOnTarget" in results
        assert "NPS" in results
        assert len(results) == 2

    def test_merged_results_include_gpu(self, cpu_gpu_dir):
        """FSCOnTarget includes GPU AUC in the merged result."""
        results = load_all_model_results(cpu_gpu_dir)
        fsc = results["FSCOnTarget"]
        assert fsc["auc_tabpfn"] == 0.92
        assert fsc["auc_lr"] == 0.85

    def test_empty_directory(self, tmp_path):
        """Empty directory returns empty dict."""
        results = load_all_model_results(tmp_path)
        assert results == {}

    def test_gpu_only_evaluator_discovered(self, tmp_path):
        """GPU-only file (no matching CPU) is discovered."""
        gpu_data = {"auc_tabpfn": 0.88}
        (tmp_path / "GpuOnly_gpu_model_results.json").write_text(json.dumps(gpu_data))
        results = load_all_model_results(tmp_path)
        assert "GpuOnly" in results
        assert results["GpuOnly"]["auc_tabpfn"] == 0.88


# ── Scattered GPU JSON tests (Step 4) ──────────────────────────────────────


class TestScatteredGpuJsons:
    """Tests for per-model scattered GPU JSONs from Nextflow scatter.

    In the new design, each GPU model writes its own JSON:
      FSCOnTarget_tabpfn_gpu_model_results.json
      FSCOnTarget_tabpfn_ft_gpu_model_results.json
    These must be merged into the CPU results.
    """

    @pytest.fixture
    def scattered_dir(self, tmp_path):
        """Directory with CPU + 2 scattered per-model GPU files."""
        # CPU results
        cpu = {
            "evaluator": "FSCOnTarget",
            "auc_lr": 0.85,
            "auc_rf": 0.88,
            "oof_labels": [0, 1, 0, 1],
            "oof_sample_ids": ["S1", "S2", "S3", "S4"],
        }
        (tmp_path / "FSCOnTarget_model_results.json").write_text(json.dumps(cpu))

        # Scattered GPU results — one file per model
        tabpfn = {
            "auc_tabpfn": 0.90,
            "tabpfn_oof_probs": [0.1, 0.9, 0.2, 0.8],
            "evaluator": "FSCOnTarget",
            "oof_labels": [0, 1, 0, 1],
        }
        (tmp_path / "FSCOnTarget_tabpfn_gpu_model_results.json").write_text(
            json.dumps(tabpfn)
        )

        tabicl_ft = {
            "auc_tabicl_ft": 0.93,
            "tabicl_ft_oof_probs": [0.05, 0.95, 0.15, 0.85],
            "evaluator": "FSCOnTarget",
            "oof_labels": [0, 1, 0, 1],
        }
        (tmp_path / "FSCOnTarget_tabicl_ft_gpu_model_results.json").write_text(
            json.dumps(tabicl_ft)
        )

        return tmp_path

    def test_scattered_merge_includes_all_models(self, scattered_dir):
        """All scattered GPU models merge into the CPU result."""
        result = load_model_results(scattered_dir, "FSCOnTarget")
        assert result is not None
        # CPU keys
        assert result["auc_lr"] == 0.85
        assert result["auc_rf"] == 0.88
        # Scattered GPU keys
        assert result["auc_tabpfn"] == 0.90
        assert result["auc_tabicl_ft"] == 0.93
        assert result["tabpfn_oof_probs"] == [0.1, 0.9, 0.2, 0.8]

    def test_scattered_preserves_cpu_metadata(self, scattered_dir):
        """Metadata (evaluator, oof_labels, oof_sample_ids) comes from CPU."""
        result = load_model_results(scattered_dir, "FSCOnTarget")
        assert result["evaluator"] == "FSCOnTarget"
        assert result["oof_sample_ids"] == ["S1", "S2", "S3", "S4"]

    def test_scattered_gpu_only(self, tmp_path):
        """Scattered GPU-only evaluators are discovered."""
        data = {"auc_tabpfn_ft": 0.87}
        (tmp_path / "NPS_tabpfn_ft_gpu_model_results.json").write_text(
            json.dumps(data)
        )
        result = load_model_results(tmp_path, "NPS")
        assert result is not None
        assert result["auc_tabpfn_ft"] == 0.87

    def test_load_all_discovers_scattered(self, scattered_dir):
        """load_all_model_results discovers evaluators from scattered files."""
        results = load_all_model_results(scattered_dir)
        assert "FSCOnTarget" in results
        fsc = results["FSCOnTarget"]
        assert fsc["auc_tabpfn"] == 0.90
        assert fsc["auc_tabicl_ft"] == 0.93

    def test_monolithic_plus_scattered_coexist(self, tmp_path):
        """Monolithic GPU JSON and scattered GPU JSON merge correctly."""
        cpu = {"auc_lr": 0.80, "oof_labels": [0, 1]}
        (tmp_path / "Eval_model_results.json").write_text(json.dumps(cpu))

        # Monolithic GPU
        mono = {"auc_tabpfn": 0.85}
        (tmp_path / "Eval_gpu_model_results.json").write_text(json.dumps(mono))

        # Scattered GPU
        scat = {"auc_tabicl_ft": 0.90}
        (tmp_path / "Eval_tabicl_ft_gpu_model_results.json").write_text(
            json.dumps(scat)
        )

        result = load_model_results(tmp_path, "Eval")
        assert result["auc_lr"] == 0.80
        assert result["auc_tabpfn"] == 0.85
        assert result["auc_tabicl_ft"] == 0.90

