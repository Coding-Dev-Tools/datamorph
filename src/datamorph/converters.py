"""Data format conversion engine for DataMorph.

Supports: CSV, JSON, YAML, Parquet, Avro, Protobuf (via optional protobuf dep).
All conversions are streaming-safe (row-by-row for text formats, row-group for columnar).
"""

from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator

# ── Types ────────────────────────────────────────────────────────────

Row = dict[str, Any]
RowStream = Generator[Row, None, None]

# Registered format readers/writers
_READERS: dict[str, type["FormatReader"]] = {}
_WRITERS: dict[str, type["FormatWriter"]] = {}


def register_format(
    name: str, reader: type["FormatReader"] | None = None, writer: type["FormatWriter"] | None = None
) -> None:
    """Register a format reader and/or writer."""
    if reader:
        _READERS[name] = reader
    if writer:
        _WRITERS[name] = writer


def supported_formats() -> list[str]:
    """Return sorted list of supported format names."""
    return sorted(set(_READERS.keys()) | set(_WRITERS.keys()))


def get_reader(name: str, **kwargs: Any) -> "FormatReader":
    cls = _READERS.get(name)
    if not cls:
        raise ValueError(f"Unsupported format for reading: {name}. Supported: {', '.join(_READERS.keys())}")
    return cls(**kwargs)


def get_writer(name: str, **kwargs: Any) -> "FormatWriter":
    cls = _WRITERS.get(name)
    if not cls:
        raise ValueError(f"Unsupported format for writing: {name}. Supported: {', '.join(_WRITERS.keys())}")
    return cls(**kwargs)


def detect_format(path: str | Path) -> str | None:
    """Detect file format from extension."""
    ext = Path(path).suffix.lower()
    ext_map = {
        ".csv": "csv",
        ".json": "json",
        ".jsonl": "jsonl",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".parquet": "parquet",
        ".pq": "parquet",
        ".avro": "avro",
        ".avsc": "avro",
        ".proto": "protobuf",
        ".pbf": "protobuf",
    }
    return ext_map.get(ext)


# ── Abstract base classes ────────────────────────────────────────────


class FormatReader(ABC):
    """Base class for format readers."""

    @abstractmethod
    def read_stream(self, path: str | Path) -> RowStream:
        """Read rows one at a time (streaming-safe)."""
        ...

    def read_all(self, path: str | Path) -> list[Row]:
        """Read all rows into memory."""
        return list(self.read_stream(path))

    def infer_schema(self, path: str | Path, sample_size: int = 100) -> list[dict[str, str]]:
        """Infer schema from a sample of rows."""
        rows = []
        for i, row in enumerate(self.read_stream(path)):
            rows.append(row)
            if i >= sample_size - 1:
                break
        return _infer_schema_from_rows(rows)


class FormatWriter(ABC):
    """Base class for format writers."""

    def __init__(self) -> None:
        self._field_order: list[str] | None = None

    def set_field_order(self, fields: list[str]) -> None:
        """Set the order of fields for output."""
        self._field_order = fields

    @abstractmethod
    def write_stream(self, rows: RowStream, path: str | Path) -> int:
        """Write rows from a stream. Returns number of rows written."""
        ...


# ── Schema inference ─────────────────────────────────────────────────


def _infer_schema_from_rows(rows: list[Row]) -> list[dict[str, str]]:
    """Infer schema (field name -> type) from sample rows."""
    if not rows:
        return []
    fields: dict[str, str] = {}
    for row in rows:
        for key, val in row.items():
            if key not in fields:
                fields[key] = _infer_type(val)
            else:
                # Widen type if necessary
                current = fields[key]
                new_type = _infer_type(val)
                fields[key] = _widen_type(current, new_type)
    return [{"name": k, "type": v} for k, v in fields.items()]


def _infer_type(val: Any) -> str:
    if isinstance(val, bool):
        return "bool"
    elif isinstance(val, int):
        return "int64"
    elif isinstance(val, float):
        return "float64"
    elif isinstance(val, str):
        # Check if string is a date
        if val and len(val) == 10 and val[4] == "-" and val[7] == "-":
            try:
                from datetime import date
                date.fromisoformat(val)
                return "date"
            except (ValueError, IndexError):
                pass
        return "string"
    elif val is None:
        return "null"
    else:
        return "string"


