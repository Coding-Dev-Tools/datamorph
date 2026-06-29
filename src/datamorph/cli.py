"""DataMorph CLI — Batch data format converter."""

from __future__ import annotations

import json
import sys
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .converters import (
    convert,
    convert_batch,
    detect_format,
    supported_formats,
    validate,
)

console = Console()
err_console = Console(stderr=True)


@click.group()
@click.version_option(__version__, prog_name="datamorph")
def cli() -> None:
    """DataMorph — Convert between data formats with streaming support.

    Supports CSV, JSON, JSONL, YAML, Parquet, Avro (and Protobuf with
    optional protobuf package).

    Also try: batch, schema, formats, validate
    """


# ── convert ──────────────────────────────────────────────────────────


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--input-format", "-if", default=None, help="Input format (auto-detected from extension if omitted)")
@click.option("--output-format", "-of", default=None, help="Output format (auto-detected from extension if omitted)")
@click.option("--pretty", "-p", is_flag=True, help="Pretty-print JSON output")
@click.option("--csv-delimiter", default=",", help="CSV delimiter (default: comma)")
def convert_cmd(
    input: str,
    output: str,
    input_format: str | None,
    output_format: str | None,
    pretty: bool,
    csv_delimiter: str,
) -> None:
    """Convert INPUT file to OUTPUT format."""
    writer_kwargs: dict[str, Any] = {}
    if pretty:
        writer_kwargs["indent"] = 2
    if csv_delimiter != ",":
        writer_kwargs["delimiter"] = csv_delimiter

    result = convert(
        input,
        output,
        input_format=input_format,
        output_format=output_format,
        **writer_kwargs,
    )

    if result.errors:
        for err in result.errors:
            err_console.print(f"[red]ERROR:[/red] {err}")
        sys.exit(1)

    console.print(
        f"[green]✓[/green] Converted [bold]{result.rows_written}[/bold] rows "
        f"from [cyan]{result.input_format}[/cyan] → [magenta]{result.output_format}[/magenta]"
    )
    console.print(f"  Input:  {input}")
    console.print(f"  Output: {output}")


# ── batch ────────────────────────────────────────────────────────────


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("output_dir", type=click.Path(file_okay=False))
@click.option("--from", "-f", "from_format", required=True, help="Source format")
@click.option("--to", "-t", "to_format", required=True, help="Target format")
@click.option("--pattern", default="*", help="File glob pattern (default: all files)")
@click.option("--recursive", "-r", is_flag=True, help="Search subdirectories recursively")
@click.option("--csv-delimiter", default=",", help="CSV delimiter")
def batch_cmd(
    input_dir: str,
    output_dir: str,
    from_format: str,
    to_format: str,
    pattern: str,
    recursive: bool,
    csv_delimiter: str,
) -> None:
    """Batch convert all matching files in INPUT_DIR to OUTPUT_DIR."""
    writer_kwargs: dict[str, Any] = {}
    if csv_delimiter != ",":
        writer_kwargs["delimiter"] = csv_delimiter

    results = convert_batch(
        input_dir,
        output_dir,
        from_format,
        to_format,
        pattern=pattern,
        recursive=recursive,
        **writer_kwargs,
    )

    success = [r for r in results if not r.errors]
    failed = [r for r in results if r.errors]

    console.print("\n[bold]Batch Conversion Complete[/bold]")
    console.print(f"  Files: {len(success)} converted, {len(failed)} failed")

    if failed:
        for r in failed:
            for err in r.errors:
                err_console.print(f"  [red]ERROR:[/red] {err}")

    total_rows = sum(r.rows_written for r in success)
    console.print(f"  Total rows written: [bold]{total_rows}[/bold]")

    if failed:
        sys.exit(1)


