"""Smoke tests for all kreview CLI commands.

Verifies every subcommand is registered and shows ``--help`` without error.
These are cheap sanity checks — they do NOT exercise actual pipeline logic
(that requires data fixtures).  They catch:
- Missing imports or registration
- Typer signature errors (wrong type annotations, missing defaults)
- Broken subcommand wiring (add_typer vs app.command)
"""

import pytest
from typer.testing import CliRunner

from kreview.cli import app

runner = CliRunner()


# ── Top-level ──


class TestTopLevel:
    """Verify the main ``kreview`` CLI entry point."""

    def test_help(self):
        """``kreview --help`` returns exit code 0."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0, result.output

    def test_help_lists_all_commands(self):
        """All registered commands appear in the help output."""
        result = runner.invoke(app, ["--help"])
        expected_commands = [
            "label",
            "extract",
            "fuse",
            "select",
            "report",
            "features-list",
            "eval",
        ]
        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not found in --help output"

    def test_monolithic_run_command_is_gone(self):
        """`kreview run` was removed; the pipeline is Nextflow-multistage only.

        Guards against the legacy all-in-one orchestrator being reintroduced. It was a
        second, drifting implementation of the whole pipeline (see #55) and the single
        largest source of the fix-one-path-miss-the-other bugs.
        """
        assert "run" not in [
            (c.name or c.callback.__name__) for c in app.registered_commands
        ], "the monolithic `run` command was reintroduced"
        assert runner.invoke(app, ["run", "--help"]).exit_code != 0


# ── Standalone commands ──


class TestStandaloneCommands:
    """Smoke test each standalone command's --help."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "label",
            "extract",
            "fuse",
            "select",
            "report",
            "features-list",
        ],
    )
    def test_help(self, cmd):
        """``kreview <cmd> --help`` returns exit code 0."""
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0, f"{cmd}: {result.output}"


# ── Eval subcommand group ──


class TestEvalSubcommands:
    """Smoke test the ``kreview eval`` subcommand group."""

    def test_eval_help(self):
        """``kreview eval --help`` returns exit code 0."""
        result = runner.invoke(app, ["eval", "--help"])
        assert result.exit_code == 0, result.output

    @pytest.mark.parametrize("sub", ["cpu", "gpu", "multimodal", "ablate"])
    def test_eval_sub_help(self, sub):
        """``kreview eval <sub> --help`` returns exit code 0."""
        result = runner.invoke(app, ["eval", sub, "--help"])
        assert result.exit_code == 0, f"eval {sub}: {result.output}"

    @pytest.mark.parametrize("sub", ["cpu", "gpu", "merge"])
    def test_eval_ablate_sub_help(self, sub):
        """``kreview eval ablate <sub> --help`` returns exit code 0 (full nested tree)."""
        result = runner.invoke(app, ["eval", "ablate", sub, "--help"])
        assert result.exit_code == 0, f"eval ablate {sub}: {result.output}"

    @pytest.mark.parametrize("sub", ["run", "prep", "single", "ablation", "merge"])
    def test_eval_multimodal_sub_help(self, sub):
        """``kreview eval multimodal <sub> --help`` returns exit code 0 (full nested tree)."""
        result = runner.invoke(app, ["eval", "multimodal", sub, "--help"])
        assert result.exit_code == 0, f"eval multimodal {sub}: {result.output}"


# ── Parameter validation ──


class TestParameterValidation:
    """Verify parameter validation catches bad input early."""

    def test_select_missing_required(self):
        """``kreview select`` without --matrices-dir fails with non-zero exit."""
        result = runner.invoke(app, ["select"])
        assert result.exit_code != 0

    def test_fuse_missing_required(self):
        """``kreview fuse`` without --output-dir fails with non-zero exit."""
        result = runner.invoke(app, ["fuse"])
        assert result.exit_code != 0

    def test_extract_bad_chunk_size(self):
        """``kreview extract --chunk-size garbage`` fails with non-zero exit."""
        result = runner.invoke(
            app,
            [
                "extract",
                "--cancer-samplesheet",
                "/nonexistent.csv",
                "--healthy-xs1-samplesheet",
                "/nonexistent.csv",
                "--healthy-xs2-samplesheet",
                "/nonexistent.csv",
                "--cbioportal-dir",
                "/nonexistent",
                "--krewlyzer-dir",
                "/nonexistent",
                "--chunk-size",
                "garbage",
            ],
        )
        assert result.exit_code != 0


# ── #98: report writes a machine-readable manifest (always) ──────────────────


class TestReportManifest:
    """#98: `kreview report` must write reports/report_manifest.json on success AND failure.

    On the iris v0.0.29 run, 17/26 dashboards rendered but the failing task published
    nothing — and nothing machine-readable recorded which dashboards were missing. The
    manifest is the loud, durable record the Nextflow terminal-attempt publish relies on.
    """

    def _fake_matrix(self, tmp_path, name):
        import pandas as pd

        p = tmp_path / f"{name}_matrix.parquet"
        pd.DataFrame({"f1": [1.0, 2.0]}).to_parquet(p, index=False)
        return p

    def test_manifest_on_partial_failure_and_exit_1(self, tmp_path, monkeypatch):
        """One failed render → exit 1 (fail loud) AND a manifest naming the failure."""
        import json
        import kreview.cli as cli_mod

        self._fake_matrix(tmp_path, "GoodEval")
        self._fake_matrix(tmp_path, "BadEval")

        def fake_render(matrix_path, feat_name, out_path, _python, **kwargs):
            if feat_name == "BadEval":
                return False, "Exit code 1. Full log: BadEval_render.log"
            return True, str(out_path / f"{feat_name}_dashboard.html")

        monkeypatch.setattr(cli_mod, "_render_quarto_report", fake_render)
        out_dir = tmp_path / "reports"
        result = runner.invoke(
            app, ["report", "--input-dir", str(tmp_path), "--out-dir", str(out_dir)]
        )
        assert result.exit_code == 1, "failures must still exit 1 (fail loud)"

        manifest = json.loads((out_dir / "report_manifest.json").read_text())
        assert manifest["total"] == 2
        assert manifest["succeeded_evaluators"] == ["GoodEval"]
        assert manifest["failed_evaluators"] == ["BadEval"]
        assert manifest["render_logs"] == {"BadEval": "BadEval_render.log"}

    def test_manifest_on_full_success_and_exit_0(self, tmp_path, monkeypatch):
        """All renders succeed → exit 0 and a manifest with no failures."""
        import json
        import kreview.cli as cli_mod

        self._fake_matrix(tmp_path, "OnlyEval")
        monkeypatch.setattr(
            cli_mod,
            "_render_quarto_report",
            lambda *a, **k: (True, "OnlyEval_dashboard.html"),
        )
        out_dir = tmp_path / "reports"
        result = runner.invoke(
            app, ["report", "--input-dir", str(tmp_path), "--out-dir", str(out_dir)]
        )
        assert result.exit_code == 0, result.output

        manifest = json.loads((out_dir / "report_manifest.json").read_text())
        assert manifest["failed"] == 0
        assert manifest["succeeded_evaluators"] == ["OnlyEval"]
        assert manifest["failed_evaluators"] == []
