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

from kreview.pipeline_diagram import CLUSTERS
from kreview.report_data import (
    assert_no_phi,
    build_report_data,
    render_report,
    write_report_data,
)


def _fake_id(i: int) -> str:
    # Runtime-assembled DMP-shaped id; deliberately not a literal.
    return "P-" + str(1000000 + i) + "-T01-XS1"


def _write_outdir(
    tmp_path, n_pos=25, n_neg=25, n_donor=10, oof_labels=None, mixed_cancer_types=False
):
    """Build a structurally faithful output directory at a chosen size.

    Parameterised because the TN-anchored operating point only computes above 200
    verified negatives — at the 60-sample default the report's *primary endpoint*
    silently never runs, so nothing exercised it until `anchor_outdir` existed.
    """
    n = n_pos + n_neg + n_donor
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
            # halves put every positive in one histology and every negative in the
            # other, which no per-class floor can pass; interleaving gives subgroups
            # that look like a real cohort
            "CANCER_TYPE": (
                ["Lung", "Breast"] * (n // 2) + ["Lung"] * (n % 2)
                if mixed_cancer_types
                else ["Lung"] * (n // 2) + ["Breast"] * (n - n // 2)
            ),
            "label": (
                ["True ctDNA+"] * n_pos
                + ["Possible ctDNA−"] * n_neg
                + ["Healthy Normal"] * n_donor
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
    y = [1] * n_pos + [0] * (n_neg + n_donor)
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
        "oof_sample_labels": (
            oof_labels
            if oof_labels is not None
            else ["Healthy Normal"] * 10 + ["True ctDNA+"] * 50
        ),
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


@pytest.fixture
def mini_outdir(tmp_path):
    """A minimal but structurally faithful pipeline output directory."""
    return _write_outdir(tmp_path)


@pytest.fixture
def anchor_outdir(tmp_path):
    """Large enough for the TN-anchored primary endpoint to actually compute.

    Label tiers are internally consistent here (the small fixture's oof_sample_labels
    deliberately are not — several tests depend on that mismatch), and the negatives
    clear the 200-sample gate that guards the anchored block.
    """
    n_pos, n_neg, n_donor = 300, 300, 40
    labels = (
        ["True ctDNA+"] * n_pos
        + ["Possible ctDNA−"] * n_neg
        + ["Healthy Normal"] * n_donor
    )
    out = _write_outdir(
        tmp_path, n_pos, n_neg, n_donor, oof_labels=labels, mixed_cancer_types=True
    )
    import pandas as pd

    lb = pd.read_parquet(out / "labels" / "labels.parquet")
    # qualified TN = paired tumour sequencing AND zero confirmed variants in plasma
    lb["has_paired_impact"] = True
    lb["n_impact_confirmed"] = 0
    lb.loc[lb["label"] == "True ctDNA+", "n_impact_confirmed"] = 2
    lb["max_vaf"] = 0.0
    lb.loc[lb["label"] == "True ctDNA+", "max_vaf"] = 0.05
    lb.to_parquet(out / "labels" / "labels.parquet", index=False)
    return out


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

    def test_findings_derived_and_structured(self, mini_outdir):
        """The findings engine emits structured, tab-tagged inferences."""
        data = build_report_data(mini_outdir)
        fs = data["findings"]
        assert fs, "no findings derived"
        assert all(f["kind"] in {"good", "info", "warn"} for f in fs)
        assert all(
            f["tab"] in {"overview", "scoreboard", "multimodal", "diagnostics"}
            for f in fs
        )
        # The fixture has patients spanning train/test -> the leakage warning fires.
        assert any(
            "BOTH train and test" in f["text"] and f["kind"] == "warn" for f in fs
        )
        # Stacking beats the best single in the fixture -> the stacking finding fires.
        assert any("Stacking" in f["text"] for f in fs)

    def test_findings_clean_split_yields_good(self, mini_outdir):
        """With a clean patient-grouped split, the good-split finding replaces the warning."""
        import pandas as pd

        labels = pd.read_parquet(mini_outdir / "labels" / "labels.parquet")
        labels["split"] = [
            "train" if i % 2 == 0 else "test" for i in range(len(labels))
        ]
        labels["PATIENT_ID"] = [f"Q{i}" for i in range(len(labels))]
        labels.to_parquet(mini_outdir / "labels" / "labels.parquet", index=False)
        fs = build_report_data(mini_outdir)["findings"]
        assert any("split intact" in f["text"] and f["kind"] == "good" for f in fs)
        assert not any("BOTH train and test" in f["text"] for f in fs)

    def test_primary_endpoint_carries_a_clustered_interval(self, anchor_outdir):
        """The headline is an estimate; it ships with an interval, or says why not."""
        data = build_report_data(anchor_outdir)
        tn = ((data.get("primary") or {}).get("operating_points") or {}).get(
            "tn_anchor"
        )
        assert tn, "the anchored block must compute on a fixture above the TN gate"
        assert tn["n_tn"] >= 200 and tn["n_tn_patients"]
        assert "patient-clustered" in tn["ci_method"]
        lo, hi = tn["sens_at_98spec_ci"]
        assert lo <= tn["sens_at_98spec"] <= hi
        # the width is decomposed, never quoted as one conflated ratio
        assert tn["sens_at_98spec_deff"] > 0
        assert tn["sens_at_98spec_threshold_inflation"] > 0

    def test_missing_patient_column_fails_loudly(self, anchor_outdir):
        """PATIENT_ID is required, so its absence must name itself, not raise a KeyError
        from three frames down inside pandas."""
        import pandas as pd

        lb = pd.read_parquet(anchor_outdir / "labels" / "labels.parquet")
        lb.drop(columns=["PATIENT_ID"]).to_parquet(
            anchor_outdir / "labels" / "labels.parquet", index=False
        )
        with pytest.raises(KeyError, match="PATIENT_ID"):
            build_report_data(anchor_outdir)

    def test_operating_points_record_why_an_interval_is_absent(self):
        """The anchored block itself degrades when handed a frame with no patients —
        it reports the point estimate and records that the interval is unavailable,
        rather than substituting a narrower one."""
        from kreview.report_data import _anchored_operating_points

        rng = np.random.default_rng(0)
        n_pos, n_tn = 400, 400
        y = np.array([1] * n_pos + [0] * n_tn)
        p_arr = np.concatenate([rng.normal(1.2, 1, n_pos), rng.normal(0, 1, n_tn)])
        ids = [f"S{i}" for i in range(n_pos + n_tn)]
        lab = pd.DataFrame(
            {
                "SAMPLE_ID": ids,
                "label": ["True ctDNA+"] * n_pos + ["Possible ctDNA−"] * n_tn,
                "has_paired_impact": True,
                "n_impact_confirmed": [2] * n_pos + [0] * n_tn,
            }
        ).set_index("SAMPLE_ID")
        out = _anchored_operating_points(y, p_arr, ids, lab)
        tn = out["tn_anchor"]
        assert "unavailable" in tn["ci_method"]
        assert "sens_at_98spec_ci" not in tn
        assert tn["sens_at_98spec"] is not None

    def test_cluster_bootstrap_widens_with_clustering(self):
        """Repeated timepoints must not be counted as independent observations."""
        from kreview.report_data import _cluster_bootstrap_sens

        rng = np.random.default_rng(0)
        # 60 patients x 8 identical-ish timepoints: sample-level resampling sees 480
        # independent draws, patient-level resampling sees 60 — the interval must widen
        per_patient = rng.normal(size=60)
        p_pos = np.repeat(per_patient, 8) + rng.normal(scale=0.05, size=480) + 1.0
        pat_pos = np.repeat(np.arange(60), 8)
        p_tn = rng.normal(size=480)
        pat_tn = np.repeat(np.arange(1000, 1060), 8)
        lo_c, hi_c = _cluster_bootstrap_sens(p_pos, p_tn, pat_pos, pat_tn, 0.98)
        lo_i, hi_i = _cluster_bootstrap_sens(
            p_pos, p_tn, pat_pos, pat_tn, 0.98, cluster=False
        )
        assert None not in (lo_c, hi_c, lo_i, hi_i)
        assert (hi_c - lo_c) > (hi_i - lo_i), (
            "clustered interval must be wider than the sample-level one when "
            f"timepoints repeat: {hi_c - lo_c:.4f} vs {hi_i - lo_i:.4f}"
        )

    def test_cluster_bootstrap_degrades_without_enough_negatives(self):
        from kreview.report_data import _cluster_bootstrap_sens

        assert _cluster_bootstrap_sens(
            np.array([0.9, 0.8]), np.array([0.1]), np.array([1, 2]), np.array([3]), 0.98
        ) == (None, None)

    def test_dual_anchor_operating_points(self, mini_outdir):
        """#123: TN-anchored points, one-sided donor bound, verification-bias AUCs."""
        import pandas as pd

        # give the fixture a qualified-TN population: paired IMPACT, zero confirmed
        labels = pd.read_parquet(mini_outdir / "labels" / "labels.parquet")
        labels["has_paired_impact"] = True
        labels["n_impact_confirmed"] = 0
        labels.loc[labels["label"] == "True ctDNA+", "n_impact_confirmed"] = 2
        labels.loc[labels["label"] == "True ctDNA+", "label"] = "True ctDNA+"
        labels.loc[labels["label"] == "Possible ctDNA−", "label"] = "Possible ctDNA−"
        labels.to_parquet(mini_outdir / "labels" / "labels.parquet", index=False)

        data = build_report_data(mini_outdir)
        ops = data["primary"]["operating_points"]
        assert "auc_vs_all_negatives" in ops
        don = ops.get("donor_anchor")
        assert don and "sens_at_100spec_lower_bound" in don
        # the donor number must NEVER be presented as a two-sided point estimate
        assert "sens_at_100spec" not in don
        assert data["primary"]["evaluator"] and data["primary"]["model"]
        # winner's-curse annotation: the a-priori primary is reported with the argmax
        assert "argmax_evaluator" in data["primary"]

    def test_operating_points_absent_degrades_quietly(self, mini_outdir):
        """No TN population (and no crash) when the label columns are missing."""
        import pandas as pd

        labels = pd.read_parquet(mini_outdir / "labels" / "labels.parquet")
        labels = labels.drop(
            columns=[
                c for c in ("has_paired_impact", "n_impact_confirmed") if c in labels
            ]
        )
        labels.to_parquet(mini_outdir / "labels" / "labels.parquet", index=False)
        ops = build_report_data(mini_outdir)["primary"]["operating_points"]
        assert "tn_anchor" not in ops  # explicitly absent, never fabricated
        assert ops.get("auc_vs_all_negatives") is not None

    def test_lod_curve_and_tradeoff(self):
        """The burden-response curve and spec/sens trade-off, built directly from
        OOF arrays: sensitivity must fall as specificity tightens, and detection
        must rise with tumor burden (the curve that makes every other number
        interpretable)."""
        import numpy as np
        import pandas as pd

        from kreview.report_data import _anchored_operating_points

        rng = np.random.RandomState(0)
        n_pos, n_tn = 400, 400
        ids = [f"S{i}" for i in range(n_pos + n_tn)]
        y = np.array([1] * n_pos + [0] * n_tn)
        # positives: score rises with burden; negatives: low scores
        vaf = np.concatenate([np.geomspace(0.0005, 0.4, n_pos), np.zeros(n_tn)])
        score = np.concatenate(
            [
                np.clip(0.25 + 0.55 * (np.log10(vaf[:n_pos]) + 3.3) / 3.0, 0, 1)
                + rng.normal(0, 0.05, n_pos),
                rng.uniform(0, 0.45, n_tn),
            ]
        )
        lab = pd.DataFrame(
            {
                "SAMPLE_ID": ids,
                "PATIENT_ID": ids,
                "label": ["True ctDNA+"] * n_pos + ["Possible ctDNA−"] * n_tn,
                "has_paired_impact": True,
                "n_impact_confirmed": [2] * n_pos + [0] * n_tn,
                "max_vaf": vaf,
            }
        ).set_index("SAMPLE_ID")

        ops = _anchored_operating_points(y, score, ids, lab)
        c = ops["sens_spec_curve"]
        assert len(c["spec"]) == len(c["sens"]) > 5
        assert all(
            b <= a + 1e-9 for a, b in zip(c["sens"], c["sens"][1:])
        ), "sensitivity must not rise as specificity tightens"

        lod = ops["lod"]
        det = [b["detected"] for b in lod["bins"]]
        assert len(det) >= 4
        assert det[0] < det[-1], "detection must rise with tumor burden"
        assert 0 < lod["lod50_vaf"] < 1
        # TF ~ 2 x VAF for a clonal heterozygous variant
        assert lod["lod50_tumor_fraction"] == pytest.approx(
            2 * lod["lod50_vaf"], rel=1e-6
        )
        for b in lod["bins"]:
            assert b["ci"][0] <= b["detected"] <= b["ci"][1]

    def test_wilson_interval_bounds(self):
        """Wilson beats the normal approximation exactly where the LOD curve lives:
        tiny p and small n, where normal CIs go below zero."""
        from kreview.report_data import _wilson

        lo, hi = _wilson(0, 50)
        assert lo == 0.0 and 0 < hi < 0.15
        lo, hi = _wilson(25, 50)
        assert lo < 0.5 < hi
        lo, hi = _wilson(50, 50)
        assert hi == 1.0 and 0.9 < lo < 1.0

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

    def test_subgroup_gate_counts_the_scarce_class(self, anchor_outdir):
        """A floor on total n lets a group through on its negatives alone."""
        import pandas as pd

        from kreview.report_data import MIN_SUBGROUP_CLASS

        lb = pd.read_parquet(anchor_outdir / "labels" / "labels.parquet")
        # a histology with plenty of samples but almost no positives — the shape that
        # produced a meaningless retinoblastoma statistic in review
        pos_idx = lb.index[lb["label"] == "True ctDNA+"][:5]
        neg_idx = lb.index[lb["label"] == "Possible ctDNA−"][:200]
        lb.loc[list(pos_idx) + list(neg_idx), "CANCER_TYPE"] = "Thin Positives"
        lb.to_parquet(anchor_outdir / "labels" / "labels.parquet", index=False)
        data = build_report_data(anchor_outdir)
        groups = data["evaluators"][0].get("breakdowns", {}).get("cancer_type", {})
        assert (
            "Thin Positives" not in groups
        ), f"a group with 5 positives cleared a floor of {MIN_SUBGROUP_CLASS} per class"

    def test_subgroup_rows_carry_tier_composition(self, anchor_outdir):
        """AUC alone hides that a group's positives may be mostly the ambiguous tier."""
        data = build_report_data(anchor_outdir)
        groups = data["evaluators"][0].get("breakdowns", {}).get("cancer_type", {})
        if not groups:
            pytest.skip("fixture produced no subgroup above the per-class floor")
        for name, row in groups.items():
            assert "pct_true_pos" in row, name
            assert 0.0 <= row["pct_true_pos"] <= 1.0

    def test_subgroup_intervals_only_on_the_primary_evaluator(self, anchor_outdir):
        """Every other subgroup table is exploratory; bootstrapping all of them costs
        minutes of build time for panels that carry no declared claim."""
        from kreview.report_data import PRIMARY_EVALUATOR

        data = build_report_data(anchor_outdir)
        for e in data["evaluators"]:
            rows = (e.get("breakdowns") or {}).get("cancer_type") or {}
            has_ci = any("ci" in r for r in rows.values())
            if e["evaluator"] != PRIMARY_EVALUATOR:
                assert (
                    not has_ci
                ), f"{e['evaluator']} should not carry subgroup intervals"

    def test_subgroup_breakdowns_are_aggregates(self, anchor_outdir):
        """Counts and rates only — never anything that could identify a sample.

        Asserts a subset of an allowed key set rather than exact equality: the point of
        this test is that no identifier leaks in, and an exact match breaks whenever a
        legitimate aggregate (an interval, a tier share) is added.
        """
        allowed = {"n", "n_pos", "auc", "ci", "pct_true_pos"}
        data = build_report_data(anchor_outdir)
        bd = data["evaluators"][0].get("breakdowns", {})
        assert "cancer_type" in bd and bd["cancer_type"]
        for name, grp in bd["cancer_type"].items():
            extra = set(grp) - allowed
            assert not extra, f"{name} carries unexpected keys {extra}"
            assert isinstance(grp["n"], int) and isinstance(grp["n_pos"], int)

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

    def test_pipeline_diagram_is_injected(self, mini_outdir, tmp_path):
        out = render_report(mini_outdir, tmp_path / "report.html", run_label="unit")
        page = out.read_text()
        # every injection token must be consumed -- a leftover placeholder ships a
        # literal "__PIPELINE_METHODS__" into the page
        assert "__PIPELINE" not in page
        # two layouts in Methods (overview + standard), one in Run diagnostics
        assert page.count('class="pd-dag"') == 3
        assert page.count('<div data-cluster="') == len(CLUSTERS)
        assert '"pipeline":' in page
