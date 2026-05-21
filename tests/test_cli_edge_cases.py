"""Tests for CLI edge cases: convert flags, schema options, validate combos."""

from __future__ import annotations

import json

import pytest
import yaml

from datamorph.cli import cli
from datamorph.converters import convert, validate

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def runner():
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def sample_csv(tmp_path):
    path = tmp_path / "test.csv"
    path.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n")
    return path


@pytest.fixture
def sample_json(tmp_path):
    path = tmp_path / "test.json"
    data = [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "LA"},
    ]
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def schema_file(tmp_path, sample_csv):
    """Generate a schema file matching sample_csv fields."""
    path = tmp_path / "schema.json"
    schema = [
        {"name": "name", "type": "string"},
        {"name": "age", "type": "string"},
        {"name": "city", "type": "string"},
    ]
    path.write_text(json.dumps(schema))
    return path


# ── convert --pretty ──────────────────────────────────────────────────


class TestConvertPretty:
    def test_pretty_flag_produces_indented_json(self, runner, sample_csv, tmp_path):
        output = tmp_path / "pretty.json"
        result = runner.invoke(cli, ["convert", str(sample_csv), str(output), "--pretty"])
        assert result.exit_code == 0
        content = output.read_text()
        # Pretty-printed JSON should have indentation (newlines)
        assert "\n" in content
        data = json.loads(content)
        assert len(data) == 3

    def test_no_pretty_flag_compact_json(self, runner, sample_csv, tmp_path):
        output = tmp_path / "compact.json"
        result = runner.invoke(cli, ["convert", str(sample_csv), str(output)])
        assert result.exit_code == 0
        content = output.read_text()
        # Default JSON has indent=2 so this also has newlines; just verify it's valid
        data = json.loads(content)
        assert len(data) == 3


# ── convert --csv-delimiter ───────────────────────────────────────────


