#!/usr/bin/env python3
"""Unit tests for dead code adapter."""

from types import SimpleNamespace

from mcp_refactoring_assistant.refactorops.adapters import dead_code as dead_code_adapter


class _FakeVulture:
    scanned_files = []
    items = []

    def scan(self, _content, filename=None):
        _FakeVulture.scanned_files.append(filename)

    def get_unused_code(self):
        return list(_FakeVulture.items)


class _FakeItem:
    def __init__(self, name, typ, confidence, filename, first_lineno, last_lineno=None, message=""):
        self.name = name
        self.typ = typ
        self.confidence = confidence
        self.filename = filename
        self.first_lineno = first_lineno
        self.last_lineno = last_lineno
        self.message = message


def test_run_dead_code_scan_filters_by_confidence(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "src" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("def unused():\n    pass\n")

    _FakeVulture.scanned_files = []
    _FakeVulture.items = [
        _FakeItem("unused", "function", 90, str(file_path), 1, 2, "unused function"),
        _FakeItem("maybe", "variable", 50, str(file_path), 3, 3, "unused variable"),
    ]

    monkeypatch.setattr(
        dead_code_adapter,
        "vulture",
        SimpleNamespace(Vulture=_FakeVulture),
    )

    findings, metrics, errors = dead_code_adapter.run_dead_code_scan(
        str(repo),
        files=["src/a.py"],
        min_confidence=80,
    )

    assert errors == []
    assert metrics.count == 2
    assert metrics.high_confidence == 1
    assert len(findings) == 1
    assert findings[0].rule_id == "vulture:unused-function"


def test_run_dead_code_scan_includes_low_confidence(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "src" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("def unused():\n    pass\n")

    _FakeVulture.scanned_files = []
    _FakeVulture.items = [
        _FakeItem("unused", "function", 40, str(file_path), 1, 2, "unused function"),
    ]

    monkeypatch.setattr(
        dead_code_adapter,
        "vulture",
        SimpleNamespace(Vulture=_FakeVulture),
    )

    findings, metrics, errors = dead_code_adapter.run_dead_code_scan(
        str(repo),
        files=["src/a.py"],
        min_confidence=80,
        include_low_confidence=True,
    )

    assert errors == []
    assert metrics.count == 1
    assert len(findings) == 1
    assert findings[0].severity == "info"


def test_run_dead_code_scan_skips_non_python_files(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "src" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("def unused():\n    pass\n")
    non_py = repo / "README.md"
    non_py.write_text("hello")

    _FakeVulture.scanned_files = []
    _FakeVulture.items = []

    monkeypatch.setattr(
        dead_code_adapter,
        "vulture",
        SimpleNamespace(Vulture=_FakeVulture),
    )

    dead_code_adapter.run_dead_code_scan(
        str(repo),
        files=["README.md", "src/a.py"],
    )

    assert str(file_path) in _FakeVulture.scanned_files
    assert str(non_py) not in _FakeVulture.scanned_files


def test_run_dead_code_scan_timeout(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    file_path = repo / "src" / "a.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("def unused():\n    pass\n")

    _FakeVulture.scanned_files = []
    _FakeVulture.items = []

    monkeypatch.setattr(
        dead_code_adapter,
        "vulture",
        SimpleNamespace(Vulture=_FakeVulture),
    )

    findings, metrics, errors = dead_code_adapter.run_dead_code_scan(
        str(repo),
        files=["src/a.py"],
        timeout_sec=0,
    )

    assert findings == []
    assert metrics.count == 0
    assert errors[0]["type"] == "timeout"
