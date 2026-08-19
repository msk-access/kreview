"""Tests for the decomposed multimodal pipeline.

Tests the 4-stage pipeline: prep → single → ablation → merge.
Each function is tested independently with synthetic data.
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from kreview.eval_engine import (
    multimodal_ablation,
    multimodal_eval,
    multimodal_merge,
    multimodal_prep,
    multimodal_single,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _write_json(path: Path, data: dict) -> None:
    """Helper to write JSON files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


@pytest.fixture()
def sample_evaluator_jsons(tmp_path: Path) -> Path:
    """Create synthetic model_results.json files for 3 evaluators.

    Each evaluator has LR and RF OOF probabilities for 20 samples.
    """
    np.random.seed(42)
    n_samples = 20
    labels = [0] * 10 + [1] * 10
    sample_ids = [f"sample_{i}" for i in range(n_samples)]

    for eval_name in ["EvalA", "EvalB", "EvalC"]:
        lr_probs = np.random.rand(n_samples).tolist()
        rf_probs = np.random.rand(n_samples).tolist()

        data = {
            "evaluator": eval_name,
            "oof_labels": labels,
            "oof_sample_ids": sample_ids,
            "lr_oof_probs": lr_probs,
            "rf_oof_probs": rf_probs,
            "auc_lr": float(np.random.uniform(0.6, 0.9)),
            "auc_rf": float(np.random.uniform(0.6, 0.9)),
            "best_model": "rf",
            "best_auc": float(np.random.uniform(0.7, 0.9)),
        }
        _write_json(tmp_path / f"{eval_name}_model_results.json", data)

    return tmp_path


@pytest.fixture()
def stacking_parquet(tmp_path: Path) -> Path:
    """Create a synthetic stacking_matrix.parquet."""
    np.random.seed(42)
    n_samples = 20
    df = pd.DataFrame(
        {
            "EvalA_lr": np.random.rand(n_samples),
            "EvalA_rf": np.random.rand(n_samples),
            "EvalB_lr": np.random.rand(n_samples),
            "EvalB_rf": np.random.rand(n_samples),
            "EvalC_lr": np.random.rand(n_samples),
            "EvalC_rf": np.random.rand(n_samples),
            "_label": [0] * 10 + [1] * 10,
        }
    )
    path = tmp_path / "stacking_matrix.parquet"
    df.to_parquet(path, index=False)
    return path


@pytest.fixture()
def stacking_results(tmp_path: Path, stacking_parquet: Path) -> Path:
    """Run multimodal_single for rf and xgb, producing partial JSONs."""
    for model in ["rf", "xgb"]:
        multimodal_single(
            stacking_matrix_path=stacking_parquet,
            model_name=model,
            n_folds=3,
            random_state=42,
            output_dir=tmp_path,
        )
    return tmp_path


@pytest.fixture()
def stacking_parquet_v0028(tmp_path: Path) -> Path:
    """A stacking matrix in the shape ``multimodal_prep`` actually writes (v0.0.28+).

    The plain ``stacking_parquet`` fixture carries only ``_label``, which is a shape
    production never produces: ``multimodal_prep`` always writes ``_sample_id``, and
    ``_sample_label`` whenever 4-tier labels are available. Those extra *string* columns
    are what break a consumer that forgets to drop them, so any regression test for that
    class of bug must use this fixture.
    """
    np.random.seed(42)
    n_samples = 20
    df = pd.DataFrame(
        {
            "EvalA_lr": np.random.rand(n_samples),
            "EvalA_rf": np.random.rand(n_samples),
            "EvalB_lr": np.random.rand(n_samples),
            "EvalB_rf": np.random.rand(n_samples),
            "EvalC_lr": np.random.rand(n_samples),
            "EvalC_rf": np.random.rand(n_samples),
            "_label": [0] * 10 + [1] * 10,
            # Metadata columns written by multimodal_prep — strings, not features.
            "_sample_id": [f"S{i:03d}" for i in range(n_samples)],
            "_sample_label": ["Healthy Normal"] * 10 + ["True ctDNA+"] * 10,
        }
    )
    path = tmp_path / "stacking_matrix_v0028.parquet"
    df.to_parquet(path, index=False)
    return path


