"""Smoke tests for kreview.report.generate_report (#79 wrapper).

Covers the reachable-without-a-full-outdir guard paths: an invalid outdir returns
None (fail loud in logs, no crash through library callers) and a render exception is
caught. Full rendering is covered by tests/test_report_data.py.
"""

from pathlib import Path

from kreview.report import generate_report


def test_invalid_outdir_returns_none_and_creates_output_dir(tmp_path):
    """A directory without a scoreboard yields None; output_dir is still created."""
    out_dir = tmp_path / "reports"
    result = generate_report(tmp_path / "not_an_outdir", out_dir)
    assert result is None
    assert out_dir.exists()


def test_render_exception_is_caught(tmp_path, monkeypatch):
    """Errors inside rendering are logged and surfaced as None, not raised."""
    import kreview.report_data as rd

    (tmp_path / "scoreboard_combined__all.parquet").write_text("stub")

    def boom(*a, **k):
        raise RuntimeError("bad artifacts")

    monkeypatch.setattr(rd, "render_report", boom)
    assert generate_report(tmp_path, tmp_path / "reports") is None


def test_accepts_str_and_path_inputs(tmp_path):
    """Both str and Path inputs are accepted on the guard path."""
    assert generate_report(str(tmp_path / "x"), str(tmp_path / "y")) is None
    assert generate_report(Path(tmp_path / "x"), Path(tmp_path / "y")) is None
