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
        assert (
            "ERROR" in result.output
            or "error" in result.output
            or "Error" in result.output
        )

    def test_detect_no_file(self):
        """detect subcommand with nonexistent file shows error."""
        result = runner.invoke(cli, ["detect", "/nonexistent/file.json"])
        assert result.exit_code != 0

    def test_convert_nonexistent_file(self):
        """convert subcommand with nonexistent file shows error."""
        result = runner.invoke(cli, ["convert", "/nonexistent/file.json"])
        assert result.exit_code != 0


class TestSchemaCmdErrorPaths:
    """Tests for the `schema` subcommand error paths (silent-failure class)."""

    def test_schema_unsupported_format_exits_cleanly(self, tmp_path):
        """--format with an unsupported name errors instead of traceback."""
        f = tmp_path / "data.txt"
        f.write_text("hello")
        result = runner.invoke(cli, ["schema", str(f), "--format", "nope"])
        assert result.exit_code == 1
        assert "Unsupported format" in result.output
        assert "Traceback" not in result.output

    def test_schema_malformed_json_exits_cleanly(self, tmp_path):
        """Malformed input yields a clean error, not an unhandled traceback."""
        f = tmp_path / "broken.json"
        f.write_text("{not valid json!!!")
        result = runner.invoke(cli, ["schema", str(f)])
        assert result.exit_code == 1
        assert "Could not infer schema" in result.output
        assert "Traceback" not in result.output

    def test_schema_sample_message_is_honest(self, tmp_path):
        """Footer reports the sample cap, not '{sample}+ rows'."""
        import json as _json

        f = tmp_path / "rows.json"
        f.write_text(_json.dumps([{"a": 1}, {"a": 2}]))
        result = runner.invoke(cli, ["schema", str(f), "--sample", "100"])
        assert result.exit_code == 0
        assert "up to 100 rows" in result.output
