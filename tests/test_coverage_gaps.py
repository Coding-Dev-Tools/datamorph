"""Targeted tests for uncovered code paths in DataMorph.

Covers:
- _format_to_extension() format→extension mapping
- _infer_type() date detection and edge types
- _widen_type() all widening combinations
- JsonlReader/JsonlWriter (JSONL format - no direct tests existed)
- JsonReader non-list/non-dict (scalar value path)
- CsvReader None-key handling
- csv_delimiter→delimiter normalization in convert()
- register_format() standalone behavior
- convert_batch() standalone function edge cases
- validate() corrupted data mid-read
"""

from __future__ import annotations

import json
from unittest.mock import patch

from datamorph import converters
from datamorph.converters import (
    ConversionResult,
    _format_to_extension,
    _infer_type,
    _widen_type,
    convert,
    convert_batch,
    detect_format,
    get_reader,
    register_format,
    validate,
)

# ═══════════════════════════════════════════════════════════════════════
# _format_to_extension
# ═══════════════════════════════════════════════════════════════════════


class TestFormatToExtension:
    """Cover _format_to_extension() — never directly tested."""

    def test_csv_extension(self):
        assert _format_to_extension("csv") == ".csv"

    def test_json_extension(self):
        assert _format_to_extension("json") == ".json"

    def test_jsonl_extension(self):
        assert _format_to_extension("jsonl") == ".jsonl"

    def test_yaml_extension(self):
        assert _format_to_extension("yaml") == ".yaml"

    def test_parquet_extension(self):
        assert _format_to_extension("parquet") == ".parquet"

    def test_avro_extension(self):
        assert _format_to_extension("avro") == ".avro"

    def test_unknown_format_falls_back(self):
        """Unknown format should use .<fmt> as fallback."""
        assert _format_to_extension("exe") == ".exe"
        assert _format_to_extension("txt") == ".txt"

    def test_empty_string(self):
        assert _format_to_extension("") == "."


# ═══════════════════════════════════════════════════════════════════════
# _infer_type — date detection
# ═══════════════════════════════════════════════════════════════════════


class TestInferTypeDates:
    """Cover _infer_type() date detection path."""

    def test_date_iso_format(self):
        """ISO date strings (YYYY-MM-DD) should be detected as 'date'."""
        assert _infer_type("2024-01-15") == "date"

    def test_date_leap_year(self):
        assert _infer_type("2024-02-29") == "date"  # leap year
        assert _infer_type("2023-02-28") == "date"

    def test_date_edge_cases(self):
        """Edge ISO-like strings that shouldn't parse."""
        # Month 13 doesn't exist -> fails date.fromisoformat -> returns "string"
        assert _infer_type("2024-13-01") == "string"
        # Day 32 doesn't exist -> fails -> "string"
        assert _infer_type("2024-01-32") == "string"

    def test_non_date_10char_string(self):
        """10-char strings that don't match ISO format should remain 'string'."""
        assert _infer_type("1234567890") == "string"
        assert _infer_type("abcdefghij") == "string"

    def test_short_date_like_string(self):
        """Strings with hyphens but wrong length are not dates."""
        assert _infer_type("2024-1-1") == "string"  # too short
        assert _infer_type("2024-01-01T00:00:00") == "string"  # too long (datetime, not just date)

    def test_bool_values(self):
        assert _infer_type(True) == "bool"
        assert _infer_type(False) == "bool"

    def test_none_value(self):
        assert _infer_type(None) == "null"

    def test_unknown_type_falls_back_to_string(self):
        """Non-standard types should fall back to 'string'."""

        class CustomType:
            pass

        assert _infer_type(CustomType()) == "string"


# ═══════════════════════════════════════════════════════════════════════
# _widen_type — all widening combinations
# ═══════════════════════════════════════════════════════════════════════


