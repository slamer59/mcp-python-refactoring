#!/usr/bin/env python3
"""Unit tests for complexity adapter."""

from types import SimpleNamespace

from mcp_refactoring_assistant.refactorops.adapters import complexity as complexity_adapter


class _FakeBlock:
    def __init__(self, name, complexity, lineno, endline, classname=None, letter="F"):
        self.name = name
        self.complexity = complexity
        self.lineno = lineno
        self.endline = endline
        self.classname = classname
        self.letter = letter


class _FakeFunction:
    def __init__(self, name, complexity, line_start, line_end):
        self.name = name
        self.complexity = complexity
        self.line_start = line_start
        self.line_end = line_end


def test_run_complexity_scan_maps_findings(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "src" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    content_lines = ["def long():"] + ["    x = 1"] * 35
    file_path.write_text("\n".join(content_lines) + "\n")

    def fake_cc_visit(_content):
        return [
            _FakeBlock("long", 12, 1, 10),
            _FakeBlock("ignored", 5, 20, 21),
            _FakeBlock("Cls", 20, 1, 2, letter="C"),
        ]

    def fake_code_complexity(_content):
        return SimpleNamespace(functions=[_FakeFunction("long", 20, 1, 10)])

    monkeypatch.setattr(complexity_adapter, "cc_visit", fake_cc_visit)
    monkeypatch.setattr(complexity_adapter, "code_complexity", fake_code_complexity)

    findings, metrics, errors = complexity_adapter.run_complexity_scan(
        str(repo),
        files=["src/a.py"],
        max_cyclomatic=10,
        max_cognitive=15,
        max_function_lines=10,
    )

    assert errors == []
    assert metrics.max_cyclomatic == 12
    assert metrics.max_cognitive == 20
    assert metrics.long_functions == 1
    rule_ids = {finding.rule_id for finding in findings}
    assert "radon:cyclomatic" in rule_ids
    assert "complexipy:cognitive" in rule_ids
    assert "complexity:long-function" in rule_ids


def test_run_complexity_scan_handles_missing_dependencies(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "src" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("def long():\n    return 1\n")

    monkeypatch.setattr(complexity_adapter, "cc_visit", None)
    monkeypatch.setattr(complexity_adapter, "code_complexity", None)

    findings, metrics, errors = complexity_adapter.run_complexity_scan(
        str(repo),
        files=["src/a.py"],
        max_function_lines=1,
    )

    assert metrics.long_functions == 1
    assert any(error["type"] == "dependency_missing" for error in errors)
    assert any(finding.rule_id == "complexity:long-function" for finding in findings)


def test_run_complexity_scan_timeout(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "src" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("def f():\n    return 1\n")

    findings, metrics, errors = complexity_adapter.run_complexity_scan(
        str(repo),
        files=["src/a.py"],
        timeout_sec=0,
    )

    assert findings == []
    assert metrics.max_cyclomatic == 0
    assert errors[0]["type"] == "timeout"
