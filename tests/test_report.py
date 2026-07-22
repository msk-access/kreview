"""Smoke tests for kreview.report.generate_report (#63 — was 0% covered).

Covers the reachable-without-Quarto guard paths: a missing matrix returns None (fail
loud, not a crash) and the output directory is created. The actual Quarto render needs
quarto-cli + real data and is exercised by the Nextflow report stage, not here.
"""

from pathlib import Path

from kreview.report import generate_report


def test_missing_matrix_returns_none_and_creates_outdir(tmp_path):
    """A non-existent matrix yields None (surfaced), and output_dir is still created."""
    out_dir = tmp_path / "reports"
    result = generate_report(tmp_path / "absent_matrix.parquet", out_dir)
    assert result is None
    assert out_dir.exists(), "output_dir should be created even on the guard path"


def test_accepts_str_and_path_inputs(tmp_path):
    """Both str and Path inputs are accepted without a type error (guard path)."""
    out_dir = tmp_path / "out2"
    # str inputs
    assert generate_report(str(tmp_path / "nope.parquet"), str(out_dir)) is None
    # Path inputs
    assert generate_report(Path(tmp_path / "nope.parquet"), Path(out_dir)) is None
