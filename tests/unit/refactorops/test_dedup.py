#!/usr/bin/env python3
"""Unit tests for RefactorOps finding deduplication."""

from mcp_refactoring_assistant.refactorops.dedup import deduplicate_findings
from mcp_refactoring_assistant.refactorops.schema import Finding, Location, Position


def _make_location(file_path: str, line: int) -> Location:
    return Location(
        file=file_path,
        start=Position(line=line, col=1),
        end=Position(line=line + 1, col=1),
    )


def _make_finding(
    file_path: str,
    line: int,
    rule_id: str,
    message: str,
    tool: str = "ruff",
    category: str = "style",
) -> Finding:
    return Finding(
        tool=tool,
        category=category,
        severity="warn",
        confidence="high",
        rule_id=rule_id,
        message=message,
        location=_make_location(file_path, line),
    )


def test_deduplicate_by_rule_id():
    findings = [
        _make_finding("src/a.py", 10, "F401", "Unused import"),
        _make_finding("src/a.py", 10, "F401", "Unused import"),
    ]

    result = deduplicate_findings(findings)

    assert len(result) == 1
    merged = result[0].evidence.extra.get("merged", [])
    assert len(merged) == 1
    assert merged[0]["rule_id"] == "F401"


def test_deduplicate_by_message_hash_when_rule_id_missing():
    findings = [
        _make_finding("src/a.py", 5, "", "Shadowed name"),
        _make_finding("src/a.py", 5, "", "Shadowed name"),
    ]

    result = deduplicate_findings(findings)

    assert len(result) == 1
    merged = result[0].evidence.extra.get("merged", [])
    assert len(merged) == 1
    assert merged[0]["message"] == "Shadowed name"


def test_dedup_is_deterministic():
    findings = [
        _make_finding("src/b.py", 20, "B001", "Issue B"),
        _make_finding("src/a.py", 5, "A001", "Issue A"),
        _make_finding("src/a.py", 12, "A002", "Issue A2"),
    ]

    result = deduplicate_findings(findings)

    assert [f.location.file for f in result] == ["src/a.py", "src/a.py", "src/b.py"]
    assert [f.location.start.line for f in result] == [5, 12, 20]
