# Recipe: gate a promptfoo CSV test set before `promptfoo eval`

promptfoo can read test cases from a CSV file (`tests: file://tests.csv` in
`promptfooconfig.yaml`): column headers become prompt variables and the
`__expected` column holds one assertion per row. A duplicated case, a blank
assertion, or a `TODO` left in `__expected` makes an eval spend time and tokens
on rows that cannot tell you anything. This recipe runs csv-quality-gate on the
dataset first and stops on `warn` or `fail`.

It uses the existing custom-profile mechanism only: a small TOML file names the
columns, thresholds, and a placeholder pattern, and the gate applies its usual
checks (required columns, empty cells, duplicate rate, regex noise) with
bounded line-number evidence. It does not parse or run assertions, judge
whether an expected answer is right, or know anything about promptfoo beyond
the file being a CSV.

## Files

- [`promptfoo-dataset/csv-quality-gate.toml`](promptfoo-dataset/csv-quality-gate.toml)
  — a `promptfoo` profile: `question` and `__expected` are required, any empty
  cell is a warning (10% or more fails), any repeated `question` is a warning
  (20% or more fails), and a placeholder assertion such as `TODO`, `TBD`, or
  `FIXME` is a warning (10% or more fails).
- [`promptfoo-dataset/tests.csv`](promptfoo-dataset/tests.csv) — a clean test
  set (passes).
- [`promptfoo-dataset/tests-broken.csv`](promptfoo-dataset/tests-broken.csv) —
  the same set with a repeated question, an empty assertion, and a `TODO`
  placeholder (fails).

## Try it from a checkout

```bash
pip install csv-quality-gate      # or, from the repository root: pip install -e .
cd examples/promptfoo-dataset
```

Clean test set, exit code `0`:

```bash
csv-quality-gate check tests.csv --config csv-quality-gate.toml --profile promptfoo
```

```text
csv-quality-gate: PASS
file: tests.csv
profile: promptfoo
config: csv-quality-gate.toml
rows: 6
```

Broken test set, exit code `2`:

```bash
csv-quality-gate check tests-broken.csv --config csv-quality-gate.toml --profile promptfoo
```

```text
csv-quality-gate: FAIL
file: tests-broken.csv
profile: promptfoo
config: csv-quality-gate.toml
rows: 6
  ERROR: empty rate for __expected is 17%, exceeds fail threshold 10%
    evidence: column=__expected affected=1 row at line(s) 4
  WARNING: duplicate rate 17% exceeds warning threshold 0%
    evidence: column=question affected=1 row at line(s) 3
  ERROR: suspicious __expected rate is 17%
    evidence: column=__expected affected=1 row at line(s) 5
```

## Wire it into a promptfoo project

Copy `csv-quality-gate.toml` next to `promptfooconfig.yaml`, rename `question`
to whichever variable column your prompts use, and run the gate before the
eval. The promptfoo side is unchanged; only the `tests:` line matters here:

```yaml
# promptfooconfig.yaml
tests: file://tests.csv
```

```bash
csv-quality-gate check tests.csv --config csv-quality-gate.toml --profile promptfoo && promptfoo eval
```

As a pre-commit hook, limit the hook to the dataset:

```yaml
repos:
  - repo: https://github.com/hermes-labs-ai/csv-quality-gate
    rev: v0.3.1
    hooks:
      - id: csv-quality-gate
        args: [--config, csv-quality-gate.toml, --profile, promptfoo]
        files: ^tests\.csv$
```

In GitHub Actions, run the composite Action before the step that calls
`promptfoo eval`:

```yaml
- uses: hermes-labs-ai/csv-quality-gate@v0.3.1
  with:
    csv-path: tests.csv
    profile: promptfoo
    config: csv-quality-gate.toml
- run: npx promptfoo@latest eval
```

TOML configuration needs Python 3.11+; on 3.10, use a `.json` file with the
same keys.
