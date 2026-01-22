#!/usr/bin/env python3
"""Unit tests for RefactorOps schema models."""

import pytest
from pydantic import ValidationError

from mcp_refactoring_assistant.refactorops.schema import (
    Budgets,
    Finding,
    HotspotRange,
    Location,
    Metrics,
    Position,
    RepoQualityResult,
    RunInfo,
    ScopeSpec,
    Summary,
)


def _make_location() -> Location:
    return Location(
        file="src/example.py",
        start=Position(line=10, col=1),
        end=Position(line=12, col=1),
    )


def _make_finding() -> Finding:
    return Finding(
        tool="ruff",
        category="style",
        severity="warn",
        confidence="high",
        rule_id="F401",
        message="Unused import",
        location=_make_location(),
    )


def test_repo_quality_result_serialization():
    run = RunInfo(
        id="run-1",
        timestamp="2026-01-23T00:00:00Z",
        repo_root="/repo",
        scope=ScopeSpec(type="repo"),
        budgets=Budgets(timeout_sec=60, max_findings=100),
    )
    result = RepoQualityResult(
        run=run,
        metrics=Metrics(),
        findings=[_make_finding()],
        hotspots=[],
        summary=Summary(status="pass", gate_reasons=[]),
    )

    payload = result.to_dict()

    assert "run" in payload
    assert "metrics" in payload
    assert "findings" in payload
    assert "hotspots" in payload
    assert "summary" in payload
    assert payload["run"]["scope"]["type"] == "repo"
    assert payload["findings"][0]["rule_id"] == "F401"


def test_position_validation():
    with pytest.raises(ValidationError):
        Position(line=0, col=1)


def test_hotspot_range_validation():
    with pytest.raises(ValidationError):
        HotspotRange(start_line=10, end_line=5)
