#!/usr/bin/env python3
"""Unit tests for analyze_repo_quality orchestrator."""

import importlib

analyze_module = importlib.import_module(
    "mcp_refactoring_assistant.refactorops.tools.analyze_repo_quality"
)
from mcp_refactoring_assistant.refactorops.schema import (  # type: ignore[import-not-found]
    Evidence,
    Finding,
    Location,
    Position,
    RuffMetrics,
)
from mcp_refactoring_assistant.refactorops.scope import (  # type: ignore[import-not-found]
    ResolvedScope,
)


def _make_finding(rule_id: str) -> Finding:
    return Finding(
        tool="ruff",
        category="style",
        severity="error",
        confidence="high",
        rule_id=rule_id,
        message="Issue",
        location=Location(
            file="src/app.py",
            start=Position(line=1, col=1),
            end=Position(line=1, col=1),
        ),
        evidence=Evidence(summary="Issue", extra={}),
    )


def test_analyze_repo_quality_truncates_and_fails_on_ruff(monkeypatch, tmp_path):
    resolved = ResolvedScope(files=["src/app.py"], errors=[], skipped=[])

    def fake_scope(*_args, **_kwargs):
        return resolved

    def fake_ruff(*_args, **_kwargs):
        findings = [_make_finding("F401"), _make_finding("F402"), _make_finding("F403")]
        metrics = RuffMetrics(errors=3, warnings=0, files_scanned=1)
        return findings, metrics, []

    monkeypatch.setattr(analyze_module, "resolve_scope", fake_scope)
    monkeypatch.setattr(analyze_module, "run_ruff_check", fake_ruff)

    payload = {
        "repo_root": str(tmp_path),
        "scope": {"type": "repo"},
        "modes": ["ruff"],
        "budgets": {"timeout_sec": 30, "max_findings": 2},
    }
    result = analyze_module.analyze_repo_quality(payload)

    assert result.summary.status == "fail"
    assert "ruff_errors" in result.summary.gate_reasons
    assert len(result.findings) == 2
    assert any(f.rule_id == "refactorops:findings_truncated" for f in result.findings)


def test_analyze_repo_quality_handles_no_files(monkeypatch, tmp_path):
    resolved = ResolvedScope(files=[], errors=["no_files_matched"], skipped=[])

    monkeypatch.setattr(analyze_module, "resolve_scope", lambda *_args, **_kwargs: resolved)

    payload = {
        "repo_root": str(tmp_path),
        "scope": {"type": "paths", "paths": ["missing.py"]},
        "modes": ["ruff"],
        "budgets": {"timeout_sec": 30, "max_findings": 10},
    }
    result = analyze_module.analyze_repo_quality(payload)

    assert result.summary.status == "warn"
    assert "scope_failed" in result.summary.gate_reasons
    assert any(f.rule_id == "refactorops:no_files_matched" for f in result.findings)