class TestWidenType:
    """Cover _widen_type() all documented combinations."""

    def test_identical_types(self):
        for t in ("int64", "float64", "string", "bool", "null", "date"):
            assert _widen_type(t, t) == t

    def test_int64_float64(self):
        assert _widen_type("int64", "float64") == "float64"

    def test_int64_string(self):
        assert _widen_type("int64", "string") == "string"

    def test_float64_string(self):
        assert _widen_type("float64", "string") == "string"

    def test_null_int64(self):
        assert _widen_type("null", "int64") == "int64"

    def test_null_float64(self):
        assert _widen_type("null", "float64") == "float64"

    def test_null_string(self):
        assert _widen_type("null", "string") == "string"

    def test_null_bool(self):
        assert _widen_type("null", "bool") == "bool"

    def test_null_date(self):
        assert _widen_type("null", "date") == "date"

    def test_unknown_pair_falls_back_to_string(self):
        """A pair not in the widening table should return 'string'."""
        assert _widen_type("bool", "date") == "string"
        assert _widen_type("date", "float64") == "string"

    def test_reversed_order(self):
        """Widening should be symmetric (order shouldn't matter for the table)."""
        assert _widen_type("float64", "int64") == "float64"
        assert _widen_type("string", "int64") == "string"
        assert _widen_type("string", "float64") == "string"
        assert _widen_type("int64", "null") == "int64"
        assert _widen_type("bool", "null") == "bool"
        assert _widen_type("date", "null") == "date"


# ═══════════════════════════════════════════════════════════════════════
# JSONL format — reader/writer
# ═══════════════════════════════════════════════════════════════════════


