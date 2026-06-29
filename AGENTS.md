# datamorph

## Purpose
Batch data format converter — stream files between CSV, JSON, Parquet, YAML, Avro, and more. Includes schema inference and validation.

## Build & Test Commands
- Install: `pip install -e .` or `pip install datamorph-cli`
- Test: `pytest tests/` (or `python -m pytest tests/ -v --tb=short`)
- Lint: `ruff check .`
- Build: `pip install build twine && python -m build && twine check dist/*`
- CLI check: `datamorph --version && datamorph --help && datamorph formats`

## Architecture
Key directories:
- `src/datamorph/` — Main package (CLI, converters, schema inference, validation)
- `tests/` — Test suite
- `.github/workflows/` — CI/CD (auto-code-review.yml, ci.yml, pages.yml, publish.yml)
- `dist/` — Built distributions

## Conventions
- Language: Python 3.10+
- Test framework: pytest
- CI: GitHub Actions (lint + test matrix: Python 3.10, 3.11, 3.12, 3.13)
- Linting: ruff
- Build system: hatchling
- Package layout: src/ layout
- Dependencies: click, rich, faker, flask, requests, jsonschema, werkzeug, pandas, pyarrow
- CLI entry point: datamorph.cli:cli
- Default branch: master