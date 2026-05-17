# DataMorph CLI

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/datamorph?style=social)](https://github.com/Coding-Dev-Tools/datamorph/stargazers)

**Batch data format converter** with streaming support for files over 10GB.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/datamorph/)
[![CI](https://github.com/Coding-Dev-Tools/datamorph/actions/workflows/test.yml/badge.svg)](https://github.com/Coding-Dev-Tools/datamorph/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/datamorph)](https://pypi.org/project/datamorph/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/Coding-Dev-Tools/datamorph/blob/main/LICENSE)
[![Open Source Alternative](https://img.shields.io/badge/Open_Source_Alternative-%E2%87%92-blue?logo=opensourceinitiative)](https://www.opensourcealternative.to/project/datamorph)
[![LibHunt](https://img.shields.io/badge/LibHunt-%E2%87%92-blue?logo=codeigniter)](https://www.libhunt.com/r/Coding-Dev-Tools/datamorph)
[![Awesome Python](https://img.shields.io/badge/Awesome_Python-%E2%87%92-blue?logo=python)](https://github.com/uhub/awesome-python)

Part of the [Revenue Holdings](https://coding-dev-tools.github.io/revenueholdings.dev/) developer tool ecosystem.

## Why DataMorph?

Data format conversion shouldn't require a custom script every time. CSV to Parquet for analytics, JSON to YAML for configs, Avro to JSON for debugging — DataMorph handles it all with one command. And for large files, row-by-row streaming means you never run out of memory.

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

# List supported formats
datamorph formats
```

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | CLI only, 100 conversions/mo |
| **Pro** | $12/mo | Unlimited conversions, streaming, batch mode, all formats |
| **Suite** | $49/mo | All 8 Revenue Holdings tools |

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