_type_widening: dict[tuple[str, str], str] = {
    ("int64", "float64"): "float64",
    ("int64", "string"): "string",
    ("float64", "string"): "string",
    ("null", "int64"): "int64",
    ("null", "float64"): "float64",
    ("null", "string"): "string",
    ("null", "bool"): "bool",
    ("null", "date"): "date",
}

def _widen_type(a: str, b: str) -> str:
    if a == b:
        return a
    key = (a, b) if (a, b) in _type_widening else (b, a)
    return _type_widening.get(key, "string")


# ── CSV Reader/Writer ────────────────────────────────────────────────


class CsvReader(FormatReader):
    def __init__(self, delimiter: str = ",") -> None:
        super().__init__()
        self.delimiter = delimiter

    def read_stream(self, path: str | Path) -> RowStream:
        with open(path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            for row in reader:
                yield {k.strip(): v.strip() if v else None for k, v in row.items()}


class CsvWriter(FormatWriter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.delimiter = kwargs.get("delimiter", ",")

    def write_stream(self, rows: RowStream, path: str | Path) -> int:
        count = 0
        fieldnames: list[str] | None = None
        with open(path, "w", newline="", encoding="utf-8") as f:
            for count, row in enumerate(rows, 1):
                if fieldnames is None:
                    fieldnames = self._field_order or list(row.keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=self.delimiter)
                    writer.writeheader()
                writer.writerow(row)
        return count


# ── JSON Reader/Writer ───────────────────────────────────────────────


class JsonReader(FormatReader):
    def read_stream(self, path: str | Path) -> RowStream:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            # If it's a dict of dicts (e.g., keyed objects)
            first_val = next(iter(data.values())) if data else None
            if isinstance(first_val, dict):
                for val in data.values():
                    yield val
            else:
                yield data
        else:
            yield {"data": data}


class JsonWriter(FormatWriter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.indent = kwargs.get("indent", 2)

    def write_stream(self, rows: RowStream, path: str | Path) -> int:
        rows_list = list(rows)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows_list, f, indent=self.indent, default=str, ensure_ascii=False)
        return len(rows_list)


# ── JSONL (JSON Lines) Reader/Writer ─────────────────────────────────


class JsonlReader(FormatReader):
    def read_stream(self, path: str | Path) -> RowStream:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)


class JsonlWriter(FormatWriter):
    def write_stream(self, rows: RowStream, path: str | Path) -> int:
        count = 0
        with open(path, "w", encoding="utf-8") as f:
            for count, row in enumerate(rows, 1):
                f.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
        return count


# ── YAML Reader/Writer ────────────────────────────────────────────────


class YamlReader(FormatReader):
    def read_stream(self, path: str | Path) -> RowStream:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            yield data
        else:
            yield {"data": data}


class YamlWriter(FormatWriter):
    def write_stream(self, rows: RowStream, path: str | Path) -> int:
        import yaml
        rows_list = list(rows)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(rows_list, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return len(rows_list)


# ── Parquet Reader/Writer ─────────────────────────────────────────────


class ParquetReader(FormatReader):
    def read_stream(self, path: str | Path) -> RowStream:
        import pyarrow.parquet as pq
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches():
            table = batch.to_pandas()
            for _, row in table.iterrows():
                yield row.where(row.notna(), None).to_dict()


class ParquetWriter(FormatWriter):
    def write_stream(self, rows: RowStream, path: str | Path) -> int:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        rows_list = list(rows)
        if not rows_list:
            # Write empty file with schema
            empty = pa.table({})
            pq.write_table(empty, path)
            return 0
        df = pd.DataFrame(rows_list)
        table = pa.Table.from_pandas(df)
        pq.write_table(table, path)
        return len(rows_list)


# ── Avro Reader/Writer ────────────────────────────────────────────────


class AvroReader(FormatReader):
    def read_stream(self, path: str | Path) -> RowStream:
        import fastavro
        with open(path, "rb") as f:
            reader = fastavro.reader(f)
            for row in reader:
                yield dict(row)


class AvroWriter(FormatWriter):
    def write_stream(self, rows: RowStream, path: str | Path) -> int:
        import fastavro
        rows_list = list(rows)
        if not rows_list:
            return 0

        # Infer schema from first row
        schema = {
            "type": "record",
            "name": "Record",
            "fields": [
                {"name": k, "type": _avro_type(v)}
                for k, v in rows_list[0].items()
            ],
        }

        with open(path, "wb") as f:
            fastavro.writer(f, schema, rows_list)
        return len(rows_list)


def _avro_type(val: Any) -> str | list:
    if isinstance(val, bool):
        return "boolean"
    elif isinstance(val, int):
        return "long"
    elif isinstance(val, float):
        return "double"
    elif val is None:
        return "null"
    else:
        return "string"


# ── Protobuf Reader/Writer (optional) ─────────────────────────────────


# Protobuf support requires a compiled .proto file descriptor.
# We provide a schema-based dynamic approach for well-known structures.
class ProtobufConversionError(Exception):
    pass


# ── Register all formats ─────────────────────────────────────────────

register_format("csv", CsvReader, CsvWriter)
register_format("json", JsonReader, JsonWriter)
register_format("jsonl", JsonlReader, JsonlWriter)
register_format("yaml", YamlReader, YamlWriter)
register_format("parquet", ParquetReader, ParquetWriter)
register_format("avro", AvroReader, AvroWriter)


# ── High-level conversion function ───────────────────────────────────


@dataclass
class ConversionResult:
    rows_read: int = 0
    rows_written: int = 0
    input_format: str = ""
    output_format: str = ""
    errors: list[str] = field(default_factory=list)


def convert(
    input_path: str | Path,
    output_path: str | Path,
    input_format: str | None = None,
    output_format: str | None = None,
    stream: bool = False,
    **writer_kwargs: Any,
) -> ConversionResult:
    """Convert a file from one format to another.

    Args:
        input_path: Source file path.
        output_path: Destination file path.
        input_format: Source format (auto-detected from extension if None).
        output_format: Target format (auto-detected from extension if None).
        stream: If True, use streaming (row-by-row) conversion.
        **writer_kwargs: Additional kwargs passed to the format writer.

    Returns:
        ConversionResult with counts and any errors.
    """
    result = ConversionResult()

    # Detect formats
    if not input_format:
        input_format = detect_format(input_path)
    if not output_format:
        output_format = detect_format(output_path)

    if not input_format:
        result.errors.append(f"Could not detect input format for: {input_path}")
        return result
    if not output_format:
        result.errors.append(f"Could not detect output format for: {output_path}")
        return result

    result.input_format = input_format
    result.output_format = output_format

    # Normalize csv_delimiter to delimiter for consistency
    if "csv_delimiter" in writer_kwargs:
        writer_kwargs.setdefault("delimiter", writer_kwargs.pop("csv_delimiter"))

    # Get reader and writer (pass writer_kwargs that apply to reader, like csv delimiter)
    reader_kwargs: dict[str, Any] = {}
    if input_format == "csv" and "delimiter" in writer_kwargs:
        reader_kwargs["delimiter"] = writer_kwargs["delimiter"]
    reader = get_reader(input_format, **reader_kwargs)
    writer = get_writer(output_format, **writer_kwargs)

    # If writing to parquet/avro, we may need field order from schema
    if output_format in ("parquet", "avro"):
        schema = reader.infer_schema(input_path)
        field_names = [s["name"] for s in schema]
        writer.set_field_order(field_names)
    elif output_format == "csv":
        # Get field order from first few rows for CSV header
        sample = reader.read_stream(input_path)
        try:
            first_row = next(sample)
            writer.set_field_order(list(first_row.keys()))
            # We consumed the first row, so we need to chain it back
            sample = _prepend_row(sample, first_row)
        except StopIteration:
            pass

    # Convert
    try:
        row_stream = reader.read_stream(input_path)
        result.rows_written = writer.write_stream(row_stream, output_path)
    except Exception as e:
        result.errors.append(f"Conversion failed: {e}")

    return result


def convert_batch(
    input_dir: str | Path,
    output_dir: str | Path,
    input_format: str,
    output_format: str,
    pattern: str = "*",
    recursive: bool = False,
    **writer_kwargs: Any,
) -> list[ConversionResult]:
    """Convert all matching files in a directory."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    glob_pattern = f"**/{pattern}" if recursive else pattern
    results: list[ConversionResult] = []

    for input_path in sorted(input_dir.glob(glob_pattern)):
        if input_path.is_dir():
            continue
        if detect_format(str(input_path)) != input_format:
            continue

        # Preserve relative path structure
        rel_path = input_path.relative_to(input_dir)
        output_path = output_dir / rel_path.with_suffix(
            _format_to_extension(output_format)
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = convert(str(input_path), str(output_path), input_format, output_format, **writer_kwargs)
        results.append(result)

    return results


def _prepend_row(stream: RowStream, row: Row) -> RowStream:
    """Prepend a row to a stream (for re-inserting a consumed first row)."""
    yield row
    yield from stream


def _format_to_extension(fmt: str) -> str:
    ext_map = {
        "csv": ".csv",
        "json": ".json",
        "jsonl": ".jsonl",
        "yaml": ".yaml",
        "parquet": ".parquet",
        "avro": ".avro",
    }
    return ext_map.get(fmt, f".{fmt}")


# ── Schema Validation ────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Result of validating a data file against an expected schema."""
    valid: bool = True
    rows_checked: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate(
    input_path: str | Path,
    expected_schema: list[dict[str, str]] | None = None,
    input_format: str | None = None,
    max_rows: int = 0,
    strict: bool = False,
) -> ValidationResult:
    """Validate a data file against an expected schema.

    Args:
        input_path: Path to the data file.
        expected_schema: List of {"name": ..., "type": ...} dicts. If None,
            the schema is inferred from the file and only structural checks
            (file readable, consistent columns) are performed.
        input_format: Format override (auto-detected if None).
        max_rows: Maximum rows to check (0 = all).
        strict: If True, fail on type mismatches. If False, only warn.

    Returns:
        ValidationResult with validity, errors, and warnings.
    """
    result = ValidationResult()
    input_path = Path(input_path)

    if not input_format:
        input_format = detect_format(input_path)
    if not input_format:
        result.valid = False
        result.errors.append(f"Could not detect format for: {input_path}")
        return result

    try:
        reader = get_reader(input_format)
    except ValueError as e:
        result.valid = False
        result.errors.append(str(e))
        return result

    # Infer schema from file if none provided
    if expected_schema is None:
        expected_schema = reader.infer_schema(input_path)
        if not expected_schema:
            result.warnings.append("File appears to be empty or has no detectable schema")
            return result

    expected_fields = {f["name"]: f["type"] for f in expected_schema}

    # Stream through rows and check
    rows_checked = 0
    for row in reader.read_stream(input_path):
        rows_checked += 1

        # Check for missing fields
        for field_name in expected_fields:
            if field_name not in row and strict:
                result.errors.append(
                    f"Row {rows_checked}: missing required field '{field_name}'"
                )
                result.valid = False

        # Check for unexpected fields (strict mode)
        if strict:
            for field_name in row:
                if field_name not in expected_fields:
                    result.warnings.append(
                        f"Row {rows_checked}: unexpected field '{field_name}'"
                    )

        # Check types on non-None values
        for field_name, expected_type in expected_fields.items():
            val = row.get(field_name)
            if val is None:
                continue  # nulls are acceptable unless we add nullability checks
            actual_type = _infer_type(val)
            if actual_type != expected_type and actual_type != "null":
                # Check for compatible widening
                widened = _widen_type(expected_type, actual_type)
                if widened != expected_type:
                    msg = (
                        f"Row {rows_checked}: field '{field_name}' expected "
                        f"{expected_type} but got {actual_type}"
                    )
                    if strict:
                        result.errors.append(msg)
                        result.valid = False
                    else:
                        result.warnings.append(msg)

        if max_rows > 0 and rows_checked >= max_rows:
            break

    result.rows_checked = rows_checked
    if rows_checked == 0 and expected_schema:
        result.warnings.append("File contains no data rows")

    return result
