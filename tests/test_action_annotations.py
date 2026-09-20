from csv_quality_gate.action_annotations import MAX_ANNOTATIONS, workflow_commands


def test_annotations_use_only_workspace_paths_rows_and_severity(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("company\nAcme\n")
    receipt = {
        "path": str(csv_file),
        "issues": [
            {
                "severity": "warning",
                "message": "private",
                "evidence": {"column": "secret", "rows": [2, 2]},
            },
            {
                "severity": "error",
                "message": "private",
                "evidence": {"column": "secret", "rows": [2]},
            },
        ],
    }
    commands = list(workflow_commands(receipt, tmp_path))
    expected = "title=CSV quality gate::CSV quality gate detected an affected row."
    assert commands == [
        f"::warning file=data.csv,line=2,{expected}",
        f"::error file=data.csv,line=2,{expected}",
    ]
    assert "private" not in "".join(commands)
    assert "secret" not in "".join(commands)


def test_annotations_skip_outside_paths_and_bound_output(tmp_path):
    receipt = {"path": "/outside.csv", "issues": [{"severity": "error", "evidence": {"rows": [2]}}]}
    assert list(workflow_commands(receipt, tmp_path)) == []
    inside = tmp_path / "data.csv"
    inside.write_text("x\n")
    rows = list(range(1, MAX_ANNOTATIONS + 10))
    commands = list(
        workflow_commands(
            {"path": str(inside), "issues": [{"severity": "error", "evidence": {"rows": rows}}]},
            tmp_path,
        )
    )
    assert len(commands) == MAX_ANNOTATIONS
