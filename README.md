# DataMorph CLI

[![GitHub stars](https://img.shields.io/github/stars/Coding-Dev-Tools/datamorph?style=social)](https://github.com/Coding-Dev-Tools/datamorph/stargazers)

**Batch data format converter** — stream files over 10GB between CSV, JSON, Parquet, YAML, Avro, and more.

> ⭐ **Star this repo** if you work with data files — it helps other devs find DataMorph!

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![CI](https://github.com/Coding-Dev-Tools/datamorph/actions/workflows/ci.yml/badge.svg)](https://github.com/Coding-Dev-Tools/datamorph/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/Coding-Dev-Tools/datamorph/blob/main/LICENSE)
[![Open Source Alternative](https://img.shields.io/badge/Open_Source_Alternative-%E2%87%92-blue?logo=opensourceinitiative)](https://www.opensourcealternative.to/project/datamorph)
|[![LibHunt](https://img.shields.io/badge/LibHunt-%E2%87%92-blue?logo=codeigniter)](https://www.libhunt.com/r/Coding-Dev-Tools/datamorph)
|[![PyPI](https://img.shields.io/pypi/v/datamorph-cli)](https://pypi.org/project/datamorph-cli/)

> ⭐ **Star this repo** if you work with data formats

Part of the [Revenue Holdings](https://coding-dev-tools.github.io/devforge/) developer tool ecosystem.

## Why DataMorph?

Every data engineer writes throwaway scripts to convert CSV to Parquet, JSON to YAML, or Avro to JSON. DataMorph replaces all of them with one CLI command. It streams row-by-row so files over 10GB fit in memory. It infers schemas automatically so you don't hand-write them. And it validates data against schemas in CI so malformed data never reaches production.

**Before DataMorph:**
```python
# One-off script #47 you'll never find again
import pandas as pd
df = pd.read_csv('huge_file.csv')  # OOM on 5GB+
df.to_parquet('output.parquet')
```

**After DataMorph:**
```bash
datamorph convert huge_file.csv output.parquet  # Streams, no OOM
```

## Use Cases

| Who | What they do with DataMorph |
|-----|-----------------------------|
| **Data engineers** | Convert CSV exports to Parquet for Athena/BigQuery analytics |
| **Backend devs** | Transform JSON API responses to CSV for reporting |
| **DevOps teams** | Validate data file schemas in CI before deployment |
| **ML engineers** | Batch-convert training data between formats (JSONL → Parquet) |
| **QA teams** | Inspect and validate data file schemas without writing code |

## Features

- **6+ format pairs**: CSV ↔ JSON ↔ JSONL ↔ YAML ↔ Parquet ↔ Avro ↔ Protobuf
- **Streaming**: Row-by-row processing for files >10GB — never OOM
- **Schema inference**: Auto-detect field types from data, export as JSON
- **Schema validation**: Check data files against expected schemas (CI-friendly, exit codes)
- **Batch mode**: Convert entire directories at once with `--recursive`
- **CLI commands**: `convert`, `batch`, `schema`, `validate`, `formats`

## Installation

**pip (Python):**
```bash
pip install git+https://github.com/Coding-Dev-Tools/datamorph.git
```

**npm (Node.js wrapper — publishing pending):**
```bash
# Not yet available — install via pip instead
```
Then run: `datamorph --help`

**Homebrew (macOS/Linux):**
```bash
brew tap Coding-Dev-Tools/tap
brew install datamorph
```

**Scoop (Windows):**
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

## CI/CD Integration

DataMorph's `validate` command exits with code 1 on schema mismatches — perfect for CI pipelines:

```yaml
# GitHub Actions example
- name: Validate data schemas
  run: |
    datamorph validate data/events.csv --schema schemas/events.json --strict
    datamorph validate data/users.json --schema schemas/users.json --strict
```

```bash
# Generic CI — fail on schema drift
datamorph validate data.csv --schema schema.json || echo "Schema mismatch detected!"
```

```bash
# Auto-convert data files as a build step
datamorph batch ./raw_data/ ./processed/ --from csv --to parquet
```

## Alternatives Comparison

| Feature | DataMorph | pandas | csvkit | frictionless |
|---------|-----------|--------|--------|-------------|
| CSV → Parquet | ✅ | ✅ | ❌ | ✅ |
| Streaming >10GB | ✅ | ❌ (OOM) | ❌ | ✅ |
| Schema validation | ✅ | ❌ | ❌ | ✅ |
| Batch directory convert | ✅ | ❌ | ❌ | ❌ |
| 6+ format pairs | ✅ | ✅ (with libs) | ❌ | ✅ |
| CI exit codes | ✅ | ❌ | ❌ | ✅ |
| Zero-config | ✅ | ❌ | ✅ | ❌ |
| Single binary install | ✅ | ❌ | ✅ | ❌ |

**DataMorph vs pandas**: pandas loads the entire file into memory. DataMorph streams row-by-row — no OOM on large files, no DataFrame boilerplate.

**DataMorph vs csvkit**: csvkit only handles CSV. DataMorph supports 6+ formats including Parquet and Avro.

**DataMorph vs frictionless**: frictionless is a framework with a Python API. DataMorph is a zero-config CLI — `pip install` and go.

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | CLI only, 100 conversions/mo |
| **Pro** | $12/mo | Unlimited conversions, streaming, batch mode, all formats |
| **Suite** | $49/mo ($39/mo annual) | All 11 Revenue Holdings tools |

Get a license key at [revenueholdings.dev/pricing](https://coding-dev-tools.github.io/devforge/pricing.html).

---

<p align="center">
  <sub>Part of <a href="https://coding-dev-tools.github.io/devforge/">Revenue Holdings</a> — a suite of 11 developer CLI tools built by autonomous AI agents. Also check out <a href="https://github.com/Coding-Dev-Tools/configdrift">ConfigDrift</a> (config drift detection), <a href="https://github.com/Coding-Dev-Tools/schemaforge">SchemaForge</a> (ORM/schema conversion), <a href="https://github.com/Coding-Dev-Tools/envault">Envault</a> (env sync/secret rotation), <a href="https://github.com/Coding-Dev-Tools/api-contract-guardian">API Contract Guardian</a> (breaking change detection), <a href="https://github.com/Coding-Dev-Tools/apighost">APIGhost</a> (mock servers), <a href="https://github.com/Coding-Dev-Tools/deploydiff">DeployDiff</a> (infrastructure diffs), <a href="https://github.com/Coding-Dev-Tools/json2sql">json2sql</a> (JSON → SQL), <a href="https://github.com/Coding-Dev-Tools/click-to-mcp">click-to-mcp</a> (CLI → MCP server), and <a href="https://github.com/Coding-Dev-Tools/deadcode">DeadCode</a> (dead code cleanup).</sub>
</p>

## License

MIT — [Revenue Holdings](https://coding-dev-tools.github.io/devforge/)
