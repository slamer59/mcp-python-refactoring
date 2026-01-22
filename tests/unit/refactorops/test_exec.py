#!/usr/bin/env python3
"""Unit tests for RefactorOps command execution."""

from pathlib import Path
import subprocess

from mcp_refactoring_assistant.refactorops.exec import run_command


def test_run_command_rejects_not_allowed(tmp_path: Path) -> None:
    result = run_command(["rm", "-rf", "/"], repo_root=str(tmp_path))

    assert result.ok is False
    assert result.error_type == "not_allowed"


def test_run_command_rejects_empty_command(tmp_path: Path) -> None:
    result = run_command([], repo_root=str(tmp_path))

    assert result.ok is False
    assert result.error_type == "invalid_command"


def test_run_command_rejects_invalid_cwd(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = run_command(["git", "status"], repo_root=str(missing))

    assert result.ok is False
    assert result.error_type == "invalid_cwd"


def test_run_command_runs_and_captures(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_run(args, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return subprocess.CompletedProcess(args=args, returncode=2, stdout="out", stderr="err")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_command(["git", "status"], repo_root=str(tmp_path))

    assert result.ok is True
    assert result.exit_code == 2
    assert result.stdout == "out"
    assert result.stderr == "err"
    assert captured["cwd"] == str(tmp_path.resolve())


def test_run_command_handles_timeout(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*_args, **_kwargs):
        exc = subprocess.TimeoutExpired(cmd="git", timeout=1)
        exc.stdout = "partial"
        exc.stderr = "timeout"
        raise exc

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_command(["git", "status"], repo_root=str(tmp_path), timeout_sec=1)

    assert result.ok is False
    assert result.timed_out is True
    assert result.error_type == "timeout"
    assert result.stdout == "partial"
    assert result.stderr == "timeout"


def test_run_command_handles_missing_executable(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*_args, **_kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_command(["ruff", "check"], repo_root=str(tmp_path))

    assert result.ok is False
    assert result.error_type == "dependency_missing"


def test_run_command_truncates_output(monkeypatch, tmp_path: Path) -> None:
    def fake_run(args, **_kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="abcdef", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_command(["git", "status"], repo_root=str(tmp_path), max_output_chars=3)

    assert result.ok is True
    assert result.stdout == "abc"
    assert result.truncated is True
    assert result.stdout_len == 6


def test_run_command_blocks_interactive_git(tmp_path: Path) -> None:
    result = run_command(["git", "-i", "status"], repo_root=str(tmp_path))

    assert result.ok is False
    assert result.error_type == "not_allowed"
