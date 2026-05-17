# DataMorph CLI

> **Batch data format converter** — stream files over 10GB between CSV, JSON, Parquet, YAML, Avro, and more.

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/datamorph?style=social)](https://github.com/Coding-Dev-Tools/datamorph/stargazers)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![CI](https://github.com/Coding-Dev-Tools/datamorph/actions/workflows/test.yml/badge.svg)](https://github.com/Coding-Dev-Tools/datamorph/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/Coding-Dev-Tools/datamorph/blob/main/LICENSE)
[![Open Source Alternative](https://img.shields.io/badge/Open_Source_Alternative-%E2%87%92-blue?logo=opensourceinitiative)](https://www.opensourcealternative.to/project/datamorph)
[![LibHunt](https://img.shields.io/badge/LibHunt-%E2%87%92-blue?logo=codeigniter)](https://www.libhunt.com/r/Coding-Dev-Tools/datamorph)

> ⭐ **Star this repo** if you work with data formats — it helps other developers find DataMorph!

Part of the [Revenue Holdings](https://coding-dev-tools.github.io/revenueholdings.dev/) developer tool ecosystem.

## Why DataMorph?

Data format conversion shouldn't require a custom script every time. CSV to Parquet for analytics, JSON to YAML for configs, Avro to JSON for debugging — DataMorph handles it all with one command. And for large files, row-by-row streaming means you never run out of memory.

## Features

- **6+ format pairs**: CSV, JSON, JSONL, YAML, Parquet, Avro, Protobuf
- **Streaming**: Row-by-row processing for files >10GB
- **Schema inference**: Auto-detect field types from data
- **Schema validation**: Check data files against expected schemas (CI-friendly)
- **CLI commands**: `convert`, `batch`, `schema`, `validate`, `formats`
- **Batch mode**: Convert entire directories at once

## Installation

```bash
pip install datamorph
```

Or install via Homebrew (macOS/Linux):
```bash
brew tap Coding-Dev-Tools/tap
brew install datamorph
```

Or install via Scoop (Windows):
```bash
scoop bucket add Coding-Dev-Tools https://github.com/Coding-Dev-Tools/scoop-bucket
scoop install datamorph
```

## Quick Start

```bash
# Convert a single file
datamorph convert input.csv output.parquet
datamorph convert input.json output.csv
datamorph convert input.yaml output.json
datamorph convert input.parquet output.csv

# Batch convert all files in a directory
datamorph batch ./csv_data/ ./parquet_data/ --from csv --to parquet --recursive

# Inspect schema
datamorph schema data.parquet
datamorph schema data.csv --json-output

# Validate data against a schema
datamorph validate data.csv                          # structural check
datamorph validate data.csv --schema schema.json     # against expected schema
datamorph validate data.csv --strict --json-output   # strict mode, JSON output (CI)

# Export schema for validation
datamorph schema data.csv --json-output > schema.json

# List supported formats
datamorph formats
```

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | CLI only, 100 conversions/mo |
| **Pro** | $12/mo | Unlimited conversions, streaming, batch mode, all formats |
| **Suite** | $49/mo | All 10 Revenue Holdings tools |

Get a license key at [revenueholdings.dev/pricing](https://coding-dev-tools.github.io/revenueholdings.dev/pricing.html).

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT — [Revenue Holdings](https://coding-dev-tools.github.io/revenueholdings.dev/)


## Install via npm

```bash
npm install -g datamorph-cli
```

Then run: `datamorph --help`