# ── schema ───────────────────────────────────────────────────────────


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--format", "-f", "fmt", default=None, help="File format (auto-detected if omitted)")
@click.option("--json-output", "-j", is_flag=True, help="Output schema as JSON")
@click.option("--sample", default=100, type=int, help="Number of rows to sample for schema inference")
def schema_cmd(
    file: str,
    fmt: str | None,
    json_output: bool,
    sample: int,
) -> None:
    """Infer and display schema of a data file."""
    from .converters import get_reader

    if not fmt:
        fmt = detect_format(file)
    if not fmt:
        err_console.print(f"[red]Could not detect format for: {file}[/red]")
        sys.exit(1)

    reader = get_reader(fmt)
    schema = reader.infer_schema(file, sample_size=sample)

    if json_output:
        console.print(json.dumps(schema, indent=2))
        return

    table = Table(title=f"Schema: {file} ({fmt})")
    table.add_column("Field", style="cyan")
    table.add_column("Type", style="green")

    for field in schema:
        table.add_row(field["name"], field["type"])

    console.print(f"\nDetected format: [bold]{fmt}[/bold]")
    console.print(table)
    console.print(f"[dim]Inferred from {sample}+ rows[/dim]")


# ── formats ──────────────────────────────────────────────────────────


@cli.command(name="formats")
def formats_cmd() -> None:
    """List all supported data formats and their capabilities."""
    table = Table(title="Supported Data Formats")
    table.add_column("Format", style="cyan")
    table.add_column("Read", style="green")
    table.add_column("Write", style="green")
    table.add_column("Streaming", style="yellow")

    from .converters import _READERS, _WRITERS

    all_formats = supported_formats()
    for fmt in all_formats:
        can_read = "yes" if fmt in _READERS else ""
        can_write = "yes" if fmt in _WRITERS else ""
        can_stream = "yes" if fmt in ("csv", "jsonl", "avro") else ""
        table.add_row(fmt, can_read, can_write, can_stream)

    console.print(table)


# ── validate ─────────────────────────────────────────────────────────


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--format", "-f", "fmt", default=None, help="File format (auto-detected if omitted)")
@click.option(
    "--schema", "-s", "schema_file", default=None,
    type=click.Path(exists=True), help="JSON schema file to validate against",
)
@click.option("--strict", is_flag=True, help="Strict mode: fail on type mismatches and missing fields")
@click.option("--max-rows", default=0, type=int, help="Maximum rows to validate (0 = all)")
@click.option("--json-output", "-j", is_flag=True, help="Output validation result as JSON")
def validate_cmd(
    file: str,
    fmt: str | None,
    schema_file: str | None,
    strict: bool,
    max_rows: int,
    json_output: bool,
) -> None:
    """Validate a data file against an expected schema.

    If no schema file is provided, the schema is inferred from the data
    and only structural checks (consistent columns, readable format) are
    performed. Use --strict to fail on type mismatches.

    To create a schema file, use: datamorph schema data.csv --json-output > schema.json
    """
    # Load expected schema if provided
    expected_schema = None
    if schema_file:
        with open(schema_file, "r", encoding="utf-8") as f:
            expected_schema = json.load(f)

    result = validate(
        file,
        expected_schema=expected_schema,
        input_format=fmt,
        max_rows=max_rows,
        strict=strict,
    )

    if json_output:
        output = {
            "valid": result.valid,
            "rows_checked": result.rows_checked,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        console.print(json.dumps(output, indent=2))
    else:
        if result.valid:
            console.print(f"[green]✓ VALID[/green] — {result.rows_checked} rows checked")
        else:
            console.print(f"[red]✗ INVALID[/red] — {result.rows_checked} rows checked")

        if result.errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for err in result.errors:
                console.print(f"  [red]•[/red] {err}")

        if result.warnings:
            console.print("\n[bold yellow]Warnings:[/bold yellow]")
            for warn in result.warnings:
                console.print(f"  [yellow]•[/yellow] {warn}")

    if not result.valid:
        sys.exit(1)


if __name__ == "__main__":
    cli()
