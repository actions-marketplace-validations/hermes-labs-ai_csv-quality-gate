# Changelog

## Unreleased

- The repository root is now a portable Agent Plugin (`plugin.json`, Agent
  Plugins 1.0.0) with Claude Code, Codex CLI, and Gemini CLI manifests that all
  resolve one skill, `skills/csv-quality-gate/SKILL.md`. Runtime code is
  unchanged.

- Added an opt-in composite Action job summary with status, profile, row count,
  issue counts, and an opt-in bounded evidence-column list. The JSON receipt and
  CLI exit codes are unchanged; the Action also exposes an additive
  `tool-version` output.
- The composite Action declares `author` and Marketplace `branding` in
  `action.yml`; inputs, outputs, and behavior are unchanged.
- Added ecosystem recipes with one passing and one failing fixture each:
  `examples/dbt-seed.md` (gate `seeds/*.csv` before `dbt seed`) and
  `examples/promptfoo-dataset.md` (gate a CSV test set before `promptfoo eval`).
- Documented the release and Marketplace-listing steps in `CONTRIBUTING.md`.

## 0.3.0 - 2026-09-05

- Added project-specific profiles: `check --config FILE --profile NAME` loads
  TOML (Python 3.11+) or JSON profiles declared under `[profiles]`. Profiles are
  data only (column names, thresholds, regex strings) and may `extends` a
  built-in. Invalid files are rejected with a precise message and a normal
  `fail` receipt. Built-in profiles and their behavior are unchanged.
- Added bounded evidence to issues: each empty-rate, duplicate-rate, and
  suspicious-value issue now carries the affected column, the count of affected
  rows, and up to `--max-examples` (default 5) physical line numbers. Cell
  values are never emitted. JSON issues gain an optional `evidence` object;
  issues without evidence keep the 0.2.0 shape.
- The `check` command accepts several CSV paths; text output prints one block
  per file, JSON output becomes an array, and the exit code is the worst status.
- Added a pre-commit hook (`.pre-commit-hooks.yaml`, id `csv-quality-gate`)
  so the same gate runs on staged CSV files before commit.
- The composite Action accepts an optional `config` input; `csv-path` and
  `profile` behave exactly as before.
- Exposed `suspicious_warning_rate` and `suspicious_fail_rate` on `Profile`
  (defaults keep the previous fixed 10% / 30%). Public API additions:
  `Profile`, `Evidence`, `ConfigError`, `load_config`, and keyword-only
  `profile`, `max_examples`, and `config` parameters on `validate_csv`.
- CI now tests Python 3.10 and 3.11 and exercises the pre-commit hook.
- Fixed: a file that is not valid UTF-8 now yields a normal `fail` receipt
  instead of a traceback (which the Action previously reported as `warn`).
- Fixed: a header with surrounding whitespace (for example `company `) is now
  matched and read as that column instead of being counted as fully empty.
- Fixed: a header-only file no longer adds a false `missing required column`
  error next to `csv has no data rows`; the status is still `fail`.
- A warning or fail rate of `0.0` now means "any occurrence"; a check with no
  affected rows never raises an issue. Built-in thresholds are unaffected.
- Options may appear between CSV paths (`check a.csv --json b.csv`).

## 0.2.0 - 2026-09-05

- Added a root composite GitHub Action with typed CSV path and profile inputs.
- The Action writes a JSON receipt and exposes its status and receipt path while
  preserving the CLI's pass/warn/fail exit codes.

## 0.1.2 - 2026-08-04

- Clarified the README, limitations, and outreach-profile heuristic without
  changing validation behavior.
- Added canonical package links and modernized license metadata.
- Added a tag-bound OIDC Trusted Publishing workflow for PyPI.

## 0.1.1 - 2026-05-30

- Added citation and Zenodo metadata.
- Aligned the public repository and Hermes Labs identity surfaces.

## 0.1.0

- Initial public release.
- Added `generic` and `outreach` validation profiles.
- Added text and JSON output modes.
- Added fixture-based tests for pass, warning, and fail cases.
