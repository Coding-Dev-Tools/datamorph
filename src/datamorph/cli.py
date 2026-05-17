"""DataMorph CLI — Batch data format converter."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from . import __version__
try:
    from revenueholdings_core import check_license_and_limit
except ImportError:
    check_license_and_limit = None
from .converters import (
    convert,
    convert_batch,
    supported_formats,
    detect_format,
)

console = Console()
err_console = Console(stderr=True)


@click.group()
@click.version_option(__version__, prog_name="datamorph")
def cli() -> None:
    """DataMorph — Convert between data formats with streaming support.

    Supports CSV, JSON, JSONL, YAML, Parquet, Avro (and Protobuf with
    optional protobuf package).

    Examples:

        datamorph convert input.csv output.parquet

        datamorph convert input.csv output.json --pretty

        datamorph batch ./data/ --from csv --to parquet

        datamorph schema input.parquet
    """
    # License gate
    if check_license_and_limit:
        ok, _claims, msg = check_license_and_limit("datamorph")
    else:
        ok, msg = True, ""  # License check skipped (dev/CI mode)
    if not ok:
        from rich.console import Console
        Console(stderr=True).print(f"[red]Access denied:[/red] {msg}")
        raise SystemExit(1)


# ── convert ──────────────────────────────────────────────────────────


@cli.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--input-format", "-if", default=None, help="Input format (auto-detected from extension if omitted)")
@click.option("--output-format", "-of", default=None, help="Output format (auto-detected from extension if omitted)")
@click.option("--pretty", "-p", is_flag=True, help="Pretty-print JSON output")
@click.option("--csv-delimiter", default=",", help="CSV delimiter (default: comma)")
@click.option("--stream", is_flag=True, help="Use streaming mode (row-by-row, lower memory)")
def convert_cmd(
    input: str,
    output: str,
    input_format: str | None,
    output_format: str | None,
    pretty: bool,
    csv_delimiter: str,
    stream: bool,
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
        stream=stream,
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

    console.print(f"\n[bold]Batch Conversion Complete[/bold]")
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
        can_read = "✓" if fmt in _READERS else ""
        can_write = "✓" if fmt in _WRITERS else ""
        can_stream = "✓" if fmt in ("csv", "jsonl", "avro") else ""
        table.add_row(fmt, can_read, can_write, can_stream)

    console.print(table)


if __name__ == "__main__":
    cli()