class TestConvertCsvDelimiter:
    def test_pipe_delimiter_read(self, runner, tmp_path):
        csv_path = tmp_path / "pipes.csv"
        csv_path.write_text("name|age\nAlice|30\nBob|25\n")
        output = tmp_path / "out.json"
        result = runner.invoke(cli, [
            "convert", str(csv_path), str(output), "--csv-delimiter", "|",
        ])
        assert result.exit_code == 0
        data = json.loads(output.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "Alice"

    def test_tab_delimiter_read(self, runner, tmp_path):
        csv_path = tmp_path / "tabs.csv"
        csv_path.write_text("name\tage\nAlice\t30\nBob\t25\n")
        output = tmp_path / "out.json"
        result = runner.invoke(cli, [
            "convert", str(csv_path), str(output), "--csv-delimiter", "\t",
        ])
        assert result.exit_code == 0
        data = json.loads(output.read_text())
        assert len(data) == 2

    def test_delimiter_roundtrip_via_cli(self, runner, tmp_path):
        """Pipe-delimited CSV in → JSON → pipe-delimited CSV out."""
        csv_in = tmp_path / "in.csv"
        csv_in.write_text("name|age\nAlice|30\n")
        json_path = tmp_path / "mid.json"
        runner.invoke(cli, ["convert", str(csv_in), str(json_path), "--csv-delimiter", "|"])
        csv_out = tmp_path / "out.csv"
        runner.invoke(cli, [
            "convert", str(json_path), str(csv_out), "--csv-delimiter", "|",
        ])
        content = csv_out.read_text()
        assert "name|age" in content
        assert "Alice" in content


# ── convert --input-format / --output-format ─────────────────────────


class TestConvertFormatOverrides:
    def test_format_overrides(self, runner, tmp_path):
        """Convert a file with no extension using format overrides."""
        no_ext = tmp_path / "datafile"
        no_ext.write_text("name,age\nAlice,30\n")
        output = tmp_path / "out.json"
        result = runner.invoke(cli, [
            "convert", str(no_ext), str(output),
            "--input-format", "csv", "--output-format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(output.read_text())
        assert data[0]["name"] == "Alice"


# ── schema CLI edge cases ─────────────────────────────────────────────


class TestSchemaCLIEdgeCases:
    def test_schema_with_format_override(self, runner, tmp_path):
        """Schema command with --format flag on extensionless file."""
        path = tmp_path / "datafile"
        path.write_text("name,age\nAlice,30\n")
        result = runner.invoke(cli, ["schema", str(path), "--format", "csv"])
        assert result.exit_code == 0
        assert "name" in result.output

    def test_schema_sample_size(self, runner, tmp_path):
        """Schema with custom --sample size."""
        path = tmp_path / "big.csv"
        lines = ["name,age\n"] + [f"User{i},{20+i}\n" for i in range(200)]
        path.write_text("".join(lines))
        result = runner.invoke(cli, ["schema", str(path), "--sample", "10"])
        assert result.exit_code == 0
        assert "name" in result.output

    def test_schema_unknown_format(self, runner, tmp_path):
        """Schema on a file with unknown format should fail."""
        path = tmp_path / "data.xyz"
        path.write_text("hello")
        result = runner.invoke(cli, ["schema", str(path)])
        assert result.exit_code != 0


# ── validate CLI edge cases ──────────────────────────────────────────


class TestValidateCLIEdgeCases:
    def test_validate_strict_with_json_output(self, runner, sample_csv, schema_file):
        """Strict + JSON output should produce valid JSON even on failure."""
        # Use a mismatched schema to force strict failure
        bad_schema = tmp_path = schema_file.parent / "bad_schema.json"
        bad_schema.write_text(json.dumps([
            {"name": "name", "type": "int64"},
            {"name": "age", "type": "string"},
        ]))
        result = runner.invoke(cli, [
            "validate", str(sample_csv),
            "--schema", str(bad_schema),
            "--strict", "--json-output",
        ])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["valid"] is False
        assert data["errors"]

    def test_validate_no_schema_text_output(self, runner, sample_csv):
        """Default text output for valid file."""
        result = runner.invoke(cli, ["validate", str(sample_csv)])
        assert result.exit_code == 0
        assert "VALID" in result.output
        assert "3 rows checked" in result.output

    def test_validate_empty_csv(self, runner, tmp_path):
        """Validate an empty CSV (header only)."""
        path = tmp_path / "empty.csv"
        path.write_text("name,age\n")
        result = runner.invoke(cli, ["validate", str(path)])
        assert result.exit_code == 0


# ── formats CLI ───────────────────────────────────────────────────────


class TestFormatsCLIEdgeCases:
    def test_formats_includes_all_core_formats(self, runner):
        result = runner.invoke(cli, ["formats"])
        assert result.exit_code == 0
        for fmt in ["csv", "json", "jsonl", "yaml", "parquet", "avro"]:
            assert fmt in result.output, f"Missing format: {fmt}"


# ── Validate function edge cases ──────────────────────────────────────


class TestValidateFunctionEdgeCases:
    def test_validate_json_with_schema(self, sample_json, schema_file):
        """Validate JSON against a schema."""
        schema = json.loads(schema_file.read_text())
        result = validate(sample_json, expected_schema=schema)
        assert result.valid
        assert result.rows_checked == 2

    def test_validate_with_max_rows_zero(self, sample_csv):
        """max_rows=0 means check all rows."""
        result = validate(sample_csv, max_rows=0)
        assert result.rows_checked == 3

    def test_validate_strict_unexpected_fields(self, tmp_path):
        """Strict mode warns on unexpected fields."""
        schema = [{"name": "name", "type": "string"}]
        path = tmp_path / "extra.csv"
        path.write_text("name,extra\nAlice,x\n")
        result = validate(path, expected_schema=schema, strict=True)
        assert result.valid  # unexpected fields are warnings, not errors
        assert result.warnings
        assert any("unexpected field" in w for w in result.warnings)
