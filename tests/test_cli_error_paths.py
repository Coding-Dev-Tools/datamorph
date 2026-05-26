"""Tests for CLI error paths and __main__.py entry point."""

from __future__ import annotations

from click.testing import CliRunner

from datamorph.cli import cli

runner = CliRunner()


class TestCliErrorPaths:
    """Tests for uncovered CLI error paths (cli.py:134-165)."""

    def test_batch_with_nonexistent_file(self):
        """batch subcommand with missing file shows errors."""
        result = runner.invoke(cli, ["batch", "/nonexistent/file.json"])
        assert result.exit_code != 0
        assert "ERROR" in result.output or "error" in result.output or "Error" in result.output

    def test_detect_no_file(self):
        """detect subcommand with nonexistent file shows error."""
        result = runner.invoke(cli, ["detect", "/nonexistent/file.json"])
        assert result.exit_code != 0

    def test_convert_nonexistent_file(self):
        """convert subcommand with nonexistent file shows error."""
        result = runner.invoke(cli, ["convert", "/nonexistent/file.json"])
        assert result.exit_code != 0
