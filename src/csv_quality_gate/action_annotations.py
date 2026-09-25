"""Emit bounded, value-free GitHub Actions annotations from a gate receipt."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

MAX_ANNOTATIONS = 50
MAX_RECEIPT_BYTES = 1024 * 1024
_SEVERITIES = {"error": "error", "warning": "warning"}
_MESSAGE = "CSV quality gate detected an affected row."


def _escape_property(value: str) -> str:
    return (value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            .replace(":", "%3A").replace(",", "%2C"))


def _workspace_file(value: object, workspace: Path) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        candidate = Path(value)
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (workspace / candidate).resolve()
        )
        return resolved.relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return None


def workflow_commands(receipt: object, workspace: Path) -> Iterable[str]:
    """Yield safe, bounded file/row annotations only for receipt-backed evidence."""
    results = receipt if isinstance(receipt, list) else [receipt]
    emitted: set[tuple[str, int, str]] = set()
    for result in results:
        if not isinstance(result, dict):
            continue
        file_name = _workspace_file(result.get("path"), workspace)
        if file_name is None:
            continue
        for issue in result.get("issues", []):
            if not isinstance(issue, dict):
                continue
            severity = _SEVERITIES.get(issue.get("severity"))
            evidence = issue.get("evidence")
            if severity is None or not isinstance(evidence, dict):
                continue
            for row in evidence.get("rows", []):
                if isinstance(row, bool) or not isinstance(row, int) or row < 1:
                    continue
                key = (file_name, row, severity)
                if key in emitted:
                    continue
                emitted.add(key)
                yield (
                    f"::{severity} file={_escape_property(file_name)},line={row},"
                    f"title=CSV quality gate::{_MESSAGE}"
                )
                if len(emitted) >= MAX_ANNOTATIONS:
                    return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit GitHub Actions annotations from a gate receipt"
    )
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with args.receipt.open("rb") as receipt_file:
            raw_receipt = receipt_file.read(MAX_RECEIPT_BYTES + 1)
        if len(raw_receipt) > MAX_RECEIPT_BYTES:
            return 0
        receipt: Any = json.loads(raw_receipt.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        parser.error(f"could not read receipt: {error}")
    for command in workflow_commands(receipt, args.workspace):
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