@pytest.fixture()
def stacking_results_v0028(tmp_path: Path, stacking_parquet_v0028: Path) -> Path:
    """Partial stacking JSONs produced from the v0.0.28-shaped matrix."""
    out = tmp_path / "single_v0028"
    out.mkdir()
    for model in ["rf", "xgb"]:
        multimodal_single(
            stacking_matrix_path=stacking_parquet_v0028,
            model_name=model,
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
    return out


@pytest.fixture()
def prep_metadata(tmp_path: Path) -> Path:
    """Create a synthetic prep_metadata.json."""
    metadata = {
        "stacking_columns": ["EvalA_lr", "EvalA_rf", "EvalB_lr", "EvalB_rf"],
        "stacking_shape": [20, 4],
        "n_evaluators": 2,
        "evaluators": ["EvalA", "EvalB"],
        "single_evaluator_aucs": {"EvalA": 0.85, "EvalB": 0.80},
        "best_single_evaluator": "EvalA",
        "best_single_auc": 0.85,
        "multimodal_selection": "mi",
        "top_percentile": 10.0,
        "has_raw_features": False,
        "raw_shape": None,
    }
    path = tmp_path / "prep_metadata.json"
    _write_json(path, metadata)
    return path


# ── Tests: multimodal_prep ────────────────────────────────────────────────────


class TestMultimodalPrep:
    """Tests for multimodal_prep (Stage 1)."""

    def test_produces_stacking_parquet(self, sample_evaluator_jsons, tmp_path):
        """Prep should produce stacking_matrix.parquet."""
        out = tmp_path / "prep_out"
        multimodal_prep(
            results_dir=sample_evaluator_jsons,
            output_dir=out,
        )
        assert (out / "stacking_matrix.parquet").exists()
        assert (out / "prep_metadata.json").exists()

    def test_stacking_matrix_has_label_column(self, sample_evaluator_jsons, tmp_path):
        """Stacking parquet should contain _label column."""
        out = tmp_path / "prep_out"
        multimodal_prep(
            results_dir=sample_evaluator_jsons,
            output_dir=out,
        )
        df = pd.read_parquet(out / "stacking_matrix.parquet")
        assert "_label" in df.columns

    def test_metadata_has_required_keys(self, sample_evaluator_jsons, tmp_path):
        """Prep metadata JSON should contain all required keys."""
        out = tmp_path / "prep_out"
        metadata = multimodal_prep(
            results_dir=sample_evaluator_jsons,
            output_dir=out,
        )
        required_keys = {
            "stacking_columns",
            "stacking_shape",
            "n_evaluators",
            "evaluators",
            "single_evaluator_aucs",
            "best_single_evaluator",
            "best_single_auc",
        }
        assert required_keys.issubset(metadata.keys())

    def test_metadata_n_evaluators_correct(self, sample_evaluator_jsons, tmp_path):
        """Number of evaluators should match JSON files."""
        out = tmp_path / "prep_out"
        metadata = multimodal_prep(
            results_dir=sample_evaluator_jsons,
            output_dir=out,
        )
        assert metadata["n_evaluators"] == 3  # EvalA, EvalB, EvalC

    def test_empty_results_dir_raises(self, tmp_path):
        """Empty results dir should raise ValueError."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(ValueError, match="No .* files in"):
            multimodal_prep(
                results_dir=empty_dir,
                output_dir=tmp_path / "out",
            )

    def test_nonexistent_results_dir_raises(self, tmp_path):
        """Non-existent results dir should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            multimodal_prep(
                results_dir=tmp_path / "nonexistent",
                output_dir=tmp_path / "out",
            )


# ── Tests: multimodal_single ─────────────────────────────────────────────────


class TestMultimodalSingle:
    """Tests for multimodal_single (Stage 2)."""

    def test_produces_stacking_json(self, stacking_parquet, tmp_path):
        """Single should produce stacking_{model}_results.json."""
        out = tmp_path / "single_out"
        multimodal_single(
            stacking_matrix_path=stacking_parquet,
            model_name="rf",
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        assert (out / "stacking_rf_results.json").exists()

    def test_auc_in_output(self, stacking_parquet, tmp_path):
        """Output JSON should contain auc_stacking_rf."""
        out = tmp_path / "single_out"
        results = multimodal_single(
            stacking_matrix_path=stacking_parquet,
            model_name="rf",
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        assert "auc_stacking_rf" in results
        assert isinstance(results["auc_stacking_rf"], float)
        assert 0 <= results["auc_stacking_rf"] <= 1

    def test_lr_model(self, stacking_parquet, tmp_path):
        """LR model should also work."""
        out = tmp_path / "single_out"
        results = multimodal_single(
            stacking_matrix_path=stacking_parquet,
            model_name="lr",
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        assert "auc_stacking_lr" in results

    def test_xgb_model(self, stacking_parquet, tmp_path):
        """XGB model should work."""
        out = tmp_path / "single_out"
        results = multimodal_single(
            stacking_matrix_path=stacking_parquet,
            model_name="xgb",
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        assert "auc_stacking_xgb" in results

    def test_delta_vs_best_single(self, stacking_parquet, tmp_path):
        """When best_single_auc is provided, delta should be computed."""
        out = tmp_path / "single_out"
        results = multimodal_single(
            stacking_matrix_path=stacking_parquet,
            model_name="rf",
            n_folds=3,
            random_state=42,
            best_single_auc=0.75,
            output_dir=out,
        )
        assert "stacking_rf_vs_best_single" in results

    def test_nonexistent_stacking_matrix_raises(self, tmp_path):
        """Missing stacking matrix should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Stacking matrix not found"):
            multimodal_single(
                stacking_matrix_path=tmp_path / "nonexistent.parquet",
                model_name="rf",
                output_dir=tmp_path,
            )

    def test_unknown_model_raises(self, stacking_parquet, tmp_path):
        """Unknown model should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown model"):
            multimodal_single(
                stacking_matrix_path=stacking_parquet,
                model_name="not_a_model",
                output_dir=tmp_path,
            )


# ── Tests: multimodal_ablation ────────────────────────────────────────────────


class TestMultimodalAblation:
    """Tests for multimodal_ablation (Stage 3)."""

    def test_produces_ablation_json(self, stacking_parquet, stacking_results, tmp_path):
        """Ablation should produce ablation_results.json."""
        out = tmp_path / "ablation_out"
        multimodal_ablation(
            stacking_matrix_path=stacking_parquet,
            stacking_results_dir=stacking_results,
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        assert (out / "ablation_results.json").exists()

    def test_ablation_has_model_key(self, stacking_parquet, stacking_results, tmp_path):
        """Ablation should identify the best stacking model."""
        out = tmp_path / "ablation_out"
        results = multimodal_ablation(
            stacking_matrix_path=stacking_parquet,
            stacking_results_dir=stacking_results,
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        assert "ablation_model" in results
        assert results["ablation_model"] in ("rf", "xgb", "lr")

    def test_ablation_has_per_evaluator_deltas(
        self, stacking_parquet, stacking_results, tmp_path
    ):
        """Each evaluator should have a delta in ablation results."""
        out = tmp_path / "ablation_out"
        results = multimodal_ablation(
            stacking_matrix_path=stacking_parquet,
            stacking_results_dir=stacking_results,
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        ablation = results["ablation"]
        assert len(ablation) > 0
        for eval_name, info in ablation.items():
            if "error" not in info:
                assert "delta" in info
                assert "auc_without" in info

    def test_no_results_raises(self, stacking_parquet, tmp_path):
        """No stacking results should raise ValueError."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(ValueError, match="No valid stacking results"):
            multimodal_ablation(
                stacking_matrix_path=stacking_parquet,
                stacking_results_dir=empty_dir,
                output_dir=tmp_path / "out",
            )

    # ── Regression: metadata columns must not reach the model ─────────────────
    # multimodal_prep always writes _sample_id (and _sample_label on v0.0.28+). If
    # ablation only drops _label, those string columns stay in the feature matrix,
    # every model.fit() raises, and the broad except records {"error": ...} for every
    # evaluator while the stage still reports success — a silently empty ablation.

    def test_ablation_succeeds_on_production_shaped_matrix(
        self, stacking_parquet_v0028, stacking_results_v0028, tmp_path
    ):
        """Every evaluator must produce a real result, not an error entry."""
        results = multimodal_ablation(
            stacking_matrix_path=stacking_parquet_v0028,
            stacking_results_dir=stacking_results_v0028,
            n_folds=3,
            random_state=42,
            output_dir=tmp_path / "ablation_v0028",
        )
        ablation = results["ablation"]
        assert ablation, "ablation is empty — no evaluator was evaluated"
        errored = {k: v["error"] for k, v in ablation.items() if "error" in v}
        assert not errored, (
            "metadata columns leaked into the feature matrix, so every evaluator "
            f"failed while the stage reported success: {errored}"
        )
        # Unconditional (not `if "error" not in info`) so this cannot pass vacuously.
        for eval_name, info in ablation.items():
            assert "delta" in info and "auc_without" in info, eval_name

    def test_systematic_failure_raises_instead_of_reporting_success(
        self, stacking_results, tmp_path
    ):
        """If EVERY evaluator fails, the stage must raise, not return a dict of errors.

        Returning ``{"EvalA": {"error": ...}, ...}`` with a success exit is how an empty
        ablation reached downstream consumers unnoticed.
        """
        # Non-numeric FEATURE columns (not metadata) => every model.fit() fails.
        n = 20
        bad = pd.DataFrame(
            {
                "EvalA_lr": ["x"] * n,
                "EvalA_rf": ["x"] * n,
                "EvalB_lr": ["x"] * n,
                "EvalB_rf": ["x"] * n,
                "_label": [0] * 10 + [1] * 10,
            }
        )
        bad_path = tmp_path / "bad_matrix.parquet"
        bad.to_parquet(bad_path, index=False)

        with pytest.raises(RuntimeError, match="every evaluator failed"):
            multimodal_ablation(
                stacking_matrix_path=bad_path,
                stacking_results_dir=stacking_results,
                n_folds=3,
                random_state=42,
                output_dir=tmp_path / "bad_out",
            )

    def test_matrix_without_evaluator_columns_raises(self, stacking_results, tmp_path):
        """A matrix with no '<evaluator>_<model>' columns must fail loudly."""
        n = 20
        df = pd.DataFrame(
            {"_label": [0] * 10 + [1] * 10, "_sample_id": [f"S{i}" for i in range(n)]}
        )
        path = tmp_path / "no_features.parquet"
        df.to_parquet(path, index=False)

        with pytest.raises(ValueError, match="No evaluator columns found"):
            multimodal_ablation(
                stacking_matrix_path=path,
                stacking_results_dir=stacking_results,
                n_folds=3,
                random_state=42,
                output_dir=tmp_path / "nofeat_out",
            )

    def test_ablation_derives_real_evaluators_only(
        self, stacking_parquet_v0028, stacking_results_v0028, tmp_path
    ):
        """No phantom evaluator invented from a metadata column name."""
        results = multimodal_ablation(
            stacking_matrix_path=stacking_parquet_v0028,
            stacking_results_dir=stacking_results_v0028,
            n_folds=3,
            random_state=42,
            output_dir=tmp_path / "ablation_v0028b",
        )
        names = set(results["ablation"])
        assert names == {"EvalA", "EvalB", "EvalC"}, (
            f"expected the three real evaluators, got {sorted(names)} — a name like "
            "'_sample' means metadata columns were split into a fake evaluator"
        )

    def test_ablation_no_phantom_from_ft_suffix(self, stacking_results_v0028, tmp_path):
        """Two-part model suffixes must not mint phantom evaluators.

        rsplit("_", 1) parsed "EvalA_tabicl_ft" into a phantom evaluator
        "EvalA_tabicl" — the v0.0.32 iris run ablated 52 "evaluators" instead of
        26, half of them phantoms that each re-trained the stacking model just to
        drop a single _ft column (doubling the LOO stage's GPU cost).
        """
        np.random.seed(42)
        n = 20
        df = pd.DataFrame(
            {
                "EvalA_lr": np.random.rand(n),
                "EvalA_tabicl": np.random.rand(n),
                "EvalA_tabicl_ft": np.random.rand(n),
                "EvalB_rf": np.random.rand(n),
                "EvalB_tabpfn_ft": np.random.rand(n),
                "_label": [0] * 10 + [1] * 10,
            }
        )
        path = tmp_path / "stacking_ft.parquet"
        df.to_parquet(path, index=False)

        results = multimodal_ablation(
            stacking_matrix_path=path,
            stacking_results_dir=stacking_results_v0028,
            n_folds=3,
            random_state=42,
            output_dir=tmp_path / "ablation_ft",
        )
        names = set(results["ablation"])
        assert names == {
            "EvalA",
            "EvalB",
        }, f"phantom evaluator minted from a _ft column: {sorted(names)}"


# ── Tests: multimodal_merge ──────────────────────────────────────────────────


class TestMultimodalMerge:
    """Tests for multimodal_merge (Stage 4)."""

    def test_produces_unified_json(self, stacking_results, prep_metadata, tmp_path):
        """Merge should produce multimodal_results.json."""
        out = tmp_path / "merge_out"
        multimodal_merge(
            stacking_results_dir=stacking_results,
            prep_metadata_path=prep_metadata,
            output_dir=out,
        )
        assert (out / "multimodal_results.json").exists()

    def test_schema_has_strategy(self, stacking_results, prep_metadata, tmp_path):
        """Merged JSON should have 'strategy' key."""
        out = tmp_path / "merge_out"
        results = multimodal_merge(
            stacking_results_dir=stacking_results,
            prep_metadata_path=prep_metadata,
            output_dir=out,
        )
        assert results["strategy"] == "multimodal"

    def test_stacking_key_contains_aucs(
        self, stacking_results, prep_metadata, tmp_path
    ):
        """Merged stacking dict should contain AUC keys."""
        out = tmp_path / "merge_out"
        results = multimodal_merge(
            stacking_results_dir=stacking_results,
            prep_metadata_path=prep_metadata,
            output_dir=out,
        )
        stacking = results["stacking"]
        auc_keys = [k for k in stacking if k.startswith("auc_stacking_")]
        assert len(auc_keys) >= 2  # rf + xgb at minimum

    def test_merge_with_ablation(
        self, stacking_results, prep_metadata, stacking_parquet, tmp_path
    ):
        """Merge with ablation should include ablation keys."""
        # Run ablation first
        abl_out = tmp_path / "abl"
        multimodal_ablation(
            stacking_matrix_path=stacking_parquet,
            stacking_results_dir=stacking_results,
            n_folds=3,
            random_state=42,
            output_dir=abl_out,
        )

        out = tmp_path / "merge_out"
        results = multimodal_merge(
            stacking_results_dir=stacking_results,
            prep_metadata_path=prep_metadata,
            ablation_path=abl_out / "ablation_results.json",
            output_dir=out,
        )
        assert "ablation" in results
        assert "ablation_model" in results

    def test_missing_metadata_raises(self, tmp_path):
        """Missing prep metadata should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Prep metadata not found"):
            multimodal_merge(
                stacking_results_dir=tmp_path,
                prep_metadata_path=tmp_path / "nonexistent.json",
                output_dir=tmp_path / "out",
            )

    def test_merge_without_stacking_files_warns(self, prep_metadata, tmp_path):
        """Merge with no stacking files should produce empty stacking dict."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        out = tmp_path / "merge_out"
        results = multimodal_merge(
            stacking_results_dir=empty_dir,
            prep_metadata_path=prep_metadata,
            output_dir=out,
        )
        # Should succeed but with empty stacking
        assert results["stacking"] == {}


# ── Tests: Full Pipeline Integration ─────────────────────────────────────────


class TestMultimodalFullPipeline:
    """End-to-end test of the decomposed pipeline."""

    def test_prep_single_ablation_merge(self, sample_evaluator_jsons, tmp_path):
        """Full pipeline: prep → single(rf,xgb) → ablation → merge."""
        prep_out = tmp_path / "prep"
        single_out = tmp_path / "single"
        abl_out = tmp_path / "ablation"
        merge_out = tmp_path / "merge"

        # Stage 1: Prep
        metadata = multimodal_prep(
            results_dir=sample_evaluator_jsons,
            output_dir=prep_out,
        )
        assert (prep_out / "stacking_matrix.parquet").exists()
        assert (prep_out / "prep_metadata.json").exists()

        # Stage 2: Single × 2
        for model in ["rf", "xgb"]:
            multimodal_single(
                stacking_matrix_path=prep_out / "stacking_matrix.parquet",
                model_name=model,
                n_folds=3,
                random_state=42,
                best_single_auc=metadata["best_single_auc"],
                output_dir=single_out,
            )
        assert (single_out / "stacking_rf_results.json").exists()
        assert (single_out / "stacking_xgb_results.json").exists()

        # Stage 3: Ablation
        multimodal_ablation(
            stacking_matrix_path=prep_out / "stacking_matrix.parquet",
            stacking_results_dir=single_out,
            n_folds=3,
            random_state=42,
            output_dir=abl_out,
        )
        assert (abl_out / "ablation_results.json").exists()

        # Stage 4: Merge
        results = multimodal_merge(
            stacking_results_dir=single_out,
            prep_metadata_path=prep_out / "prep_metadata.json",
            ablation_path=abl_out / "ablation_results.json",
            output_dir=merge_out,
        )

        # Verify merged output
        assert (merge_out / "multimodal_results.json").exists()
        assert results["strategy"] == "multimodal"
        assert "stacking" in results
        assert "ablation" in results
        assert "ablation_model" in results
        assert results["n_evaluators"] == 3

        # Verify AUCs exist for both models
        stacking = results["stacking"]
        assert "auc_stacking_rf" in stacking
        assert "auc_stacking_xgb" in stacking


# ── Tests: entry-point parity ─────────────────────────────────────────────────


class TestMultimodalEntryPointParity:
    """`multimodal_eval` and the scattered stages must stay one implementation.

    `multimodal_eval` (single machine) and the Nextflow multistage pipeline both drive
    the same stages, but through different entry points. They were previously separate
    implementations, and the drift between them is what allowed a bug fixed in one path
    to persist in the other. These tests fail if the two ever produce different result
    schemas again.
    """

    # Keys that only the in-process orchestrator can know: they describe a single
    # invocation, whereas the scattered pipeline has no one process that sees them.
    ORCHESTRATOR_ONLY = {
        "models_requested",
        "gpu_models_requested",
        "model_errors",
        "ablation_error",
    }

    def _run_stages_manually(self, results_dir: Path, out: Path, model: str) -> dict:
        """Drive prep -> single -> ablation -> merge the way Nextflow scatters them."""
        out.mkdir(parents=True, exist_ok=True)
        multimodal_prep(results_dir=results_dir, output_dir=out)
        multimodal_single(
            stacking_matrix_path=out / "stacking_matrix.parquet",
            model_name=model,
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        multimodal_ablation(
            stacking_matrix_path=out / "stacking_matrix.parquet",
            stacking_results_dir=out,
            n_folds=3,
            random_state=42,
            output_dir=out,
        )
        return multimodal_merge(
            stacking_results_dir=out,
            prep_metadata_path=out / "prep_metadata.json",
            ablation_path=out / "ablation_results.json",
            output_dir=out,
        )

    def test_both_entry_points_produce_the_same_schema(
        self, sample_evaluator_jsons, tmp_path
    ):
        """Same keys from both drivers, modulo the documented orchestrator-only ones."""
        via_orchestrator = multimodal_eval(
            results_dir=sample_evaluator_jsons, models=("rf",), n_folds=3
        )
        via_stages = self._run_stages_manually(
            sample_evaluator_jsons, tmp_path / "staged", "rf"
        )

        only_orchestrator = set(via_orchestrator) - set(via_stages)
        only_stages = set(via_stages) - set(via_orchestrator)

        assert only_orchestrator <= self.ORCHESTRATOR_ONLY, (
            "multimodal_eval grew keys the scattered pipeline does not produce: "
            f"{sorted(only_orchestrator - self.ORCHESTRATOR_ONLY)}"
        )
        assert not only_stages, (
            "the scattered pipeline produces keys multimodal_eval drops: "
            f"{sorted(only_stages)}"
        )

    def test_orchestrator_reports_what_it_requested(self, sample_evaluator_jsons):
        """The orchestrator-only keys are actually populated, not just declared."""
        results = multimodal_eval(
            results_dir=sample_evaluator_jsons, models=("rf",), n_folds=3
        )
        assert results["models_requested"] == ["rf"]
        assert results["gpu_models_requested"] == []
        # A fully successful run must not advertise failures.
        assert "model_errors" not in results

    def test_no_models_requested_raises(self, sample_evaluator_jsons):
        """An empty model set is a caller error and must fail loudly."""
        with pytest.raises(ValueError, match="no models requested"):
            multimodal_eval(
                results_dir=sample_evaluator_jsons, models=(), gpu_models=(), n_folds=3
            )

    def test_leaves_no_temporary_artifacts_behind(
        self, sample_evaluator_jsons, tmp_path
    ):
        """Intermediates go to a temp dir that is cleaned up; callers persist results."""
        before = set(Path(sample_evaluator_jsons).iterdir())
        multimodal_eval(results_dir=sample_evaluator_jsons, models=("rf",), n_folds=3)
        after = set(Path(sample_evaluator_jsons).iterdir())
        assert after == before, f"stray artifacts written: {sorted(after - before)}"


# ── Tests: multimodal_ablation model fallback (#97) ───────────────────────────

try:
    import tabicl  # noqa: F401

    HAS_TABICL = True
except ImportError:
    HAS_TABICL = False


class TestMultimodalAblationModelFallback:
    """#97: LOO ablation must survive a best model that this environment cannot build.

    On the iris v0.0.29 run the best stacking model was tabicl (GPU-only) but the
    ablation stage runs in the CPU container: _build_model returned None, every
    evaluator ablation failed with a baffling sklearn error, and the whole multimodal
    tail (merge + dashboard) was lost. The fix probes candidates best-AUC-first and
    degrades LOUDLY to the best buildable model, re-baselining deltas against the used
    model's own full-matrix AUC.
    """

    @pytest.mark.skipif(HAS_TABICL, reason="tabicl installed — fallback not reachable")
    def test_gpu_best_model_falls_back_loudly(self, stacking_parquet, tmp_path):
        """Best model unbuildable → falls back to runner-up, records the substitution."""
        results_dir = tmp_path / "singles"
        results_dir.mkdir()
        # tabicl "won" (as on iris) but is not installed in a CPU environment.
        _write_json(
            results_dir / "stacking_tabicl_results.json", {"auc_stacking_tabicl": 0.9}
        )
        _write_json(results_dir / "stacking_rf_results.json", {"auc_stacking_rf": 0.8})

        results = multimodal_ablation(
            stacking_matrix_path=stacking_parquet,
            stacking_results_dir=results_dir,
            n_folds=3,
            random_state=42,
            output_dir=tmp_path / "abl_out",
        )

        # The USED model and baseline are the fallback's — deltas re-baselined against
        # rf's own full-matrix AUC, never against the unbuildable tabicl's 0.9.
        assert results["ablation_model"] == "rf"
        assert results["ablation_baseline_auc"] == 0.8

        fb = results["ablation_model_fallback"]
        assert fb["requested"] == "tabicl"
        assert fb["requested_auc"] == 0.9
        assert fb["used"] == "rf"
        assert fb["used_auc"] == 0.8
        assert "unavailable" in fb["reason"]

        # And the ablation itself actually ran: per-evaluator deltas, no error entries.
        assert results["ablation"], "ablation dict is empty"
        assert all("delta" in v for v in results["ablation"].values()), results[
            "ablation"
        ]

    @pytest.mark.skipif(HAS_TABICL, reason="tabicl installed — fallback not reachable")
    def test_no_buildable_model_raises(self, stacking_parquet, tmp_path):
        """No candidate buildable → RuntimeError naming the models, not 39 sklearn errors."""
        results_dir = tmp_path / "singles"
        results_dir.mkdir()
        _write_json(
            results_dir / "stacking_tabicl_results.json", {"auc_stacking_tabicl": 0.9}
        )

        with pytest.raises(RuntimeError, match="none of the stacking models"):
            multimodal_ablation(
                stacking_matrix_path=stacking_parquet,
                stacking_results_dir=results_dir,
                n_folds=3,
                random_state=42,
                output_dir=tmp_path / "abl_out",
            )

    def test_no_fallback_key_when_best_model_available(
        self, stacking_parquet, tmp_path
    ):
        """Happy path unchanged: buildable best model → no fallback block in results."""
        results_dir = tmp_path / "singles"
        results_dir.mkdir()
        _write_json(results_dir / "stacking_rf_results.json", {"auc_stacking_rf": 0.8})

        results = multimodal_ablation(
            stacking_matrix_path=stacking_parquet,
            stacking_results_dir=results_dir,
            n_folds=3,
            random_state=42,
            output_dir=tmp_path / "abl_out",
        )
        assert results["ablation_model"] == "rf"
        assert "ablation_model_fallback" not in results
