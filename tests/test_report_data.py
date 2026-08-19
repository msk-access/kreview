"""Tests for kreview.report_data — the #79 single-page report data layer.

Covers:
  - build_report_data structure from a synthetic mini output directory
  - the PHI guarantee: sample ids consumed in memory never reach the output,
    and assert_no_phi fails loud when one is planted
  - patient-leakage detection (patients spanning train/test)
  - fail-loud on missing required inputs
  - render_report produces a self-contained page

The fake sample ids are CONSTRUCTED AT RUNTIME (never literal) so this file cannot
trip the gitleaks PHI rules.
"""

import json

import numpy as np
import pandas as pd
import pytest

from kreview.report_data import (
    assert_no_phi,
    build_report_data,
    render_report,
    write_report_data,
)


def _fake_id(i: int) -> str:
    # Runtime-assembled DMP-shaped id; deliberately not a literal.
    return "P-" + str(1000000 + i) + "-T01-XS1"


@pytest.fixture()
def mini_outdir(tmp_path):
    """A minimal but structurally faithful pipeline output directory."""
    n = 60
    ids = [_fake_id(i) for i in range(n)]
    # patient 0 deliberately has samples in BOTH splits -> leakage count of 1
    patients = ["PT" + str(i // 2) for i in range(n)]
    splits = ["train" if i % 2 == 0 else "test" for i in range(n)]
    splits[1] = "train"  # patient PT0: both samples train -> not leaked
    # PT1 (samples 2,3): one train, one test -> leaked
    splits[2], splits[3] = "train", "test"

    labels = pd.DataFrame(
        {
            "SAMPLE_ID": ids,
            "PATIENT_ID": patients,
            "CANCER_TYPE": ["Lung"] * 30 + ["Breast"] * 30,
            "label": (
                ["True ctDNA+"] * 25
                + ["Possible ctDNA−"] * 25
                + ["Healthy Normal"] * 10
            ),
            "split": splits,
        }
    )
    (tmp_path / "labels").mkdir()
    labels.to_parquet(tmp_path / "labels" / "labels.parquet", index=False)

    sb = pd.DataFrame(
        [
            {"evaluator": "EvalA", "status": "OK", "best_model": "lr", "best_auc": 0.8},
        ]
    )
    sb.to_parquet(tmp_path / "scoreboard_combined__all.parquet", index=False)

    rng = np.random.RandomState(0)
    y = [1] * 25 + [0] * 35
    probs = list(np.clip(rng.rand(n) * 0.5 + np.array(y) * 0.4, 0, 1))
    (tmp_path / "models" / "cpu").mkdir(parents=True)
    mr = {
        "evaluator": "EvalA",
        "auc_lr": 0.8,
        "auc_lr_ci_lower": 0.75,
        "auc_lr_ci_upper": 0.85,
        "lr_fold_aucs": [0.79, 0.81],
        "lr_sensitivity_at_95spec": 0.5,
        "lr_refit_features": ["f1", "f2"],
        "lr_oof_probs": probs,
        "oof_labels": y,
        "oof_sample_ids": ids,
        "oof_sample_labels": ["Healthy Normal"] * 10 + ["True ctDNA+"] * 50,
    }
    (tmp_path / "models" / "cpu" / "EvalA_model_results.json").write_text(
        json.dumps(mr)
    )

    # GPU results live in models/gpu/<eval>_gpu_model_results.json — a separate
    # file with its own exact path (the NF report staging once dumped these into
    # models/cpu/, silently dropping every GPU model from the deep-dive modal).
    (tmp_path / "models" / "gpu").mkdir()
    (tmp_path / "models" / "gpu" / "EvalA_gpu_model_results.json").write_text(
        json.dumps(
            {
                "auc_tabicl": 0.83,
                "auc_tabicl_ci_lower": 0.79,
                "auc_tabicl_ci_upper": 0.87,
                "tabicl_fold_aucs": [0.82, 0.84],
                "oof_sample_ids": ids,
            }
        )
    )

    (tmp_path / "matrices" / "selected").mkdir(parents=True)
    (tmp_path / "matrices" / "selected" / "EvalA_selection_qc.json").write_text(
        json.dumps({"method": "mrmr", "total_input_features": 10, "n_mrmr_selected": 3})
    )

    (tmp_path / "models" / "multimodal").mkdir()
    (tmp_path / "models" / "multimodal" / "prep_metadata.json").write_text(
        json.dumps(
            {
                "best_single_evaluator": "EvalA",
                "best_single_auc": 0.8,
                "multimodal_selection": "boruta_shap",
                "n_evaluators": 1,
                "stacking_shape": [n, 4],
                "single_evaluator_aucs": {"EvalA": 0.8},
            }
        )
    )
    (tmp_path / "models" / "multimodal" / "stacking_rf_results.json").write_text(
        json.dumps({"auc_stacking_rf": 0.82, "stacking_rf_sensitivity_at_95spec": 0.6})
    )
    return tmp_path


class TestBuildReportData:
    def test_structure_and_counts(self, mini_outdir):
        data = build_report_data(mini_outdir, run_label="unit")
        assert data["meta"]["run"] == "unit"
        assert data["cohort"]["n_samples"] == 60
        assert data["cohort"]["label_counts"]["True ctDNA+"] == 25
        assert len(data["evaluators"]) == 1
        ev = data["evaluators"][0]
        assert ev["model_metrics"]["lr"]["auc"] == 0.8
        assert ev["top_features"] == ["f1", "f2"]
        assert "roc" in ev and "dca" in ev and "calibration" in ev
        assert ev["n_healthy_oof"] == 10
        assert data["multimodal"]["models"]["rf"]["stacking"]["auc"] == 0.82

    def test_patient_leakage_detected(self, mini_outdir):
        data = build_report_data(mini_outdir)
        # By construction most patients span train/test (alternating splits) except
        # the pairs fixed to a single split — assert the counter sees the leakage.
        assert data["cohort"]["patients_in_both_splits"] >= 1

    def test_gpu_models_reach_model_metrics(self, mini_outdir):
        """models/gpu results must appear in the deep-dive model metrics."""
        data = build_report_data(mini_outdir)
        mm = data["evaluators"][0]["model_metrics"]
        assert "tabicl" in mm, f"GPU model missing from modal metrics: {sorted(mm)}"
        assert mm["tabicl"]["auc"] == 0.83

    def test_excluded_samples_are_not_split_leakage(self, tmp_path, mini_outdir):
        """A patient with a train sample plus an EXCLUDED sample is not leakage.

        The counter once grouped over every split value and false-flagged 14
        patients on the v0.0.32 iris report — all (exclude, train/test) combos.
        """
        import pandas as pd

        labels = pd.read_parquet(mini_outdir / "labels" / "labels.parquet")
        # Make the split clean (no train/test overlap), then give patient PT0 an
        # extra excluded sample — the counter must stay at 0.
        labels["split"] = [
            "train" if i % 2 == 0 else "test" for i in range(len(labels))
        ]
        labels["PATIENT_ID"] = [f"Q{i}" for i in range(len(labels))]
        labels.loc[labels.index[-1], "PATIENT_ID"] = "Q0"
        labels.loc[labels.index[-1], "split"] = "exclude"
        labels.to_parquet(mini_outdir / "labels" / "labels.parquet", index=False)
        data = build_report_data(mini_outdir)
        assert data["cohort"]["patients_in_both_splits"] == 0

    def test_phantom_ablation_entries_filtered(self, mini_outdir):
        """Pre-fix LOO files carry phantom keys like 'EvalA_tabicl' — dropped."""
        (mini_outdir / "models" / "multimodal" / "ablation_results.json").write_text(
            json.dumps(
                {
                    "ablation_model": "tabicl",
                    "ablation_baseline_auc": 0.85,
                    "ablation": {
                        "EvalA": {"delta": 0.01, "auc_without": 0.84},
                        "EvalA_tabicl": {"delta": 0.001, "auc_without": 0.849},
                        "EvalA_tabpfn_ft": {"delta": 0.002, "auc_without": 0.848},
                    },
                }
            )
        )
        data = build_report_data(mini_outdir)
        deltas = data["multimodal"]["ablation"]["deltas"]
        assert set(deltas) == {"EvalA"}, f"phantoms not filtered: {sorted(deltas)}"

    def test_subgroup_breakdowns_are_aggregates(self, mini_outdir):
        data = build_report_data(mini_outdir)
        bd = data["evaluators"][0].get("breakdowns", {})
        assert "cancer_type" in bd
        for grp in bd["cancer_type"].values():
            assert set(grp) == {"n", "n_pos", "auc"}

    def test_missing_scoreboard_fails_loud(self, tmp_path):
        (tmp_path / "labels").mkdir()
        pd.DataFrame(
            {"SAMPLE_ID": [], "PATIENT_ID": [], "label": [], "CANCER_TYPE": []}
        ).to_parquet(tmp_path / "labels" / "labels.parquet")
        with pytest.raises(FileNotFoundError, match="scoreboard"):
            build_report_data(tmp_path)


class TestPhiGuarantee:
    def test_output_carries_no_sample_ids(self, mini_outdir, tmp_path):
        """The 60 DMP-shaped ids in the inputs must never reach the serialized output."""
        data = build_report_data(mini_outdir)
        out = write_report_data(data, tmp_path / "report_data.json")
        blob = out.read_text()
        assert _fake_id(0) not in blob
        assert "P-1" not in blob  # no id fragment either

    def test_assert_no_phi_fails_loud_on_planted_id(self):
        with pytest.raises(ValueError, match="PHI leak"):
            assert_no_phi(json.dumps({"note": "sample " + _fake_id(3) + " looked odd"}))

    def test_assert_no_phi_catches_id_field_names(self):
        with pytest.raises(ValueError, match="PHI leak"):
            assert_no_phi(json.dumps({"oof_sample_ids": []}).replace("oof_", ""))


class TestRenderReport:
    def test_renders_self_contained_page(self, mini_outdir, tmp_path):
        out = render_report(mini_outdir, tmp_path / "report.html", run_label="unit")
        page = out.read_text()
        assert "plotly" in page.lower()
        assert '"evaluators":' in page
        assert _fake_id(0) not in page
        # Self-contained means no EXTERNAL fetches: no script/link/img pointing at
        # http(s). (plotly.js internally contains the literal string "cdn.plot.ly" as
        # a config default, so a naive substring check false-positives.)
        import re

        externals = re.findall(
            r'<(?:script[^>]+src|link[^>]+href|img[^>]+src)="https?://[^"]+"', page
        )
        assert externals == [], f"page references external resources: {externals[:3]}"
