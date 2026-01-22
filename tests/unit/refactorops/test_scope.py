#!/usr/bin/env python3
"""Unit tests for RefactorOps scope resolution."""

from pathlib import Path

from mcp_refactoring_assistant.refactorops.exec import CommandResult
from mcp_refactoring_assistant.refactorops.scope import resolve_scope
from mcp_refactoring_assistant.refactorops.schema import ScopeGit, ScopeSpec


def _write_file(path: Path, content: str = "test") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_repo_scope_excludes_dirs_and_extensions(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    _write_file(repo / "src" / "keep.py")
    _write_file(repo / "node_modules" / "skip.js")
    _write_file(repo / "dist" / "bundle.js")
    _write_file(repo / "assets" / "image.png", content="\x00binary")

    result = resolve_scope(str(repo), ScopeSpec(type="repo"))

    assert result.files == ["src/keep.py"]
    assert "no_files_matched" not in result.errors


def test_paths_scope_includes_files_and_dirs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    _write_file(repo / "README.md")
    _write_file(repo / "src" / "a.py")
    _write_file(repo / "src" / "nested" / "b.py")

    scope = ScopeSpec(type="paths", paths=["README.md", "src"])
    result = resolve_scope(str(repo), scope)

    assert result.files == ["README.md", "src/a.py", "src/nested/b.py"]


def test_paths_scope_blocks_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("print('outside')")

    scope = ScopeSpec(type="paths", paths=["../outside.py"])
    result = resolve_scope(str(repo), scope)

    assert result.files == []
    assert "path_outside_repo" in result.errors
    assert "no_files_matched" in result.errors


def test_changed_scope_uses_git_diff(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_file(repo / "src" / "keep.py")
    _write_file(repo / "node_modules" / "skip.js")

    def fake_run(*_args, **_kwargs):
        return CommandResult(
            command=["git"],
            cwd=str(repo),
            exit_code=0,
            stdout="src/keep.py\nnode_modules/skip.js\nmissing.py\n",
            stderr="",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr("mcp_refactoring_assistant.refactorops.scope.run_command", fake_run)

    scope = ScopeSpec(type="changed", git=ScopeGit(base="origin/main", head="HEAD"))
    result = resolve_scope(str(repo), scope)

    assert result.files == ["src/keep.py"]


def test_changed_scope_falls_back_on_failure(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_file(repo / "src" / "fallback.py")

    def fake_run(*_args, **_kwargs):
        return CommandResult(
            command=["git"],
            cwd=str(repo),
            exit_code=1,
            stdout="",
            stderr="err",
            duration_ms=1,
            timed_out=False,
            ok=True,
        )

    monkeypatch.setattr("mcp_refactoring_assistant.refactorops.scope.run_command", fake_run)

    scope = ScopeSpec(type="changed", paths=["src/fallback.py"], git=ScopeGit(base="main", head="HEAD"))
    result = resolve_scope(str(repo), scope)

    assert result.files == ["src/fallback.py"]
    assert "git_diff_failed" in result.errors
