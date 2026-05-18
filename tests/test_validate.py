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
