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
            "run",
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


# ── Standalone commands ──


class TestStandaloneCommands:
    """Smoke test each standalone command's --help."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "run",
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

    @pytest.mark.parametrize("sub", ["cpu", "gpu", "multimodal"])
    def test_eval_sub_help(self, sub):
        """``kreview eval <sub> --help`` returns exit code 0."""
        result = runner.invoke(app, ["eval", sub, "--help"])
        assert result.exit_code == 0, f"eval {sub}: {result.output}"


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
