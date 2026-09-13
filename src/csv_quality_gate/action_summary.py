"""Render the opt-in GitHub Actions summary from an existing JSON receipt."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

_MARKDOWN_ESCAPES = frozenset("\\`*_{}[]<>()#+-.!|")
MAX_DYNAMIC_VALUE_CHARS = 120
MAX_EVIDENCE_COLUMNS = 8
MAX_SUMMARY_CHARS = 4_096
_TRUNCATION_MARKER = "… (truncated)"


def _markdown_text(value: object) -> str:
    """Return one safe table-cell value without allowing Markdown injection."""
    text = str(value).replace("\r", " ").replace("\n", " ")
    if len(text) > MAX_DYNAMIC_VALUE_CHARS:
        text = text[:MAX_DYNAMIC_VALUE_CHARS] + _TRUNCATION_MARKER
    return "".join(
        f"\\{character}" if character in _MARKDOWN_ESCAPES else character
        for character in text
    )


def render_summary(
    receipt: dict[str, Any], *, include_columns: bool = False, tool_version: str = "unknown"
) -> str:
    """Return a value-only summary that deliberately omits paths and issue messages."""
    issues = receipt.get("issues", [])
    if not isinstance(issues, list):
        raise ValueError("receipt issues must be a list")

    error_count = sum(
        isinstance(issue, dict) and issue.get("severity") == "error" for issue in issues
    )
    warning_count = sum(
        isinstance(issue, dict) and issue.get("severity") == "warning" for issue in issues
    )
    rows = [
        ("Tool", f"csv-quality-gate {tool_version}"),
        ("Status", receipt["status"]),
        ("Profile", receipt["profile"]),
        ("Rows", receipt["rows"]),
        ("Issues", len(issues)),
        ("Errors", error_count),
        ("Warnings", warning_count),
    ]
    if include_columns:
        columns: list[str] = []
        for issue in issues:
            evidence = issue.get("evidence") if isinstance(issue, dict) else None
            column = evidence.get("column") if isinstance(evidence, dict) else None
            if (
                isinstance(column, str)
                and column not in columns
                and len(columns) < MAX_EVIDENCE_COLUMNS
            ):
                columns.append(column)
        if columns:
            rows.extend(("Evidence column", column) for column in columns)

    return _bounded_summary(rows)


def _bounded_summary(rows: list[tuple[str, object]]) -> str:
    """Keep the job summary bounded even if a receipt was externally edited."""
    summary = _table(rows)
    if len(summary) <= MAX_SUMMARY_CHARS:
        return summary

    kept: list[tuple[str, object]] = []
    for row in rows:
        candidate = _table([*kept, row, ("Notice", "Additional fields truncated")])
        if len(candidate) > MAX_SUMMARY_CHARS:
            return _table([*kept, ("Notice", "Additional fields truncated")])
        kept.append(row)
    return summary


def _table(rows: list[tuple[str, object]]) -> str:
    lines = ["## CSV quality gate summary", "", "| Field | Value |", "| --- | --- |"]
    lines.extend(f"| {label} | {_markdown_text(value)} |" for label, value in rows)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a safe CSV quality gate Action summary")
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--include-columns", action="store_true")
    parser.add_argument("--tool-version", required=True)
    args = parser.parse_args(argv)

    receipt = json.loads(args.receipt.read_text())
    if not isinstance(receipt, dict):
        raise ValueError("Action receipt must be a JSON object")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        raise RuntimeError("GITHUB_STEP_SUMMARY is not set")
    with Path(summary_path).open("a", encoding="utf-8") as summary:
        summary.write(
            render_summary(
                receipt, include_columns=args.include_columns, tool_version=args.tool_version
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
