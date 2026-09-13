from csv_quality_gate.action_summary import (
    MAX_EVIDENCE_COLUMNS,
    MAX_SUMMARY_CHARS,
    render_summary,
)


def test_summary_has_status_profile_row_and_issue_counts_without_source_data():
    summary = render_summary(
        {
            "path": "/private/input-[hidden](https://example.invalid).csv",
            "profile": "outreach",
            "rows": 4,
            "status": "fail",
            "issues": [
                {
                    "severity": "error",
                    "message": "a private cell value",
                    "evidence": {"column": "company", "total": 3, "rows": [2, 3, 4]},
                },
                {"severity": "warning", "message": "another private cell value"},
            ],
        }
    )

    assert "| Status | fail |" in summary
    assert "| Profile | outreach |" in summary
    assert "| Rows | 4 |" in summary
    assert "| Issues | 2 |" in summary
    assert "| Errors | 1 |" in summary
    assert "| Warnings | 1 |" in summary
    assert "private" not in summary
    assert "company" not in summary
    assert "https://example.invalid" not in summary


def test_summary_columns_are_explicitly_opted_in_and_escaped():
    summary = render_summary(
        {
            "path": "ignored.csv",
            "profile": "bad|profile [link](https://example.invalid)",
            "rows": 1,
            "status": "warn",
            "issues": [
                {
                    "severity": "warning",
                    "message": "ignored",
                    "evidence": {
                        "column": "company|name [link](https://example.invalid)",
                        "total": 1,
                        "rows": [2],
                    },
                }
            ],
        },
        include_columns=True,
    )

    expected_columns = (
        "| Evidence column | company\\|name \\[link\\]\\(https://example\\.invalid\\) |"
    )
    assert expected_columns in summary
    assert "| Profile | bad\\|profile \\[link\\]\\(https://example\\.invalid\\) |" in summary
    assert "<a " not in summary


def test_summary_bounds_untrusted_dynamic_values_and_evidence_columns():
    receipt = {
        "profile": "p" * 1_000_000,
        "rows": 1,
        "status": "warn",
        "issues": [
            {
                "severity": "warning",
                "evidence": {"column": f"column-{index}-" + "x" * 1_000_000},
            }
            for index in range(MAX_EVIDENCE_COLUMNS + 1)
        ],
    }

    summary = render_summary(receipt, include_columns=True)

    assert len(summary) <= MAX_SUMMARY_CHARS
    assert "…" in summary
    assert f"column\\-{MAX_EVIDENCE_COLUMNS - 1}" in summary
    assert f"column\\-{MAX_EVIDENCE_COLUMNS}" not in summary
