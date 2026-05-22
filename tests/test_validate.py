"""Tests for DataMorph validate command and function."""

from __future__ import annotations

import json

import pytest

from datamorph.cli import cli
from datamorph.converters import ValidationResult, validate

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
    """Generate a schema file from the sample CSV."""
    path = tmp_path / "schema.json"
    schema = [
        {"name": "name", "type": "string"},
        {"name": "age", "type": "string"},  # CSV reads everything as strings
        {"name": "city", "type": "string"},
    ]
    path.write_text(json.dumps(schema))
    return path


# ── validate() function tests ─────────────────────────────────────────


class TestValidateFunction:
    def test_valid_csv_no_schema(self, sample_csv):
        """Validate with no schema — just structural checks."""
        result = validate(sample_csv)
        assert result.valid
        assert result.rows_checked == 3
        assert not result.errors

    def test_valid_csv_with_matching_schema(self, sample_csv, schema_file):
        """Validate CSV against matching schema."""
        schema = json.loads(schema_file.read_text())
        result = validate(sample_csv, expected_schema=schema)
        assert result.valid
        assert result.rows_checked == 3

    def test_valid_json_no_schema(self, sample_json):
        """Validate JSON with no schema — structural check."""
        result = validate(sample_json)
        assert result.valid
        assert result.rows_checked == 2

    def test_unsupported_format(self, tmp_path):
        path = tmp_path / "data.xyz"
        path.write_text("hello")
        result = validate(path)
        assert not result.valid
        assert result.errors

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("name,age\n")
        result = validate(path)
        assert result.valid
        # Should warn about no data rows

    def test_max_rows_limit(self, sample_csv):
        result = validate(sample_csv, max_rows=2)
        assert result.rows_checked == 2

    def test_truly_empty_file(self, tmp_path):
        """File with absolutely no content should warn about empty schema."""
        path = tmp_path / "empty.csv"
        path.write_text("")  # Empty file, not even headers
        result = validate(path)
        assert result.warnings
        assert any("no detectable schema" in w.lower() for w in result.warnings)

    def test_empty_file_with_schema(self, tmp_path):
        """File with headers but no data rows, validated against expected schema."""
        schema = [
            {"name": "name", "type": "string"},
            {"name": "age", "type": "string"},
        ]
        path = tmp_path / "data.csv"
        path.write_text("name,age\n")  # Header only
        result = validate(path, expected_schema=schema)
        assert result.valid
        assert result.rows_checked == 0
        assert any("no data rows" in w.lower() for w in result.warnings)

    def test_validate_reader_error(self, tmp_path):
        """Unsupported format should raise reader error via validate()."""
        path = tmp_path / "data.txt"
        path.write_text("some content")
        # Use a format name that has no registered reader
        result = validate(path, input_format="exe")
        assert not result.valid
        assert result.errors

    def test_strict_unexpected_field_warning(self, tmp_path):
        """Strict mode should warn about unexpected fields not in expected schema."""
        schema = [
            {"name": "name", "type": "string"},
        ]
        path = tmp_path / "data.csv"
        path.write_text("name,extra_field\nAlice,unexpected\n")
        result = validate(path, expected_schema=schema, strict=True)
        # Should still be valid (warnings only for unexpected fields, not errors)
        # The unexpected field is a warning, not an error
        assert result.warnings
        assert any("unexpected field" in w for w in result.warnings)

    def test_non_strict_unexpected_field_ignored(self, tmp_path):
        """Non-strict mode should not warn about unexpected fields."""
        schema = [
            {"name": "name", "type": "string"},
        ]
        path = tmp_path / "data.csv"
        path.write_text("name,extra_field\nAlice,unexpected\n")
        result = validate(path, expected_schema=schema, strict=False)
        # Should be valid with no warnings about unexpected fields
        assert result.valid
        # May have other warnings, but none about unexpected fields
        unexpected_warnings = [w for w in result.warnings if "unexpected field" in w]
        assert len(unexpected_warnings) == 0

    def test_strict_mode_missing_field(self, tmp_path):
        """Strict mode should fail when expected field is missing."""
        schema = [
            {"name": "name", "type": "string"},
            {"name": "missing_field", "type": "string"},
        ]
        path = tmp_path / "data.csv"
        path.write_text("name\nAlice\nBob\n")
        result = validate(path, expected_schema=schema, strict=True)
        assert not result.valid
        assert any("missing required field" in e for e in result.errors)

    def test_non_strict_type_mismatch(self, sample_csv):
        """Non-strict mode should warn on type mismatches, not fail."""
        schema = [
            {"name": "name", "type": "int64"},
            {"name": "age", "type": "string"},
            {"name": "city", "type": "string"},
        ]
        result = validate(sample_csv, expected_schema=schema, strict=False)
        # Should have warnings but still be valid
        assert result.warnings

    def test_strict_type_mismatch(self, sample_csv):
        """Strict mode should fail on type mismatches."""
        schema = [
            {"name": "name", "type": "int64"},
            {"name": "age", "type": "string"},
            {"name": "city", "type": "string"},
        ]
        result = validate(sample_csv, expected_schema=schema, strict=True)
        assert not result.valid

    def test_validation_result_dataclass(self):
        """Test ValidationResult defaults."""
        r = ValidationResult()
        assert r.valid is True
        assert r.rows_checked == 0
        assert r.errors == []
        assert r.warnings == []


