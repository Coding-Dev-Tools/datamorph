"""Tests for ConversionResult.rows_read accounting and silent-failure detection.

Regression coverage for the bug where ``convert()`` declared ``rows_read`` on
``ConversionResult`` but never populated it (always 0), and where a conversion
that read rows yet wrote none was reported as a green success.
"""

from __future__ import annotations

import json

import pytest

from datamorph import converters
from datamorph.converters import (
    FormatWriter,
    RowStream,
    convert,
    register_format,
)


def _write_csv(path, rows: list[dict]) -> None:
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def sample_csv(tmp_path):
    path = tmp_path / "in.csv"
    _write_csv(
        path,
        [
            {"id": "1", "name": "alice"},
            {"id": "2", "name": "bob"},
            {"id": "3", "name": "carol"},
        ],
    )
    return path


def test_rows_read_populated_csv_to_json(sample_csv, tmp_path):
    out = tmp_path / "out.json"
    result = convert(str(sample_csv), str(out))

    assert not result.errors
    assert result.rows_read == 3
    assert result.rows_written == 3
    # Output actually contains the rows.
    assert len(json.loads(out.read_text())) == 3


def test_rows_read_equals_written_across_formats(sample_csv, tmp_path):
    for ext in ("json", "jsonl", "yaml"):
        out = tmp_path / f"out.{ext}"
        result = convert(str(sample_csv), str(out))
        assert not result.errors, result.errors
        assert result.rows_read == 3, ext
        assert result.rows_read == result.rows_written, ext


def test_empty_input_reports_zero_and_no_silent_failure(tmp_path):
    # Header only, no data rows.
    empty = tmp_path / "empty.csv"
    empty.write_text("id,name\n", encoding="utf-8")
    out = tmp_path / "out.json"

    result = convert(str(empty), str(out))

    assert result.rows_read == 0
    assert result.rows_written == 0
    # Zero-in/zero-out is legitimate and must NOT be flagged as a silent failure.
    assert not result.errors


def test_silent_failure_detected_when_rows_read_but_none_written(sample_csv, tmp_path):
    """A writer that consumes rows but emits none must be reported as an error,
    not a green 'Converted 0 rows' success."""

    class _NullSinkWriter(FormatWriter):
        def write_stream(self, rows: RowStream, path) -> int:
            # Consume the stream (simulating real read work) but write nothing.
            for _ in rows:
                pass
            open(path, "w").close()
            return 0

    register_format("nullsink", writer=_NullSinkWriter)
    try:
        out = tmp_path / "out.nullsink"
        result = convert(str(sample_csv), str(out), output_format="nullsink")

        assert result.rows_read == 3
        assert result.rows_written == 0
        assert result.errors
        assert "silent failure" in result.errors[0]
    finally:
        converters._WRITERS.pop("nullsink", None)


def test_rows_read_counted_on_partial_read_before_error(sample_csv, tmp_path):
    """If the writer raises partway through, rows_read still reflects what was
    pulled from the source (set in a finally block)."""

    class _ExplodingWriter(FormatWriter):
        def write_stream(self, rows: RowStream, path) -> int:
            count = 0
            for _ in rows:
                count += 1
                if count == 2:
                    raise RuntimeError("boom")
            return count

    register_format("boom", writer=_ExplodingWriter)
    try:
        out = tmp_path / "out.boom"
        result = convert(str(sample_csv), str(out), output_format="boom")

        assert result.rows_read == 2  # counted up to the point of failure
        assert any("Conversion failed" in e for e in result.errors)
    finally:
        converters._WRITERS.pop("boom", None)
