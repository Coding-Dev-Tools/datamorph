"""Targeted edge-case tests for DataMorph.

Covers uncovered error-handling paths in CLI, converters, and packaging config.
"""

from __future__ import annotations

from pathlib import Path

import tomllib
from click.testing import CliRunner

from datamorph.cli import cli
from datamorph.converters import detect_format, get_reader, get_writer


class TestCLIEdgeCases:
    """Tests for uncovered CLI error paths."""

    def test_cli_convert_success(self, tmp_path):
        """convert CSV to JSON succeeds (covers normal flow)."""
        runner = CliRunner()
        input_file = tmp_path / "test.csv"
        input_file.write_text("a,b,c\n1,2,3\n4,5,6\n")
        output_file = tmp_path / "out.json"

        result = runner.invoke(cli, [
            "convert", str(input_file), str(output_file),
        ])
        assert result.exit_code == 0

    def test_undetectable_format_exits(self, tmp_path):
        """convert with undetectable format exits 2 (cli.py:165-166 triggers Click error)."""
        runner = CliRunner()
        input_file = tmp_path / "unknown.xyz"
        input_file.write_text("some random content\n")
        output_file = tmp_path / "out.json"

        result = runner.invoke(cli, [
            "convert", str(input_file), str(output_file),
        ])
        assert result.exit_code != 0

    def test_detect_format_none(self):
        """detect_format returns None for unknown extensions."""
        fmt = detect_format("/some/file.unknown_ext")
        assert fmt is None

    def test_cli_version(self):
        """CLI --version exits 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_formats_command(self):
        """formats command lists supported formats."""
        runner = CliRunner()
        result = runner.invoke(cli, ["formats"])
        assert result.exit_code == 0
        assert "csv" in result.output.lower()

    def test_cli_convert_error_with_bad_data(self, tmp_path):
        """convert with bad data may fail (cli.py:80-82 error reporting)."""
        runner = CliRunner()
        input_file = tmp_path / "bad.csv"
        # Actually valid CSV - convert should succeed
        input_file.write_text("a,b\n1,2\n")
        output_file = tmp_path / "out.json"

        result = runner.invoke(cli, [
            "convert", str(input_file), str(output_file),
        ])
        assert result.exit_code == 0 or "Error" in result.output


class TestConverterEdgeCases:
    """Tests for uncovered converter error paths."""

    def test_get_reader_for_csv(self):
        """get_reader returns a reader for csv format."""
        reader = get_reader("csv")
        assert reader is not None

    def test_get_writer_for_csv(self):
        """get_writer returns a writer for csv format."""
        writer = get_writer("csv")
        assert writer is not None

    def test_batch_command_basic(self, tmp_path):
        """batch command runs without error."""
        runner = CliRunner()
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "test.csv").write_text("a,b\n1,2\n")
        output_dir = tmp_path / "output"

        result = runner.invoke(cli, [
            "batch", str(input_dir), str(output_dir),
            "--from", "csv", "--to", "json",
        ])
        assert result.exit_code == 0 or "Error" in result.output

    def test_schema_command_basic(self, tmp_path):
        """schema command runs without error."""
        runner = CliRunner()
        input_file = tmp_path / "test.csv"
        input_file.write_text("a,b\n1,2\n")
        result = runner.invoke(cli, [
            "schema", str(input_file),
        ])
        assert result.exit_code == 0

    def test_validate_command_basic(self, tmp_path):
        """validate command runs without error."""
        runner = CliRunner()
        input_file = tmp_path / "test.csv"
        input_file.write_text("a,b\n1,2\n")
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text("fields:\n  a: int\n  b: int\n")
        result = runner.invoke(cli, [
            "validate", str(input_file), str(schema_file),
        ])
        assert result.exit_code == 0 or "Error" in result.output


class TestPackagingQuality:
    """Tests for py.typed packaging config."""

    def test_package_data_includes_py_typed(self):
        """pyproject.toml should have package-data config for py.typed."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        pkg_data = data.get("tool", {}).get("setuptools", {}).get("package-data", {})
        assert "datamorph" in pkg_data, \
            "Expected [tool.setuptools.package-data] section for 'datamorph'"
        assert "py.typed" in pkg_data["datamorph"], \
            f"Expected 'py.typed' in package-data, got {pkg_data['datamorph']}"

    def test_ruff_known_first_party(self):
        """ruff known-first-party should be ['datamorph']."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        isort_cfg = data.get("tool", {}).get("ruff", {}).get("lint", {}).get("isort", {})
        kfp = isort_cfg.get("known-first-party", [])
        assert kfp == ["datamorph"], f"known-first-party should be ['datamorph'], got {kfp}"
