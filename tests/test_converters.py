"""Tests for DataMorph format converters and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from datamorph.cli import cli
from datamorph.converters import (
    _infer_type,
    _widen_type,
    convert,
    convert_batch,
    detect_format,
    get_reader,
    supported_formats,
)

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
        {"name": "Charlie", "age": 35, "city": "Chicago"},
    ]
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def sample_yaml(tmp_path):
    path = tmp_path / "test.yaml"
    data = [
        {"name": "Alice", "age": 30, "city": "NYC"},
        {"name": "Bob", "age": 25, "city": "LA"},
    ]
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


# ── Format Detection ─────────────────────────────────────────────────


class TestDetectFormat:
    def test_csv(self):
        assert detect_format("data.csv") == "csv"

    def test_json(self):
        assert detect_format("data.json") == "json"

    def test_yaml(self):
        assert detect_format("data.yaml") == "yaml"
        assert detect_format("data.yml") == "yaml"

    def test_parquet(self):
        assert detect_format("data.parquet") == "parquet"
        assert detect_format("data.pq") == "parquet"

    def test_avro(self):
        assert detect_format("data.avro") == "avro"

    def test_unknown(self):
        assert detect_format("data.txt") is None

    def test_supported_formats_not_empty(self):
        fmts = supported_formats()
        assert len(fmts) >= 5
        assert "csv" in fmts
        assert "json" in fmts
        assert "yaml" in fmts


# ── CSV ────────────────────────────────────────────────────────────────


class TestCsvConversion:
    def test_csv_to_json(self, sample_csv, tmp_path):
        output = tmp_path / "output.json"
        result = convert(sample_csv, output)
        assert not result.errors
        assert result.rows_written == 3
        assert result.input_format == "csv"
        assert result.output_format == "json"

        data = json.loads(output.read_text())
        assert len(data) == 3
        assert data[0]["name"] == "Alice"
        assert data[0]["age"] == "30"

    def test_csv_to_yaml(self, sample_csv, tmp_path):
        output = tmp_path / "output.yaml"
        result = convert(sample_csv, output)
        assert not result.errors
        assert result.rows_written == 3

    def test_csv_to_csv_copy(self, sample_csv, tmp_path):
        output = tmp_path / "copy.csv"
        result = convert(sample_csv, output)
        assert not result.errors
        assert result.rows_written == 3
        assert "Alice" in output.read_text()

    def test_csv_read_empty(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("name,age\n")
        result = convert(path, tmp_path / "out.json")
        assert not result.errors
        assert result.rows_written == 0

    def test_csv_with_custom_delimiter(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("name|age\nAlice|30\nBob|25\n")
        output = tmp_path / "out.json"
        result = convert(path, output, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2
        data = json.loads(output.read_text())
        assert data[0]["name"] == "Alice"
        assert data[1]["age"] == "25"

    def test_csv_custom_delimiter_roundtrip(self, tmp_path):
        """Verify pipe-delimited CSV can be read and written back."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("name|age\nAlice|30\nBob|25\n")
        json_path = tmp_path / "intermediate.json"
        result = convert(csv_path, json_path, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2

        csv_out = tmp_path / "roundtrip.csv"
        result = convert(json_path, csv_out, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2
        content = csv_out.read_text()
        assert "Alice" in content
        assert "name|age" in content  # pipe-delimited header preserved


# ── JSON ──────────────────────────────────────────────────────────────


class TestJsonConversion:
    def test_json_to_csv(self, sample_json, tmp_path):
        output = tmp_path / "output.csv"
        result = convert(sample_json, output)
        assert not result.errors
        assert result.rows_written == 3

        content = output.read_text()
        assert "Alice" in content
        assert "name" in content  # Header

    def test_json_to_json_copy(self, sample_json, tmp_path):
        output = tmp_path / "output.json"
        result = convert(sample_json, output)
        assert not result.errors
        assert result.rows_written == 3

    def test_json_to_yaml(self, sample_json, tmp_path):
        output = tmp_path / "output.yaml"
        result = convert(sample_json, output)
        assert not result.errors
        assert result.rows_written == 3

    def test_json_single_object(self, tmp_path):
        path = tmp_path / "single.json"
        path.write_text(json.dumps({"name": "Alice", "age": 30}))
        output = tmp_path / "out.csv"
        result = convert(path, output)
        assert not result.errors
        assert result.rows_written == 1


# ── YAML ──────────────────────────────────────────────────────────────


class TestYamlConversion:
    def test_yaml_to_json(self, sample_yaml, tmp_path):
        output = tmp_path / "output.json"
        result = convert(sample_yaml, output)
        assert not result.errors
        assert result.rows_written == 2

        data = json.loads(output.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "Alice"

    def test_yaml_to_csv(self, sample_yaml, tmp_path):
        output = tmp_path / "output.csv"
        result = convert(sample_yaml, output)
        assert not result.errors
        assert result.rows_written == 2


# ── Parquet ───────────────────────────────────────────────────────────


class TestParquetConversion:
    def test_csv_to_parquet(self, sample_csv, tmp_path):
        output = tmp_path / "output.parquet"
        result = convert(sample_csv, output)
        assert not result.errors
        assert result.rows_written == 3

    def test_parquet_to_csv(self, sample_csv, tmp_path):
        parquet_file = tmp_path / "temp.parquet"
        result = convert(sample_csv, parquet_file)
        assert not result.errors
        assert result.rows_written == 3

        output = tmp_path / "roundtrip.csv"
        result = convert(parquet_file, output)
        assert not result.errors
        assert result.rows_written == 3
        assert "Alice" in output.read_text()

    def test_parquet_to_json(self, sample_csv, tmp_path):
        parquet_file = tmp_path / "temp.parquet"
        convert(sample_csv, parquet_file)
        output = tmp_path / "out.json"
        result = convert(parquet_file, output)
        assert not result.errors
        assert result.rows_written == 3


# ── Avro ──────────────────────────────────────────────────────────────


class TestAvroConversion:
    def test_csv_to_avro(self, sample_csv, tmp_path):
        output = tmp_path / "output.avro"
        result = convert(sample_csv, output)
        assert not result.errors
        assert result.rows_written == 3

    def test_avro_to_csv(self, sample_csv, tmp_path):
        avro_file = tmp_path / "temp.avro"
        result = convert(sample_csv, avro_file)
        assert not result.errors

        output = tmp_path / "roundtrip.csv"
        result = convert(avro_file, output)
        assert not result.errors
        assert result.rows_written == 3
        assert "Alice" in output.read_text()

    def test_avro_to_json(self, sample_csv, tmp_path):
        avro_file = tmp_path / "temp.avro"
        convert(sample_csv, avro_file)
        output = tmp_path / "out.json"
        result = convert(avro_file, output)
        assert not result.errors
        assert result.rows_written == 3


# ── Error Handling ────────────────────────────────────────────────────


class TestErrors:
    def test_invalid_input_format(self, tmp_path):
        result = convert(tmp_path / "nonexistent.csv", tmp_path / "out.json")
        assert result.errors

    def test_unsupported_format(self):
        from datamorph.converters import get_reader
        with pytest.raises(ValueError, match="Unsupported format"):
            get_reader("exe")

    def test_unsupported_output_format(self, sample_csv, tmp_path):
        with pytest.raises(ValueError, match="Unsupported format"):
            convert(sample_csv, tmp_path / "out.txt", output_format="exe")

    def test_nonexistent_file(self, tmp_path):
        result = convert(tmp_path / "nope.csv", tmp_path / "out.json")
        assert result.errors

    def test_empty_json_array(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("[]")
        output = tmp_path / "out.csv"
        result = convert(path, output)
        assert not result.errors
        assert result.rows_written == 0


# ── Schema Inference ──────────────────────────────────────────────────


class TestSchemaInference:
    def test_infer_from_csv(self, sample_csv):
        reader = get_reader("csv")
        schema = reader.infer_schema(sample_csv)
        assert len(schema) == 3  # name, age, city
        field_names = {s["name"] for s in schema}
        assert field_names == {"name", "age", "city"}

    def test_infer_from_json(self, sample_json):
        reader = get_reader("json")
        schema = reader.infer_schema(sample_json)
        assert len(schema) == 3


# ── CLI Tests ────────────────────────────────────────────────────────


class TestCLI:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.1" in result.output

    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "convert" in result.output
        assert "batch" in result.output
        assert "schema" in result.output
        assert "formats" in result.output

    def test_convert_command(self, runner, sample_csv, tmp_path):
        output = tmp_path / "out.json"
        result = runner.invoke(cli, ["convert", str(sample_csv), str(output)])
        assert result.exit_code == 0
        assert "Converted" in result.output

    def test_convert_with_format_override(self, runner, sample_csv, tmp_path):
        output = tmp_path / "out.txt"
        result = runner.invoke(cli, [
            "convert", str(sample_csv), str(output),
            "--input-format", "csv",
            "--output-format", "json",
        ])
        assert result.exit_code == 0
        assert "Converted" in result.output

    def test_convert_to_parquet(self, runner, sample_csv, tmp_path):
        output = tmp_path / "out.parquet"
        result = runner.invoke(cli, ["convert", str(sample_csv), str(output)])
        assert result.exit_code == 0

    def test_convert_nonexistent_input(self, runner, tmp_path):
        result = runner.invoke(cli, ["convert", "/nonexistent/file.csv", str(tmp_path / "out.json")])
        assert result.exit_code != 0

    def test_formats_command(self, runner):
        result = runner.invoke(cli, ["formats"])
        assert result.exit_code == 0
        assert "csv" in result.output
        assert "json" in result.output

    def test_schema_command(self, runner, sample_csv):
        result = runner.invoke(cli, ["schema", str(sample_csv)])
        assert result.exit_code == 0
        assert "name" in result.output
        assert "age" in result.output

    def test_schema_json_output(self, runner, sample_csv):
        result = runner.invoke(cli, ["schema", str(sample_csv), "--json-output"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_batch_no_input(self, runner, tmp_path):
        result = runner.invoke(cli, [
            "batch", str(tmp_path), str(tmp_path / "out"),
            "--from", "csv", "--to", "json",
        ])
        assert result.exit_code == 0

    def test_formats_show_streaming(self, runner):
        result = runner.invoke(cli, ["formats"])
        assert result.exit_code == 0
        assert "csv" in result.output
        assert "jsonl" in result.output  # jsonl listed as streaming-capable


# ── Multi-format Roundtrips ──────────────────────────────────────────


class TestRoundtrips:
    def test_csv_json_csv_roundtrip(self, sample_csv, tmp_path):
        json_file = tmp_path / "step1.json"
        convert(sample_csv, json_file)
        csv_file = tmp_path / "step2.csv"
        result = convert(json_file, csv_file)
        assert not result.errors
        assert result.rows_written == 3
        assert "Alice" in csv_file.read_text()

    def test_csv_yaml_csv_roundtrip(self, sample_csv, tmp_path):
        yaml_file = tmp_path / "step1.yaml"
        convert(sample_csv, yaml_file)
        csv_file = tmp_path / "step2.csv"
        result = convert(yaml_file, csv_file)
        assert not result.errors
        assert result.rows_written == 3
        assert "Alice" in csv_file.read_text()

    def test_csv_json_yaml_roundtrip(self, sample_csv, tmp_path):
        json_file = tmp_path / "step1.json"
        convert(sample_csv, json_file)
        yaml_file = tmp_path / "step2.yaml"
        result = convert(json_file, yaml_file)
        assert not result.errors
        assert result.rows_written == 3

    def test_large_json_array(self, tmp_path):
        """Test with 1000 rows."""
        path = tmp_path / "large.json"
        data = [{"id": i, "value": f"item-{i}"} for i in range(1000)]
        path.write_text(json.dumps(data))

        output = tmp_path / "out.csv"
        result = convert(path, output)
        assert not result.errors
        assert result.rows_written == 1000

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 1001  # 1000 data + 1 header


# ── JSONL (JSON Lines) ────────────────────────────────────────────────


class TestJsonlConversion:
    def test_jsonl_to_json(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_text(
            json.dumps({"name": "Alice", "age": 30}) + "\n"
            + json.dumps({"name": "Bob", "age": 25}) + "\n"
        )
        output = tmp_path / "out.json"
        result = convert(path, output)
        assert not result.errors
        assert result.rows_written == 2
        data = json.loads(output.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "Alice"

    def test_jsonl_to_csv(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_text(
            json.dumps({"name": "Alice", "age": 30}) + "\n"
            + json.dumps({"name": "Bob", "age": 25}) + "\n"
        )
        output = tmp_path / "out.csv"
        result = convert(path, output)
        assert not result.errors
        assert result.rows_written == 2
        content = output.read_text()
        assert "Alice" in content
        assert "name" in content

    def test_csv_to_jsonl(self, sample_csv, tmp_path):
        output = tmp_path / "out.jsonl"
        result = convert(sample_csv, output)
        assert not result.errors
        assert result.rows_written == 3
        lines = output.read_text().strip().split("\n")
        assert len(lines) == 3
        data = json.loads(lines[0])
        assert data["name"] == "Alice"

    def test_jsonl_empty(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        output = tmp_path / "out.json"
        result = convert(path, output)
        assert not result.errors
        assert result.rows_written == 0


# ── Batch Conversion ──────────────────────────────────────────────────


# ── Writer kwarg leak regression ──────────────────────────────────────


class TestWriterKwargLeak:
    """Regression tests for delimiter kwarg leaking to non-CSV writers."""

    def test_csv_delimiter_to_parquet(self, tmp_path):
        """csv_delimiter should not crash when converting to Parquet."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("name|age\nAlice|30\nBob|25\n")
        out_path = tmp_path / "out.parquet"
        result = convert(csv_path, out_path, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2

    def test_csv_delimiter_to_avro(self, tmp_path):
        """csv_delimiter should not crash when converting to Avro."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("name|age\nAlice|30\nBob|25\n")
        out_path = tmp_path / "out.avro"
        result = convert(csv_path, out_path, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2

    def test_csv_delimiter_to_yaml(self, tmp_path):
        """csv_delimiter should not crash when converting to YAML."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("name|age\nAlice|30\nBob|25\n")
        out_path = tmp_path / "out.yaml"
        result = convert(csv_path, out_path, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2

    def test_csv_delimiter_to_jsonl(self, tmp_path):
        """csv_delimiter should not crash when converting to JSONL."""
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("name|age\nAlice|30\nBob|25\n")
        out_path = tmp_path / "out.jsonl"
        result = convert(csv_path, out_path, csv_delimiter="|")
        assert not result.errors
        assert result.rows_written == 2


# ── Batch Conversion ──────────────────────────────────────────────────


class TestBatchConversion:
    def test_batch_single_file(self, sample_csv, tmp_path):
        input_dir = sample_csv.parent
        output_dir = tmp_path / "batch_out"
        results = convert_batch(
            str(input_dir), str(output_dir),
            "csv", "json", pattern="test.csv",
        )
        assert len(results) >= 1
        assert not results[0].errors
        assert results[0].rows_written == 3
        assert (output_dir / "test.json").exists()

    def test_batch_no_matches(self, tmp_path):
        input_dir = tmp_path / "empty_dir"
        input_dir.mkdir()
        output_dir = tmp_path / "batch_out"
        results = convert_batch(
            str(input_dir), str(output_dir),
            "csv", "json", pattern="*.csv",
        )
        assert results == []


# ── Type inference ────────────────────────────────────────────────────


class TestTypeInference:
    def test_infer_bool(self):
        assert _infer_type(True) == "bool"
        assert _infer_type(False) == "bool"

    def test_infer_int(self):
        assert _infer_type(42) == "int64"
        assert _infer_type(0) == "int64"
        assert _infer_type(-1) == "int64"

    def test_infer_float(self):
        assert _infer_type(3.14) == "float64"
        assert _infer_type(0.0) == "float64"

    def test_infer_string(self):
        assert _infer_type("hello") == "string"
        assert _infer_type("") == "string"

    def test_infer_date_string(self):
        assert _infer_type("2024-01-15") == "date"
        assert _infer_type("2026-05-18") == "date"

    def test_infer_none(self):
        assert _infer_type(None) == "null"

    def test_infer_other(self):
        assert _infer_type([1, 2, 3]) == "string"
        assert _infer_type({"key": "val"}) == "string"


# ── Edge-case format detection ──────────────────────────────────────


class TestDetectFormatEdgeCases:
    """Tests for less common format extensions."""

    def test_avsc_is_avro(self):
        assert detect_format("schema.avsc") == "avro"

    def test_pq_is_parquet(self):
        assert detect_format("data.pq") == "parquet"

    def test_pbf_is_protobuf(self):
        assert detect_format("msg.pbf") == "protobuf"

    def test_proto_is_protobuf(self):
        assert detect_format("msg.proto") == "protobuf"

    def test_yml_is_yaml(self):
        assert detect_format("data.yml") == "yaml"

    def test_jsonl_extension(self):
        assert detect_format("data.jsonl") == "jsonl"

    def test_uppercase_extension(self):
        """detect_format lowercases the extension."""
        assert detect_format("DATA.CSV") == "csv"
        assert detect_format("Data.Json") == "json"

    def test_no_extension(self):
        assert detect_format("README") is None

    def test_double_extension(self):
        assert detect_format("archive.tar.gz") is None


# ── convert() with explicit format overrides ─────────────────────────


class TestConvertWithFormatOverride:
    """Test convert() with explicit input_format/output_format overrides."""

    def test_format_override_output(self, sample_csv, tmp_path):
        """Write CSV data to a file with .txt extension but json format."""
        output = tmp_path / "output.txt"
        result = convert(sample_csv, output, output_format="json")
        assert not result.errors
        assert result.rows_written == 3
        assert result.output_format == "json"
        data = json.loads(output.read_text())
        assert len(data) == 3

    def test_format_override_input(self, sample_json, tmp_path):
        """Read JSON from a file with .dat extension."""
        renamed = tmp_path / "data.dat"
        renamed.write_text(sample_json.read_text())
        output = tmp_path / "out.csv"
        result = convert(renamed, output, input_format="json")
        assert not result.errors
        assert result.rows_written == 3
        assert result.input_format == "json"

    def test_format_override_both(self, sample_csv, tmp_path):
        """Override both formats explicitly."""
        output = tmp_path / "output.dat"
        result = convert(sample_csv, output, input_format="csv", output_format="yaml")
        assert not result.errors
        assert result.rows_written == 3

    def test_undetectable_output_format_errors(self, sample_csv, tmp_path):
        """If output has no recognizable extension and no override, return error."""
        output = tmp_path / "output.xyz"
        result = convert(sample_csv, output)
        assert result.errors
        assert "Could not detect output format" in result.errors[0]


# ── convert_batch() recursive unit test ───────────────────────────────


class TestBatchConversionRecursive:
    """Unit tests for convert_batch with recursive=True."""

    def test_recursive_finds_nested_files(self, tmp_path):
        """convert_batch with recursive should find files in subdirectories."""
        subdir = tmp_path / "input" / "nested"
        subdir.mkdir(parents=True)
        csv_file = subdir / "data.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")

        output_dir = tmp_path / "output"
        results = convert_batch(
            str(tmp_path / "input"), str(output_dir),
            "csv", "json", recursive=True,
        )
        assert len(results) == 1
        assert not results[0].errors
        assert results[0].rows_written == 2
        # Verify output preserves directory structure
        out_file = output_dir / "nested" / "data.json"
        assert out_file.exists()

    def test_recursive_vs_non_recursive(self, tmp_path):
        """Non-recursive should not find files in subdirectories."""
        subdir = tmp_path / "input" / "sub"
        subdir.mkdir(parents=True)
        csv_file = subdir / "data.csv"
        csv_file.write_text("name,age\nAlice,30\n")

        output_dir = tmp_path / "output"
        results = convert_batch(
            str(tmp_path / "input"), str(output_dir),
            "csv", "json", recursive=False,
        )
        assert len(results) == 0

    def test_recursive_multiple_levels(self, tmp_path):
        """Recursive should find files at multiple nesting levels."""
        input_dir = tmp_path / "input"
        level1 = input_dir / "l1"
        level2 = input_dir / "l1" / "l2"
        level1.mkdir(parents=True)
        level2.mkdir(parents=True)

        (input_dir / "top.csv").write_text("name\nTop\n")
        (level1 / "mid.csv").write_text("name\nMid\n")
        (level2 / "deep.csv").write_text("name\nDeep\n")

        output_dir = tmp_path / "output"
        results = convert_batch(
            str(input_dir), str(output_dir),
            "csv", "json", recursive=True,
        )
        assert len(results) == 3
        assert all(not r.errors for r in results)


# ── __main__.py invocation ─────────────────────────────────────────────


class TestMainModule:
    """Test that python -m datamorph works."""

    def test_main_module_runs(self, runner):
        """python -m datamorph should invoke the CLI."""
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "datamorph", "--version"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).parent.parent),
        )
        assert result.returncode == 0
        assert "0.1.1" in result.stdout


class TestTypeWidening:
    def test_widen_identical(self):
        assert _widen_type("int64", "int64") == "int64"
        assert _widen_type("string", "string") == "string"

    def test_widen_int_to_float(self):
        assert _widen_type("int64", "float64") == "float64"
        assert _widen_type("float64", "int64") == "float64"

    def test_widen_to_string(self):
        assert _widen_type("int64", "string") == "string"
        assert _widen_type("string", "int64") == "string"
        assert _widen_type("float64", "string") == "string"
        assert _widen_type("bool", "string") == "string"

    def test_widen_from_null(self):
        assert _widen_type("null", "int64") == "int64"
        assert _widen_type("null", "float64") == "float64"
        assert _widen_type("null", "string") == "string"
        assert _widen_type("null", "bool") == "bool"
        assert _widen_type("null", "date") == "date"

    def test_widen_unrelated(self):
        assert _widen_type("date", "int64") == "string"
        assert _widen_type("int64", "date") == "string"
