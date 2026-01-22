#!/usr/bin/env python3
"""Unit tests for jscpd adapter."""

import json
from pathlib import Path

from mcp_refactoring_assistant.refactorops.adapters import jscpd as jscpd_adapter
from mcp_refactoring_assistant.refactorops.exec import CommandResult


def test_run_jscpd_maps_findings(monkeypatch, tmp_path: Path) -> None:
    report = {
        "duplicates": [
            {
                "format": "python",
                "lines": 10,
                "tokens": 50,
                "fragment": "abcdef",
                "firstFile": {
                    "name": "src/a.py",
                    "start": 1,
                    "end": 10,
                    "startLoc": {"line": 1, "column": 1},
                    "endLoc": {"line": 10, "column": 2},
                },
                "secondFile": {
                    "name": "src/b.py",
                    "start": 5,
                    "end": 14,
                    "startLoc": {"line": 5, "column": 1},
                    "endLoc": {"line": 14, "column": 2},
                },
            }
        ],
        "statistic": {
            "total": {"percentage": 12.5, "duplicatedLines": 20, "clones": 1, "sources": 2}
        },
    }

    def fake_run(command, **_kwargs):
        output_dir = _extract_output_dir(command)
        report_path = Path(output_dir) / "jscpd-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return CommandResult(
            command=command,
            cwd=str(tmp_path),
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr(jscpd_adapter, "run_command", fake_run)

    findings, metrics, errors = jscpd_adapter.run_jscpd(
        str(tmp_path),
        paths=["src"],
        include_fragments=True,
        max_fragment_chars=3,
    )

    assert errors == []
    assert metrics.percentage == 12.5
    assert metrics.clones == 1
    assert findings[0].rule_id == "jscpd"
    assert findings[0].location.file == "src/a.py"
    assert findings[0].evidence.extra["fragment"] == "abc"
    assert findings[0].evidence.extra["fragment_truncated"] is True


def test_run_jscpd_reports_dependency_missing(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*_args, **_kwargs):
        return CommandResult(
            command=["jscpd"],
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

    monkeypatch.setattr(jscpd_adapter, "run_command", fake_run)

    findings, metrics, errors = jscpd_adapter.run_jscpd(str(tmp_path), paths=["src"])

    assert findings == []
    assert metrics.clones == 0
    assert errors[0]["type"] == "dependency_missing"


def test_run_jscpd_uses_npx_fallback(monkeypatch, tmp_path: Path) -> None:
    report = {"duplicates": [], "statistic": {"total": {"percentage": 0}}}
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if command[0] == "jscpd":
            return CommandResult(
                command=command,
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
        output_dir = _extract_output_dir(command)
        report_path = Path(output_dir) / "jscpd-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return CommandResult(
            command=command,
            cwd=str(tmp_path),
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr(jscpd_adapter, "run_command", fake_run)

    findings, metrics, errors = jscpd_adapter.run_jscpd(
        str(tmp_path),
        paths=["src"],
        use_npx=True,
    )

    assert errors == []
    assert calls[0][0] == "jscpd"
    assert calls[1][0] == "npx"
    assert findings == []


def test_run_jscpd_reports_missing_report(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **_kwargs):
        return CommandResult(
            command=command,
            cwd=str(tmp_path),
            exit_code=0,
            stdout="",
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr(jscpd_adapter, "run_command", fake_run)

    findings, metrics, errors = jscpd_adapter.run_jscpd(str(tmp_path), paths=["src"])

    assert findings == []
    assert metrics.clones == 0
    assert errors[0]["type"] == "report_missing"


def _extract_output_dir(command) -> str:
    output_index = command.index("--output")
    return command[output_index + 1]