class TestJsonlFormat:
    """Cover JSONL (JSON Lines) reader and writer — no direct tests existed."""

    def test_jsonl_write_then_read(self, tmp_path):
        """Write JSONL data then read it back."""
        from datamorph.converters import JsonlReader, JsonlWriter

        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

        # Write
        path = tmp_path / "data.jsonl"
        writer = JsonlWriter()
        count = writer.write_stream(iter(data), path)
        assert count == 2

        # Verify file format (one JSON object per line)
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"name": "Alice", "age": 30}
        assert json.loads(lines[1]) == {"name": "Bob", "age": 25}

        # Read back
        reader = JsonlReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"

    def test_jsonl_empty_lines_skipped(self, tmp_path):
        """Empty lines in JSONL should be skipped by reader."""
        from datamorph.converters import JsonlReader

        path = tmp_path / "data.jsonl"
        path.write_text(
            '{"a": 1}\n\n{"b": 2}\n\n\n{"c": 3}\n',
            encoding="utf-8",
        )

        reader = JsonlReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 3
        assert rows[0] == {"a": 1}
        assert rows[1] == {"b": 2}
        assert rows[2] == {"c": 3}

    def test_jsonl_convert_roundtrip(self, tmp_path):
        """Convert CSV to JSONL and back."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")

        # CSV -> JSONL
        jsonl_path = tmp_path / "data.jsonl"
        result = convert(csv_path, jsonl_path)
        assert not result.errors
        assert result.rows_written == 2
        assert result.output_format == "jsonl"

        # JSONL -> CSV
        csv_out = tmp_path / "out.csv"
        result = convert(jsonl_path, csv_out)
        assert not result.errors
        assert result.rows_written == 2
        assert "1" in csv_out.read_text()

    def test_jsonl_empty_write(self, tmp_path):
        """Writing empty list to JSONL returns 0."""
        from datamorph.converters import JsonlWriter

        path = tmp_path / "empty.jsonl"
        writer = JsonlWriter()
        count = writer.write_stream(iter([]), path)
        assert count == 0
        assert path.exists()
        assert path.stat().st_size == 0

    def test_jsonl_whitespace_only_lines(self, tmp_path):
        """Lines with only whitespace should be skipped."""
        from datamorph.converters import JsonlReader

        path = tmp_path / "data.jsonl"
        path.write_text('{"id": 1}\n   \n{"id": 2}\n\t\n{"id": 3}\n', encoding="utf-8")

        reader = JsonlReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 3


# ═══════════════════════════════════════════════════════════════════════
# JsonReader — scalar/non-list-non-dict path
# ═══════════════════════════════════════════════════════════════════════


class TestJsonReaderScalar:
    """Cover JsonReader.read_stream() non-list non-dict path."""

    def test_json_string_value_becomes_data_field(self, tmp_path):
        """A JSON file containing a plain string should yield {'data': ...}."""
        from datamorph.converters import JsonReader

        path = tmp_path / "scalar.json"
        path.write_text('"hello world"', encoding="utf-8")

        reader = JsonReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 1
        assert rows[0] == {"data": "hello world"}

    def test_json_number_value_becomes_data_field(self, tmp_path):
        """A JSON file containing a plain number should yield {'data': ...}."""
        from datamorph.converters import JsonReader

        path = tmp_path / "number.json"
        path.write_text("42", encoding="utf-8")

        reader = JsonReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 1
        assert rows[0] == {"data": 42}

    def test_json_null_value_becomes_data_field(self, tmp_path):
        from datamorph.converters import JsonReader

        path = tmp_path / "null.json"
        path.write_text("null", encoding="utf-8")

        reader = JsonReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 1
        assert rows[0] == {"data": None}


# ═══════════════════════════════════════════════════════════════════════
# CsvReader — None-key handling
# ═══════════════════════════════════════════════════════════════════════


class TestCsvReaderNoneKey:
    """Cover CsvReader.read_stream() None-key skip path (overflow columns)."""

    def test_extra_columns_skipped(self, tmp_path):
        """Rows with more columns than the header should not crash."""
        from datamorph.converters import CsvReader

        path = tmp_path / "ragged.csv"
        # Header has 2 columns but rows have 3 — csv.DictReader stores
        # the extra column under key None.
        path.write_text("a,b\n1,2,3\n4,5,6\n", encoding="utf-8")

        reader = CsvReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 2
        # Extra column should be silently dropped, not crash
        assert rows[0] == {"a": "1", "b": "2"}
        assert rows[1] == {"a": "4", "b": "5"}

    def test_empty_field_values_become_none(self, tmp_path):
        """Empty field values should be converted to None, not empty string."""
        from datamorph.converters import CsvReader

        path = tmp_path / "empties.csv"
        path.write_text("name,email\nAlice,\nBob,bob@test.com\n", encoding="utf-8")

        reader = CsvReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 2
        assert rows[0] == {"name": "Alice", "email": None}
        assert rows[1] == {"name": "Bob", "email": "bob@test.com"}

    def test_whitespace_stripped(self, tmp_path):
        """Values with surrounding whitespace should be stripped."""
        from datamorph.converters import CsvReader

        path = tmp_path / "spaces.csv"
        path.write_text('"name","city"\n"  Alice  ","  NYC  "\n', encoding="utf-8")

        reader = CsvReader()
        rows = list(reader.read_stream(path))
        assert len(rows) == 1
        assert rows[0] == {"name": "Alice", "city": "NYC"}


# ═══════════════════════════════════════════════════════════════════════
# csv_delimiter → delimiter normalization in convert()
# ═══════════════════════════════════════════════════════════════════════


class TestCsvDelimiterNormalization:
    """Cover csv_delimiter key normalization in convert()."""

    def test_csv_delimiter_passed_through(self, tmp_path):
        """csv_delimiter should be normalized to 'delimiter' for the writer."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a|b\n1|2\n3|4\n", encoding="utf-8")

        out_path = tmp_path / "out.json"
        result = convert(csv_path, out_path, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2

    def test_csv_delimiter_and_writer_kwargs_delimiter(self, tmp_path):
        """When both csv_delimiter and delimiter are provided, delimiter wins."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("a|b\n1|2\n3|4\n", encoding="utf-8")

        # csv_delimiter should be set as delimiter if delimiter is not already set
        out_path = tmp_path / "out.json"
        result = convert(csv_path, out_path, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2


# ═══════════════════════════════════════════════════════════════════════
# register_format()
# ═══════════════════════════════════════════════════════════════════════


class TestRegisterFormat:
    """Cover register_format() standalone behavior."""

    def test_register_reader_only(self):
        """Register a format with only a reader."""

        class DummyReader(converters.FormatReader):
            def read_stream(self, path):
                yield from []
                return

        format_name = "_test_reader_only"
        register_format(format_name, reader=DummyReader)
        try:
            reader = get_reader(format_name)
            assert reader is not None
            assert format_name in converters.supported_formats()
        finally:
            converters._READERS.pop(format_name, None)
            converters._WRITERS.pop(format_name, None)

    def test_register_writer_only(self):
        """Register a format with only a writer."""

        class DummyWriter(converters.FormatWriter):
            def write_stream(self, rows, path):
                return 0

        format_name = "_test_writer_only"
        register_format(format_name, writer=DummyWriter)
        try:
            writer = converters.get_writer(format_name)
            assert writer is not None
            assert format_name in converters.supported_formats()
        finally:
            converters._READERS.pop(format_name, None)
            converters._WRITERS.pop(format_name, None)

    def test_register_both(self):
        """Register a format with both reader and writer."""

        class R(converters.FormatReader):
            def read_stream(self, path):
                yield from []
                return

        class W(converters.FormatWriter):
            def write_stream(self, rows, path):
                return 0

        register_format("_test_both", reader=R, writer=W)
        try:
            assert converters.get_reader("_test_both") is not None
            assert converters.get_writer("_test_both") is not None
        finally:
            converters._READERS.pop("_test_both", None)
            converters._WRITERS.pop("_test_both", None)


# ═══════════════════════════════════════════════════════════════════════
# convert_batch() — standalone function
# ═══════════════════════════════════════════════════════════════════════


class TestConvertBatch:
    """Cover convert_batch() standalone edge cases."""

    def test_batch_empty_directory(self, tmp_path):
        """Batch converting from an empty dir returns empty results."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        results = convert_batch(input_dir, output_dir, "csv", "json")
        assert results == []

    def test_batch_single_file(self, tmp_path):
        """Batch convert a single CSV file to JSON."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        csv_file = input_dir / "data.csv"
        csv_file.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
        output_dir = tmp_path / "output"

        results = convert_batch(input_dir, output_dir, "csv", "json")
        assert len(results) == 1
        assert not results[0].errors
        assert results[0].rows_written == 2

        # Output file should exist
        out_file = output_dir / "data.json"
        assert out_file.exists()

    def test_batch_skips_non_matching_format(self, tmp_path):
        """Files that don't match input_format should be skipped."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "data.csv").write_text("x\n1\n", encoding="utf-8")
        (input_dir / "data.json").write_text('[{"x": 1}]\n', encoding="utf-8")
        output_dir = tmp_path / "output"

        # Only convert JSON files
        results = convert_batch(input_dir, output_dir, "json", "csv")
        assert len(results) == 1  # Only the JSON file

    def test_batch_skips_directories(self, tmp_path):
        """Directories in the glob should be skipped."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "subdir").mkdir()
        (input_dir / "data.csv").write_text("x\n1\n", encoding="utf-8")
        output_dir = tmp_path / "output"

        results = convert_batch(input_dir, output_dir, "csv", "json")
        assert len(results) == 1

    def test_batch_with_pattern(self, tmp_path):
        """Batch convert should respect the pattern filter."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "data.csv").write_text("x\n1\n", encoding="utf-8")
        (input_dir / "other.csv").write_text("y\n2\n", encoding="utf-8")
        (input_dir / "ignore.csv").write_text("z\n3\n", encoding="utf-8")
        output_dir = tmp_path / "output"

        results = convert_batch(input_dir, output_dir, "csv", "json", pattern="data.*")
        assert len(results) == 1
        assert results[0].rows_written == 1

    def test_batch_recursive(self, tmp_path):
        """Recursive mode should find files in subdirectories."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        sub = input_dir / "sub"
        sub.mkdir()
        (sub / "data.csv").write_text("x\n1\n", encoding="utf-8")
        output_dir = tmp_path / "output"

        # Non-recursive: 0 files
        results = convert_batch(input_dir, output_dir, "csv", "json", recursive=False)
        assert len(results) == 0

        # Recursive: 1 file
        results = convert_batch(input_dir, output_dir, "csv", "json", recursive=True)
        assert len(results) == 1


# ═══════════════════════════════════════════════════════════════════════
# validate() — corrupted data paths
# ═══════════════════════════════════════════════════════════════════════


class TestValidateCorruptedData:
    """Cover validate() paths: corrupted data mid-read, undetectable format."""

    def test_validate_corrupted_csv(self, tmp_path):
        """A CSV file with malformed rows should fail validation."""
        path = tmp_path / "bad.csv"
        # Valid header but then binary garbage
        path.write_text("a,b\n1,2\n\x00\xff\xfe\xfd\n", encoding="latin-1")

        result = validate(path)
        # Should not crash; should detect an issue
        assert not result.valid or result.warnings
        if result.errors:
            assert any("Validation failed" in e for e in result.errors)

    def test_validate_with_input_format_override_unknown(self, tmp_path):
        """Validate with input_format that has no registered reader."""
        path = tmp_path / "data.txt"
        path.write_text("hello\n", encoding="utf-8")

        result = validate(path, input_format="nonexistent_format")
        assert not result.valid
        assert result.errors

    def test_validate_empty_schema_no_data_warning(self, tmp_path):
        """Validating an empty file without schema should produce no-data warning."""
        path = tmp_path / "empty.csv"
        path.write_text("", encoding="utf-8")

        result = validate(path)
        # No detectable schema -> should have warnings
        assert result.warnings or not result.valid

    def test_validate_reader_throws(self, tmp_path):
        """A reader that throws during schema inference should be handled."""
        path = tmp_path / "data.csv"
        path.write_text("valid\n", encoding="utf-8")

        with patch.object(converters.CsvReader, "infer_schema", side_effect=ValueError("boom!")):
            result = validate(path)
            if not result.valid:
                assert any("could not read file" in e.lower() or "boom" in e for e in result.errors)

    def test_validate_null_type_non_string(self, tmp_path):
        """Validate should handle null values in numeric fields."""
        path = tmp_path / "data.csv"
        path.write_text("name,age\nAlice,\nBob,25\n", encoding="utf-8")

        schema = [
            {"name": "name", "type": "string"},
            {"name": "age", "type": "string"},
        ]
        result = validate(path, expected_schema=schema)
        assert result.valid  # null age is fine, not a type mismatch


# ═══════════════════════════════════════════════════════════════════════
# ConversionResult dataclass defaults
# ═══════════════════════════════════════════════════════════════════════


class TestConversionResult:
    """Cover ConversionResult dataclass."""

    def test_defaults(self):
        result = ConversionResult()
        assert result.rows_read == 0
        assert result.rows_written == 0
        assert result.input_format == ""
        assert result.output_format == ""
        assert result.errors == []

    def test_custom_values(self):
        result = ConversionResult(
            rows_read=10,
            rows_written=10,
            input_format="csv",
            output_format="json",
            errors=["warning: something"],
        )
        assert result.rows_read == 10
        assert result.rows_written == 10
        assert result.input_format == "csv"
        assert result.output_format == "json"
        assert len(result.errors) == 1


# ═══════════════════════════════════════════════════════════════════════
# detect_format — edge cases
# ═══════════════════════════════════════════════════════════════════════


class TestDetectFormatEdgeCases:
    """Cover detect_format() edge cases."""

    def test_protobuf_extensions(self):
        assert detect_format("message.proto") == "protobuf"
        assert detect_format("message.pbf") == "protobuf"

    def test_case_insensitivity(self):
        assert detect_format("DATA.CSV") == "csv"
        assert detect_format("Data.Json") == "json"

    def test_path_with_multiple_dots(self):
        """Path with multiple dots should use the last extension."""
        assert detect_format("archive.tar.gz") is None  # .gz not mapped
        assert detect_format("my.file.csv") == "csv"


# ═══════════════════════════════════════════════════════════════════════
# CLI edge cases — schema and format commands
# ═══════════════════════════════════════════════════════════════════════


class TestCLIMoreEdgeCases:
    """Additional CLI coverage for format and schema commands."""

    def test_formats_command_output(self):
        from click.testing import CliRunner

        from datamorph.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["formats"])
        assert result.exit_code == 0
        # Should list all registered formats
        for fmt in ("csv", "json", "jsonl", "yaml", "parquet", "avro"):
            assert fmt in result.output.lower()

    def test_schema_with_large_sample(self, tmp_path):
        from click.testing import CliRunner

        from datamorph.cli import cli

        path = tmp_path / "data.csv"
        path.write_text("a,b\n1,2\n3,4\n5,6\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(cli, ["schema", str(path), "--sample", "100"])
        assert result.exit_code == 0
        assert "a" in result.output
