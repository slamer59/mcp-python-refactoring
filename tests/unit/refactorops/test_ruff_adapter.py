#!/usr/bin/env python3
"""Unit tests for Ruff adapter."""

import json

from mcp_refactoring_assistant.refactorops.adapters import ruff as ruff_adapter
from mcp_refactoring_assistant.refactorops.exec import CommandResult


def test_run_ruff_check_maps_findings(monkeypatch, tmp_path):
    payload = [
        {
            "code": "F401",
            "message": "Unused import",
            "filename": "src/app.py",
            "location": {"row": 10, "column": 5},
            "end_location": {"row": 10, "column": 7},
            "fix": {
                "applicability": "safe",
                "message": "Remove unused import",
                "edits": [
                    {
                        "content": "",
                        "location": {"row": 10, "column": 1},
                        "end_location": {"row": 10, "column": 5},
                    }
                ],
            },
        }
    ]

    def fake_run(*_args, **_kwargs):
        return CommandResult(
            command=["ruff"],
            cwd=str(tmp_path),
            exit_code=1,
            stdout=json.dumps(payload),
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr(ruff_adapter, "run_command", fake_run)

    findings, metrics, errors = ruff_adapter.run_ruff_check(str(tmp_path), paths=["src/app.py"])

    assert errors == []
    assert metrics.errors == 1
    assert findings[0].rule_id == "F401"
    assert findings[0].location.file == "src/app.py"
    assert findings[0].fix.kind == "edit"


def test_run_ruff_check_reports_dependency_missing(monkeypatch, tmp_path):
    def fake_run(*_args, **_kwargs):
        return CommandResult(
            command=["ruff"],
            cwd=str(tmp_path),
            exit_code=None,
            stdout="",
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=False,
            error_type="dependency_missing",
            error_message="missing",
        )

    monkeypatch.setattr(ruff_adapter, "run_command", fake_run)

    findings, metrics, errors = ruff_adapter.run_ruff_check(str(tmp_path), paths=["src/app.py"])

    assert findings == []
    assert metrics.errors == 0
    assert errors[0]["type"] == "dependency_missing"


def test_run_ruff_check_handles_parse_error(monkeypatch, tmp_path):
    def fake_run(*_args, **_kwargs):
        return CommandResult(
            command=["ruff"],
            cwd=str(tmp_path),
            exit_code=1,
            stdout="not-json",
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr(ruff_adapter, "run_command", fake_run)

    findings, metrics, errors = ruff_adapter.run_ruff_check(str(tmp_path), paths=["src/app.py"])

    assert findings == []
    assert metrics.errors == 0
    assert errors[0]["type"] == "parse_error"


def test_run_ruff_check_builds_command(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, **_kwargs):
        captured["command"] = command
        return CommandResult(
            command=command,
            cwd=str(tmp_path),
            exit_code=0,
            stdout="[]",
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr(ruff_adapter, "run_command", fake_run)

    ruff_adapter.run_ruff_check(
        str(tmp_path),
        paths=["src"],
        select=["F", "E9"],
        ignore=["E501"],
    )

    assert captured["command"][:3] == ["ruff", "check", "--output-format=json"]
    assert "--select" in captured["command"]
    assert "F,E9" in captured["command"]
    assert "--ignore" in captured["command"]
    assert "E501" in captured["command"]


def test_run_ruff_fix_safe_diff(monkeypatch, tmp_path):
    diff_text = """--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-old\n+new\n"""

    def fake_run(*_args, **_kwargs):
        return CommandResult(
            command=["ruff"],
            cwd=str(tmp_path),
            exit_code=1,
            stdout=diff_text,
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr(ruff_adapter, "run_command", fake_run)

    findings, metrics, fix_result, errors = ruff_adapter.run_ruff_fix_safe(
        str(tmp_path),
        paths=["src/app.py"],
        apply=False,
    )

    assert errors == []
    assert fix_result["diff"] == diff_text
    assert fix_result["changed_files"] == ["src/app.py"]
