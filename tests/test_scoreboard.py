"""Tests for kreview.scoreboard — the #108 contract rebuild.

The contract: every field in a scoreboard row is either sourced from a named
artifact/key or explicitly unknown (NaN / None / "unknown") AND listed in
``missing_fields``. No fabricated defaults — the v0.0.29 scoreboard stamped
``legacy_cohens_d`` / 0 / 0.0 / False for fields it never saw, and those values
were indistinguishable from measurements.
"""

import json

import numpy as np
import pandas as pd
import pytest

from kreview.scoreboard import (
    SCOREBOARD_COLUMNS,
    SCOREBOARD_SCHEMA_VERSION,
    build_scoreboard,
    extract_evaluator_summary,
    load_selection_qc,
)


def _complete_results() -> dict:
    """A model-results dict with EVERY summary-contract source key present.

    The drift canary is built on this: if a producer renames a key without the
    extractor learning it, the corresponding field lands in missing_fields and
    ``test_complete_inputs_have_no_missing_fields`` fails.
    """
    return {
        "auc_rf": 0.85,
        "auc_lr": 0.78,
        "auc_xgb": 0.82,
        "cv_folds_actual": 5,
        "nested_cv": True,
        "top_features": ["f1", "f2", "f3"],
        "rf_classification_report": {
            "1": {"recall": 0.80, "support": 50},
            "0": {"recall": 0.90, "support": 100},
            "weighted avg": {"support": 150},
        },
        "rf_sensitivity_at_100spec": 0.62,
        "rf_sensitivity_at_100spec_healthy": 0.58,
        "rf_n_detected_at_100spec": 31,
        "rf_sensitivity_at_95spec": 0.74,
        "holdout_rf_auc": 0.82,
        "holdout_rf_sensitivity_at_100spec": 0.55,
        "holdout_n_train": 120,
        "holdout_n_test": 30,
    }


def _complete_qc() -> dict:
    return {
        "method": "mrmr",
        "n_mrmr_selected": 3,
        "total_input_features": 40,
        "target_percentile": 10.0,
    }


class TestContract:
    def test_complete_inputs_have_no_missing_fields(self):
        """Drift canary: with every source key present, nothing is missing.

        A producer-side key rename (e.g. cv_folds_actual -> cv_folds) breaks this
        test instead of silently degrading the column to NaN forever.
        """
        rec = extract_evaluator_summary("EvalA", _complete_results(), _complete_qc())
        assert rec["missing_fields"] == "", rec["missing_fields"]
        assert rec["n_missing"] == 0
        assert rec["status"] == "OK"
        assert rec["best_model"] == "rf" and rec["best_auc"] == 0.85
        assert rec["selection_method"] == "mrmr"
        assert rec["n_selected_features"] == 3
        assert rec["selection_total_input"] == 40
        assert rec["auc_drop"] == pytest.approx(0.85 - 0.82)
        assert rec["schema_version"] == SCOREBOARD_SCHEMA_VERSION

    def test_fixed_schema(self):
        rec = extract_evaluator_summary("EvalA", _complete_results(), _complete_qc())
        assert tuple(rec.keys()) == SCOREBOARD_COLUMNS

    def test_missing_qc_is_unknown_never_legacy_label(self):
        """The v0.0.29 bug (#107): absent sidecar produced 'legacy_cohens_d'."""
        rec = extract_evaluator_summary("EvalA", _complete_results(), None)
        assert rec["selection_method"] == "unknown"
        assert "selection_method" in rec["missing_fields"]
        assert "legacy_cohens_d" not in str(rec.values())

    def test_absent_nested_cv_is_none_not_false(self):
        data = _complete_results()
        del data["nested_cv"]
        rec = extract_evaluator_summary("EvalA", data, _complete_qc())
        assert rec["nested_cv"] is None
        assert "nested_cv" in rec["missing_fields"]

    def test_gpu_best_model_marks_absent_cpu_only_keys(self):
        """The silent n_features=0 pathology from v0.0.29, now visible: a GPU
        winner has no top_features/holdout keys — those become missing, not 0."""
        data = _complete_results()
        data["auc_tabicl"] = 0.95  # GPU model wins; tabicl-prefixed keys absent
        del data["top_features"]
        rec = extract_evaluator_summary("EvalA", data, _complete_qc())
        assert rec["best_model"] == "tabicl"
        assert rec["n_features"] is None
        for f in ("n_features", "sens_at_100spec", "holdout_auc"):
            assert f in rec["missing_fields"].split(";")

    def test_model_auc_columns_always_present(self):
        rec = extract_evaluator_summary("EvalA", _complete_results(), _complete_qc())
        for m in ("lr", "rf", "xgb", "tabpfn", "tabpfn_ft", "tabicl", "tabicl_ft"):
            assert f"auc_{m}" in rec
        assert np.isnan(rec["auc_tabpfn"])  # didn't run: NaN, NOT a missing field
        assert "auc_tabpfn" not in rec["missing_fields"]

    def test_error_json_yields_failed_status(self):
        rec = extract_evaluator_summary("EvalA", {"error": "cuda OOM"}, None)
        assert rec["status"] == "FAILED"
        assert rec["error_detail"] == "cuda OOM"
        rec2 = extract_evaluator_summary(
            "EvalA", {"error": "gpu fail", "auc_lr": 0.7}, None
        )
        assert rec2["status"] == "PARTIAL"


