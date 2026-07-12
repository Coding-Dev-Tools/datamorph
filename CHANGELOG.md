# Changelog

## [Unreleased]

### Fixed
- Fix ruff F402 lint error by renaming shadowed loop variable (`field` → `s_field`)
  in `AvroWriter` schema iteration.

### Removed
- Remove dead `npm-publish.yml` GitHub Actions workflow (datamorph is a Python CLI
  tool, has no `package.json`, and the workflow would fail on every release).

## [0.1.1] — 2026-05-18

### Fixed
- CSV reader now respects custom delimiter (`--csv-delimiter` / `csv_delimiter`).
  Previously the delimiter was only applied to CSV output; input reads always
  used comma, producing incorrect field parsing for pipe/tab-delimited files.
- `get_reader()` now accepts `**kwargs`, enabling format-specific reader options.
- `convert()` passes delimiter to the reader when input format is CSV.

### Added
- CLI tests for `validate --format` and `validate --format --schema` combinations.
- Roundtrip test for pipe-delimited CSV read→write→read cycle.

### Changed
- Version bumped to 0.1.1 (bugfix release).

## [0.1.0] — Initial Release

### Added
- CLI commands: `convert`, `batch`, `schema`, `validate`, `formats`.
- Format support: CSV, JSON, JSONL, YAML, Parquet, Avro (Protobuf optional).
- Streaming row-by-row conversion for CSV, JSONL, and Avro.
- Schema inference and validation with strict mode.
- Batch directory conversion with recursive glob support.
- Rich terminal output with progress feedback.
- CI/CD integration with exit-code-based validation.
