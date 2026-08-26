"""Regression tests: zero-row Avro output artifact + CLI schema-file hardening."""
from __future__ import annotations

import json

from click.testing import CliRunner

from datamorph.cli import cli
from datamorph.converters import convert


def _csv(tmp_path, rows="name,age\nalice,30\n"):
    p = tmp_path / "in.csv"
    p.write_text(rows, encoding="utf-8")
    return str(p)


def test_zero_row_avro_output_file_exists_and_is_valid(tmp_path):
    src = _csv(tmp_path, rows="name,age\n")  # header only -> zero data rows
    out = tmp_path / "out.avro"
    result = convert(src, out)
    assert not result.errors
    assert result.rows_written == 0
    assert out.exists(), "empty conversion must still create the output file"
    import fastavro

    with open(out, "rb") as f:
        rows = list(fastavro.reader(f))
    assert rows == []


def test_validate_cmd_bad_json_schema_file_clean_exit(tmp_path):
    data = _csv(tmp_path)
    bad = tmp_path / "schema.json"
    bad.write_text("{not valid json", encoding="utf-8")
    r = CliRunner().invoke(cli, ["validate", data, "--schema", str(bad)])
    assert r.exit_code == 1
    assert "Could not load schema file" in r.output


def test_validate_cmd_wrong_shape_schema_file_clean_exit(tmp_path):
    data = _csv(tmp_path)
    bad = tmp_path / "schema.json"
    bad.write_text(json.dumps({"name": "x"}), encoding="utf-8")
    r = CliRunner().invoke(cli, ["validate", data, "--schema", str(bad)])
    assert r.exit_code == 1
    assert "non-empty JSON list" in r.output


def test_validate_cmd_good_schema_file_still_works(tmp_path):
    data = _csv(tmp_path)
    schema = [{"name": "name", "type": "string"}, {"name": "age", "type": "string"}]
    good = tmp_path / "schema.json"
    good.write_text(json.dumps(schema), encoding="utf-8")
    r = CliRunner().invoke(cli, ["validate", data, "--schema", str(good)])
    assert r.exit_code == 0
    assert "VALID" in r.output
