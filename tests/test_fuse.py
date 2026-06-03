"""Tests for fuse_matrices() function."""

import pandas as pd
import pytest


class TestFuseMatrices:
    """Tests for kreview.core.fuse_matrices."""

    @pytest.fixture()
    def fuse_dir(self, tmp_path):
        """Create a temp dir with two mock evaluator matrices."""
        # Shared metadata columns
        meta = {
            "SAMPLE_ID": ["S1", "S2", "S3"],
            "label": ["True ctDNA+", "Possible ctDNA+", "Healthy Normal"],
            "max_vaf": [0.15, 0.08, 0.0],
            "mean_vaf": [0.12, 0.06, 0.0],
            "std_vaf": [0.03, 0.02, 0.0],
            "access_version": ["XS1", "XS1", "XS2"],
        }

        # Evaluator A: has all 3 samples
        df_a = pd.DataFrame(
            {
                **meta,
                "ratio_short": [0.5, 0.6, 0.4],
                "ratio_long": [0.3, 0.2, 0.1],
            }
        )
        df_a.to_parquet(tmp_path / "EvalA_matrix.parquet", index=False)

        # Evaluator B: has only S1 and S2 (not S3)
        df_b = pd.DataFrame(
            {
                "SAMPLE_ID": ["S1", "S2"],
                "label": ["True ctDNA+", "Possible ctDNA+"],
                "max_vaf": [0.15, 0.08],
                "mean_vaf": [0.12, 0.06],
                "std_vaf": [0.03, 0.02],
                "access_version": ["XS1", "XS1"],
                "entropy": [2.1, 3.4],
                "gc_content": [0.45, 0.51],
            }
        )
        df_b.to_parquet(tmp_path / "EvalB_matrix.parquet", index=False)

        return tmp_path

    def test_basic_fusion(self, fuse_dir):
        """Two evaluators should fuse into prefixed columns."""
        from kreview.core import fuse_matrices

        result = fuse_matrices(fuse_dir)

        assert len(result) == 3, f"Expected 3 samples, got {len(result)}"
        assert "EvalA__ratio_short" in result.columns
        assert "EvalA__ratio_long" in result.columns
        assert "EvalB__entropy" in result.columns
        assert "EvalB__gc_content" in result.columns

    def test_metadata_preserved(self, fuse_dir):
        """Metadata columns should be unprefixed and present."""
        from kreview.core import fuse_matrices

        result = fuse_matrices(fuse_dir)

        assert "label" in result.columns
        assert "max_vaf" in result.columns
        assert "mean_vaf" in result.columns

    def test_min_evaluators_filter(self, fuse_dir):
        """min_evaluators=2 should drop S3 (only in EvalA)."""
        from kreview.core import fuse_matrices

        result = fuse_matrices(fuse_dir, min_evaluators=2)

        assert len(result) == 2
        assert "S3" not in result["SAMPLE_ID"].values

    def test_n_evaluators_column(self, fuse_dir):
        """Each sample should have correct n_evaluators count."""
        from kreview.core import fuse_matrices

        result = fuse_matrices(fuse_dir)
        result_indexed = result.set_index("SAMPLE_ID")

        assert result_indexed.loc["S1", "n_evaluators"] == 2
        assert result_indexed.loc["S3", "n_evaluators"] == 1

    def test_output_written(self, fuse_dir):
        """super_matrix.parquet should be written to disk."""
        from kreview.core import fuse_matrices

        fuse_matrices(fuse_dir)
        assert (fuse_dir / "super_matrix.parquet").exists()

    def test_empty_dir(self, tmp_path):
        """Empty directory should return empty DataFrame."""
        from kreview.core import fuse_matrices

        result = fuse_matrices(tmp_path)
        assert result.empty

    def test_super_matrix_excluded(self, fuse_dir):
        """Existing super_matrix should not be included in inputs."""
        from kreview.core import fuse_matrices

        # First fuse creates super_matrix.parquet
        fuse_matrices(fuse_dir)
        # Second fuse should not recursively include it
        result = fuse_matrices(fuse_dir)

        # Should NOT have super_matrix__* prefixed columns
        super_cols = [c for c in result.columns if c.startswith("super_matrix__")]
        assert len(super_cols) == 0, f"Unexpected recursive columns: {super_cols}"

    def test_custom_output_name(self, fuse_dir):
        """Custom output_name should be respected."""
        from kreview.core import fuse_matrices

        fuse_matrices(fuse_dir, output_name="combined.parquet")
        assert (fuse_dir / "combined.parquet").exists()

    def test_zero_variance_dropped(self, tmp_path):
        """Constant features should be dropped when drop_low_variance=True."""
        from kreview.core import fuse_matrices

        df = pd.DataFrame(
            {
                "SAMPLE_ID": ["S1", "S2", "S3"],
                "label": ["a", "b", "c"],
                "varying": [0.1, 0.9, 0.5],
                "constant": [1.0, 1.0, 1.0],  # zero variance
            }
        )
        df.to_parquet(tmp_path / "TestEval_matrix.parquet", index=False)

        result = fuse_matrices(tmp_path, drop_low_variance=True)

        assert "TestEval__varying" in result.columns
        assert "TestEval__constant" not in result.columns

    def test_drop_low_variance_disabled(self, tmp_path):
        """drop_low_variance=False should keep constant features."""
        from kreview.core import fuse_matrices

        df = pd.DataFrame(
            {
                "SAMPLE_ID": ["S1", "S2"],
                "label": ["a", "b"],
                "constant": [5.0, 5.0],
            }
        )
        df.to_parquet(tmp_path / "NoFilter_matrix.parquet", index=False)

        result = fuse_matrices(tmp_path, drop_low_variance=False)

        assert "NoFilter__constant" in result.columns
