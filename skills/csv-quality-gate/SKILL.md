---
name: csv-quality-gate
description: Run a CSV preflight quality check with the csv-quality-gate CLI and report pass, warn, or fail with line-number evidence. Trigger when the user asks to check, validate, lint, or gate one or more named CSV files before a pipeline, ETL, enrichment, outreach, or scoring run.
---

csv-quality-gate checks CSV files for missing required columns, empty files,
empty critical cells, duplicate rates, and (outreach profile or a custom
config) suspicious values. It reads local files only, makes no model calls,
and sends no network requests
(https://github.com/hermes-labs-ai/csv-quality-gate).

1. Pick a runner: if `csv-quality-gate --help` works, use the bare
   `csv-quality-gate` command below. Otherwise use
   `uvx csv-quality-gate==0.3.0` (zero-install, no PATH changes), or
   `pipx install csv-quality-gate==0.3.0` if the user wants it installed
   persistently. Keep the exact version pin so neither fetches an unreviewed
   newer release, and keep using the runner you picked for every step.
2. Only check files the user named or clearly pointed at. Choose the profile:
   - `generic` (default): requires a `company` column.
   - `outreach`: contact lists with `company` and `person_name`.
   - If the CSV uses other column names and the project has a config file
     (for example `csv-quality-gate.toml`), pass `--config FILE --profile NAME`.
     Do not write or loosen a config just to make a file pass; ask first.
3. Run with JSON output so the result is unambiguous:
   ```
   csv-quality-gate check data/leads.csv --profile generic --json
   ```
   Several paths may be given in one call; JSON output is then an array and
   the exit code is the worst status.
4. Read the result, not just the exit code:
   - exit `0` / `"status": "pass"`: no issues found by these checks.
   - exit `1` / `"status": "warn"`: warnings only.
   - exit `2` / `"status": "fail"`: at least one blocking issue, or the file is
     missing, not UTF-8, the profile is unknown, or the config is invalid.
   Each issue has `severity` and `message`; row-backed issues add
   `evidence: {column, total, rows[]}` where `rows` are physical line numbers
   (header is line 1), capped by `--max-examples` (default 5).
5. Report to the user, per file: the status, the profile used, the row count,
   and each issue with its affected column, count, and line numbers.

Constraints:
- `pass` means these heuristic shape checks found nothing. It does not mean
  the data is correct, complete, or semantically valid; say so if the user
  asks whether the data is "good".
- A result is only as right as the profile. If `fail` comes from a missing
  required column, check whether the wrong profile was chosen before calling
  the data broken.
- Evidence gives line numbers and counts, never cell values. Do not print
  whole rows or sensitive cell contents unless the user asks.
- Do not edit or delete rows in the CSV unless the user asks for that change.
