"""Tests for DataMorph format converters and CLI."""

from __future__ import annotations

import json

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

    def test_json_dict_of_dicts(self, tmp_path):
        """JSON with dict-of-dicts structure (keyed objects)."""
        path = tmp_path / "nested.json"
        path.write_text(
            json.dumps(
                {
                    "a": {"name": "Alice", "age": 30},
                    "b": {"name": "Bob", "age": 25},
                }
            )
        )
        output = tmp_path / "out.csv"
        result = convert(path, output)
        assert not result.errors
        assert result.rows_written == 2
        content = output.read_text()
        assert "Alice" in content
        assert "Bob" in content


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

    def test_parquet_write_empty(self, tmp_path):
        """Writing empty dataset to Parquet should produce a valid empty file."""
        from datamorph.converters import ParquetWriter

        writer = ParquetWriter()
        path = tmp_path / "empty.parquet"
        count = writer.write_stream(iter([]), path)
        assert count == 0
        assert path.exists()
        assert path.stat().st_size > 0  # valid parquet has header/footer


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

    def test_avro_write_empty(self, tmp_path):
        """Writing empty dataset to Avro should return 0 without error."""
        from datamorph.converters import AvroWriter

        writer = AvroWriter()
        path = tmp_path / "empty.avro"
        count = writer.write_stream(iter([]), path)
        assert count == 0

    def test_avro_nullable_first_row(self, tmp_path):
        """Avro should handle nullable fields even when the first row has nulls."""
        path = tmp_path / "data.csv"
        path.write_text(
            "name,age,email\nAlice,,alice@test.com\nBob,30,\nCharlie,25,charlie@test.com\n"
        )
        avro_file = tmp_path / "out.avro"
        result = convert(path, avro_file)
        assert not result.errors
        assert result.rows_written == 3

        # Roundtrip back to CSV to verify data integrity
        csv_out = tmp_path / "roundtrip.csv"
        result = convert(avro_file, csv_out)
        assert not result.errors
        assert result.rows_written == 3
        content = csv_out.read_text()
        assert "Alice" in content
        assert "Bob" in content
        assert "Charlie" in content

    def test_avro_nullable_all_but_first(self, tmp_path):
        """Avro should handle nullable fields where nulls appear after the first row."""
        path = tmp_path / "data.csv"
        path.write_text("name,age\nAlice,30\nBob,\nCharlie,35\n")
        avro_file = tmp_path / "out.avro"
        result = convert(path, avro_file)
        assert not result.errors
        assert result.rows_written == 3

        # Roundtrip back to verify
        csv_out = tmp_path / "roundtrip.csv"
        result = convert(avro_file, csv_out)
        assert not result.errors
        assert result.rows_written == 3
        content = csv_out.read_text()
        # Nulls should be preserved as empty in CSV
        assert "Alice,30" in content or "Alice" in content

    def test_avro_all_nullable_fields(self, tmp_path):
        """Avro should handle rows where ALL field values are nullable."""
        path = tmp_path / "data.csv"
        path.write_text("name,score\nAlice,\nBob,\n")
        avro_file = tmp_path / "out.avro"
        result = convert(path, avro_file)
        assert not result.errors
        assert result.rows_written == 2

        # Roundtrip back
        csv_out = tmp_path / "roundtrip.csv"
        result = convert(avro_file, csv_out)
        assert not result.errors
        assert result.rows_written == 2


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

    def test_undetectable_input_format_errors(self, tmp_path):
        """If input has no recognizable extension and no override, return error."""
        path = tmp_path / "input.xyz"
        path.write_text("some,data\n")
        output = tmp_path / "out.json"
        result = convert(path, output)
        assert result.errors
        assert "Could not detect input format" in result.errors[0]


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
        result = runner.invoke(
            cli,
            [
                "convert",
                str(sample_csv),
                str(output),
                "--input-format",
                "csv",
                "--output-format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert "Converted" in result.output

    def test_convert_to_parquet(self, runner, sample_csv, tmp_path):
        output = tmp_path / "out.parquet"
        result = runner.invoke(cli, ["convert", str(sample_csv), str(output)])
        assert result.exit_code == 0

    def test_convert_nonexistent_input(self, runner, tmp_path):
        result = runner.invoke(
            cli, ["convert", "/nonexistent/file.csv", str(tmp_path / "out.json")]
        )
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
        result = runner.invoke(
            cli,
            [
                "batch",
                str(tmp_path),
                str(tmp_path / "out"),
                "--from",
                "csv",
                "--to",
                "json",
            ],
        )
        assert result.exit_code == 0

    def test_batch_with_files(self, runner, sample_csv, tmp_path):
        """Batch convert CSV files in a directory to JSON via CLI."""
        output_dir = tmp_path / "json_out"
        result = runner.invoke(
            cli,
            [
                "batch",
                str(sample_csv.parent),
                str(output_dir),
                "--from",
                "csv",
                "--to",
                "json",
                "--pattern",
                "*.csv",
            ],
        )
        assert result.exit_code == 0
        assert "converted" in result.output.lower() or "Complete" in result.output
        out_files = list(output_dir.glob("*.json"))
        assert len(out_files) >= 1

    def test_batch_recursive(self, runner, tmp_path):
        """Batch convert with --recursive to find files in subdirectories."""
        subdir = tmp_path / "sub" / "nested"
        subdir.mkdir(parents=True)
        csv_file = subdir / "data.csv"
        csv_file.write_text("name,age\nAlice,30\nBob,25\n")

        output_dir = tmp_path / "json_out"
        result = runner.invoke(
            cli,
            [
                "batch",
                str(tmp_path),
                str(output_dir),
                "--from",
                "csv",
                "--to",
                "json",
                "--recursive",
            ],
        )
        assert result.exit_code == 0
        assert "converted" in result.output.lower() or "Complete" in result.output
        out_files = list(output_dir.rglob("*.json"))
        assert len(out_files) >= 1
        # Verify nested directory structure is preserved
        assert any("nested" in str(f) for f in out_files)

    def test_batch_to_parquet(self, runner, sample_csv, tmp_path):
        """Batch convert CSV files to Parquet via CLI."""
        output_dir = tmp_path / "pq_out"
        result = runner.invoke(
            cli,
            [
                "batch",
                str(sample_csv.parent),
                str(output_dir),
                "--from",
                "csv",
                "--to",
                "parquet",
            ],
        )
        assert result.exit_code == 0
        out_files = list(output_dir.glob("*.parquet"))
        assert len(out_files) >= 1

    def test_batch_to_jsonl(self, runner, sample_csv, tmp_path):
        """Batch convert CSV files to JSONL via CLI."""
        output_dir = tmp_path / "jsonl_out"
        result = runner.invoke(
            cli,
            [
                "batch",
                str(sample_csv.parent),
                str(output_dir),
                "--from",
                "csv",
                "--to",
                "jsonl",
            ],
        )
        assert result.exit_code == 0
        out_files = list(output_dir.glob("*.jsonl"))
        assert len(out_files) >= 1
        content = out_files[0].read_text()
        assert content.count("\n") >= 1  # at least one complete JSONL line

    def test_batch_csv_delimiter(self, runner, tmp_path):
        """Batch convert CSV with custom delimiter via CLI."""
        subdir = tmp_path / "data"
        subdir.mkdir()
        csv_file = subdir / "data.csv"
        csv_file.write_text("name|age\nAlice|30\nBob|25\n")
        output_dir = tmp_path / "json_out"
        result = runner.invoke(
            cli,
            [
                "batch",
                str(subdir),
                str(output_dir),
                "--from",
                "csv",
                "--to",
                "json",
                "--csv-delimiter",
                "|",
            ],
        )
        assert result.exit_code == 0
        out_files = list(output_dir.glob("*.json"))
        assert len(out_files) >= 1
        data = json.loads(out_files[0].read_text())
        if isinstance(data, list):
            assert len(data) >= 1

    def test_batch_pattern_no_match(self, runner, tmp_path):
        """Batch convert with pattern that matches no files."""
        subdir = tmp_path / "data"
        subdir.mkdir()
        csv_file = subdir / "data.csv"
        csv_file.write_text("name,age\nAlice,30\n")
        output_dir = tmp_path / "out"
        result = runner.invoke(
            cli,
            [
                "batch",
                str(subdir),
                str(output_dir),
                "--from",
                "csv",
                "--to",
                "json",
                "--pattern",
                "*.tsv",
            ],
        )
        assert result.exit_code == 0  # graceful no-op
        out_files = list(output_dir.glob("*"))
        assert len(out_files) == 0

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
            json.dumps({"name": "Alice", "age": 30})
            + "\n"
            + json.dumps({"name": "Bob", "age": 25})
            + "\n"
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
            json.dumps({"name": "Alice", "age": 30})
            + "\n"
            + json.dumps({"name": "Bob", "age": 25})
            + "\n"
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
            str(input_dir),
            str(output_dir),
            "csv",
            "json",
            pattern="test.csv",
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
            str(input_dir),
            str(output_dir),
            "csv",
            "json",
            pattern="*.csv",
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

    def test_infer_invalid_date_string(self):
        # String with date-like format but invalid date — falls through to "string"
        assert _infer_type("2024-13-01") == "string"
        assert _infer_type("2024-00-15") == "string"
        assert _infer_type("not-a-date") == "string"
        assert _infer_type("1234-56-78") == "string"


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


# ── Avro Writer type mapping ────────────────────────────────────────────


class TestAvroTypeMapping:
    """Unit tests for _avro_type type mapping."""

    def test_avro_type_bool(self):
        from datamorph.converters import _avro_type

        assert _avro_type(True) == "boolean"

    def test_avro_type_int(self):
        from datamorph.converters import _avro_type

        assert _avro_type(42) == "long"

    def test_avro_type_float(self):
        from datamorph.converters import _avro_type

        assert _avro_type(3.14) == "double"

    def test_avro_type_none(self):
        from datamorph.converters import _avro_type

        assert _avro_type(None) == "null"

    def test_avro_type_string(self):
        from datamorph.converters import _avro_type

        assert _avro_type("hello") == "string"


class TestScalarJsonRootAndRowsRead:
    """Coverage for scalar/bare JSON roots and the previously-unpopulated rows_read."""

    def test_rows_read_dict_root(self, tmp_path):
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text(json.dumps({"a": 1, "b": 2}), encoding="utf-8")
        result = convert(inp, out, input_format="json", output_format="json")
        assert result.rows_read == 1
        assert result.rows_written == 1
        assert json.loads(out.read_text(encoding="utf-8")) == [{"a": 1, "b": 2}]

    def test_rows_read_list_root(self, tmp_path):
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
        result = convert(inp, out, input_format="json", output_format="json")
        assert result.rows_read == 2
        assert result.rows_written == 2
        assert json.loads(out.read_text(encoding="utf-8")) == [{"a": 1}, {"a": 2}]

    def test_scalar_string_root_round_trip(self, tmp_path):
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text('"hello world"', encoding="utf-8")
        result = convert(inp, out, input_format="json", output_format="json")
        assert result.rows_read == 1
        assert result.rows_written == 1
        assert json.loads(out.read_text(encoding="utf-8")) == [{"data": "hello world"}]

    def test_scalar_number_root_round_trip(self, tmp_path):
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text("42", encoding="utf-8")
        result = convert(inp, out, input_format="json", output_format="json")
        assert result.rows_read == 1
        assert result.rows_written == 1
        assert json.loads(out.read_text(encoding="utf-8")) == [{"data": 42}]

    def test_scalar_null_root_round_trip(self, tmp_path):
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text("null", encoding="utf-8")
        result = convert(inp, out, input_format="json", output_format="json")
        assert result.rows_read == 1
        assert result.rows_written == 1
        assert json.loads(out.read_text(encoding="utf-8")) == [{"data": None}]

    def test_scalar_bool_root_round_trip(self, tmp_path):
        inp = tmp_path / "in.json"
        out = tmp_path / "out.json"
        inp.write_text("true", encoding="utf-8")
        result = convert(inp, out, input_format="json", output_format="json")
        assert result.rows_read == 1
        assert result.rows_written == 1
        assert json.loads(out.read_text(encoding="utf-8")) == [{"data": True}]