# ── validate CLI command tests ────────────────────────────────────────


class TestValidateCLI:
    def test_validate_no_schema(self, runner, sample_csv):
        result = runner.invoke(cli, ["validate", str(sample_csv)])
        assert result.exit_code == 0
        assert "VALID" in result.output

    def test_validate_with_schema(self, runner, sample_csv, schema_file):
        result = runner.invoke(cli, [
            "validate", str(sample_csv),
            "--schema", str(schema_file),
        ])
        assert result.exit_code == 0
        assert "VALID" in result.output

    def test_validate_strict(self, runner, sample_csv, schema_file):
        result = runner.invoke(cli, [
            "validate", str(sample_csv),
            "--schema", str(schema_file),
            "--strict",
        ])
        assert result.exit_code == 0

    def test_validate_json_output(self, runner, sample_csv):
        result = runner.invoke(cli, [
            "validate", str(sample_csv),
            "--json-output",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True
        assert data["rows_checked"] == 3

    def test_validate_max_rows(self, runner, sample_csv):
        result = runner.invoke(cli, [
            "validate", str(sample_csv),
            "--max-rows", "2",
            "--json-output",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["rows_checked"] == 2

    def test_validate_nonexistent_file(self, runner, tmp_path):
        result = runner.invoke(cli, ["validate", str(tmp_path / "nope.csv")])
        assert result.exit_code != 0

    def test_validate_help(self, runner):
        result = runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "schema" in result.output.lower()

    def test_validate_with_format_override(self, runner, tmp_path):
        """Validate a file with explicit --format flag (no extension-based detection)."""
        path = tmp_path / "data.unknown"
        path.write_text("name,age\nAlice,30\nBob,25\n")
        result = runner.invoke(cli, [
            "validate", str(path),
            "--format", "csv",
        ])
        assert result.exit_code == 0
        assert "VALID" in result.output
        assert "2 rows checked" in result.output

    def test_validate_with_format_and_schema(self, runner, tmp_path):
        """Validate with both --format and --schema overrides."""
        data_file = tmp_path / "data.unknown"
        data_file.write_text("name,age\nAlice,30\nBob,25\n")
        schema_file = tmp_path / "schema.json"
        import json
        schema_file.write_text(json.dumps([
            {"name": "name", "type": "string"},
            {"name": "age", "type": "string"},
        ]))
        result = runner.invoke(cli, [
            "validate", str(data_file),
            "--format", "csv",
            "--schema", str(schema_file),
        ])
        assert result.exit_code == 0
        assert "VALID" in result.output

    def test_validate_invalid_non_json_shows_error_text(self, runner, tmp_path):
        """Invalid validation in non-JSON mode shows 'INVALID' and error details."""
        data_file = tmp_path / "data.csv"
        data_file.write_text("name,age\nAlice,30\n")
        schema_file = tmp_path / "schema.json"
        import json
        schema_file.write_text(json.dumps([
            {"name": "name", "type": "string"},
            {"name": "missing_field", "type": "string"},
        ]))
        result = runner.invoke(cli, [
            "validate", str(data_file),
            "--schema", str(schema_file),
            "--strict",
        ])
        assert result.exit_code != 0
        assert "INVALID" in result.output
        assert "missing_field" in result.output or "required" in result.output

    def test_validate_non_json_with_warnings(self, runner, tmp_path):
        """Non-JSON output shows warnings when present."""
        schema_file = tmp_path / "schema.json"
        import json
        schema_file.write_text(json.dumps([
            {"name": "name", "type": "string"},
        ]))
        data_file = tmp_path / "data.csv"
        data_file.write_text("name,extra\nAlice,unexpected\n")
        result = runner.invoke(cli, [
            "validate", str(data_file),
            "--schema", str(schema_file),
            "--strict",
        ])
        assert result.exit_code == 0
        assert "VALID" in result.output
        assert "unexpected" in result.output or "Warning" in result.output.lower() or "extra" in result.output
