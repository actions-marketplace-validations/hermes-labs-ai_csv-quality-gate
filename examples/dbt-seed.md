# Recipe: gate dbt seeds before `dbt seed`

dbt loads the CSV files in a project's `seeds/` directory into the warehouse
with `dbt seed`. A seed with a repeated key or a blank label loads without
complaint and only surfaces later, in a failing model or a wrong join. This
recipe runs csv-quality-gate on the seed files first and stops on `warn` or
`fail`.

It uses the existing custom-profile mechanism only: a small TOML file names the
columns and thresholds, and the gate applies its usual checks (required
columns, empty cells, duplicate rate) with bounded line-number evidence. It does
not read `dbt_project.yml`, infer seed schemas, or compare values against the
warehouse.

## Files

- [`dbt-seed/csv-quality-gate.toml`](dbt-seed/csv-quality-gate.toml) — a `seed`
  profile: `country_code` and `country_name` are required, any empty cell is a
  warning (10% or more fails), and any repeated `country_code` fails.
- [`dbt-seed/seeds/country_codes.csv`](dbt-seed/seeds/country_codes.csv) — a
  clean seed (passes).
- [`dbt-seed/seeds-broken/country_codes.csv`](dbt-seed/seeds-broken/country_codes.csv)
  — the same seed with a repeated code and an empty name (fails).

## Try it from a checkout

```bash
pip install csv-quality-gate      # or, from the repository root: pip install -e .
cd examples/dbt-seed
```

Clean seed, exit code `0`:

```bash
csv-quality-gate check seeds/country_codes.csv --config csv-quality-gate.toml --profile seed
```

```text
csv-quality-gate: PASS
file: seeds/country_codes.csv
profile: seed
config: csv-quality-gate.toml
rows: 8
```

Broken seed, exit code `2`:

```bash
csv-quality-gate check seeds-broken/country_codes.csv --config csv-quality-gate.toml --profile seed
```

```text
csv-quality-gate: FAIL
file: seeds-broken/country_codes.csv
profile: seed
config: csv-quality-gate.toml
rows: 8
  ERROR: empty rate for country_name is 12%, exceeds fail threshold 10%
    evidence: column=country_name affected=1 row at line(s) 6
  ERROR: duplicate rate 12% exceeds fail threshold 0%
    evidence: column=country_code affected=1 row at line(s) 5
```

## Wire it into a dbt project

Copy `csv-quality-gate.toml` next to `dbt_project.yml`, change the column names
to match your seed, and run the gate before the load:

```bash
csv-quality-gate check seeds/*.csv --config csv-quality-gate.toml --profile seed && dbt seed
```

A profile's required columns apply to every file in one `check` call, so seeds
with different columns need one profile each (`[profiles.country_codes]`,
`[profiles.employee_ids]`, ...) and one call per group.

As a pre-commit hook, limit the hook to the seeds directory:

```yaml
repos:
  - repo: https://github.com/hermes-labs-ai/csv-quality-gate
    rev: v0.3.1
    hooks:
      - id: csv-quality-gate
        args: [--config, csv-quality-gate.toml, --profile, seed]
        files: ^seeds/.*\.csv$
```

In GitHub Actions, run the composite Action (one file per step) before the step
that calls `dbt seed`:

```yaml
- uses: hermes-labs-ai/csv-quality-gate@v0.3.1
  with:
    csv-path: seeds/country_codes.csv
    profile: seed
    config: csv-quality-gate.toml
- run: dbt seed
```

TOML configuration needs Python 3.11+; on 3.10, use a `.json` file with the
same keys.
