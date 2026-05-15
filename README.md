# DataMorph CLI

Batch data format converter with streaming support for large files.

## Features

- **6+ format pairs**: CSV, JSON, JSONL, YAML, Parquet, Avro, Protobuf
- **Streaming**: Row-by-row processing for files >10GB
- **Schema inference**: Auto-detect field types from data
- **CLI commands**: `convert`, `batch`, `schema`, `formats`
- **Batch mode**: Convert entire directories at once

## Installation

```bash
pip install datamorph
```

## Usage

### Convert a single file

```bash
# CSV to Parquet
datamorph convert input.csv output.parquet

# JSON to CSV
datamorph convert input.json output.csv

# YAML to JSON
datamorph convert input.yaml output.json

# Parquet to CSV
datamorph convert input.parquet output.csv
```

### Batch convert all files in a directory

```bash
datamorph batch ./csv_data/ ./parquet_data/ --from csv --to parquet --recursive
```

### Inspect schema

```bash
datamorph schema data.parquet
datamorph schema data.csv --json-output
```

### List supported formats

```bash
datamorph formats
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