class TestBuildScoreboard:
    def _write(self, tmp_path, name, results, qc=None):
        (tmp_path / f"{name}_model_results.json").write_text(json.dumps(results))
        if qc is not None:
            (tmp_path / f"{name}_selection_qc.json").write_text(json.dumps(qc))

    def test_empty_directory(self, tmp_path):
        df = build_scoreboard(tmp_path)
        assert df.empty
        assert list(df.columns) == list(SCOREBOARD_COLUMNS)

    def test_ranked_with_sidecars(self, tmp_path):
        self._write(tmp_path, "EvalA", _complete_results(), _complete_qc())
        b = dict(_complete_results(), auc_xgb=0.91)
        self._write(tmp_path, "EvalB", b, _complete_qc())
        df = build_scoreboard(tmp_path)
        assert list(df["evaluator"]) == ["EvalB", "EvalA"]
        assert set(df["selection_method"]) == {"mrmr"}
        assert list(df.columns) == list(SCOREBOARD_COLUMNS)

    def test_malformed_json_yields_failed_row_not_crash(self, tmp_path):
        self._write(tmp_path, "EvalA", _complete_results(), _complete_qc())
        (tmp_path / "EvalBad_model_results.json").write_text("{not json")
        df = build_scoreboard(tmp_path)
        # loader skips unreadable files; the good evaluator still ranks
        assert "EvalA" in set(df["evaluator"])

    def test_sidecars_found_in_published_layout(self, tmp_path):
        """QC sidecars under matrices/selected/ (published outdir) are found too."""
        self._write(tmp_path, "EvalA", _complete_results())
        sel = tmp_path / "matrices" / "selected"
        sel.mkdir(parents=True)
        (sel / "EvalA_selection_qc.json").write_text(json.dumps(_complete_qc()))
        df = build_scoreboard(tmp_path)
        assert df.iloc[0]["selection_method"] == "mrmr"

    def test_schema_version_stamped_on_every_row(self, tmp_path):
        self._write(tmp_path, "EvalA", _complete_results(), _complete_qc())
        df = build_scoreboard(tmp_path)
        assert set(df["schema_version"]) == {SCOREBOARD_SCHEMA_VERSION}


class TestLoadSelectionQc:
    def test_unreadable_sidecar_skipped_loud(self, tmp_path):
        (tmp_path / "EvalA_selection_qc.json").write_text("{broken")
        (tmp_path / "EvalB_selection_qc.json").write_text(json.dumps(_complete_qc()))
        qc = load_selection_qc(tmp_path)
        assert "EvalB" in qc and "EvalA" not in qc
