"""Safe command execution helpers for RefactorOps."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import Optional, Sequence, Set


DEFAULT_ALLOWED_COMMANDS: Set[str] = {
    "git",
    "jscpd",
    "npx",
    "python",
    "python3",
    "ruff",
}


@dataclass
class CommandResult:
    command: Sequence[str]
    cwd: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    ok: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    truncated: bool = False
    stdout_len: int = 0
    stderr_len: int = 0


def run_command(
    command: Sequence[str],
    repo_root: str,
    timeout_sec: int = 120,
    allowed_commands: Optional[Set[str]] = None,
    max_output_chars: int = 50000,
) -> CommandResult:
    """Run a command with allowlist, timeout, and safe defaults."""

    start_time = time.monotonic()
    cwd = str(Path(repo_root).resolve())

    if not command:
        return _result(
            command,
            cwd,
            error_type="invalid_command",
            error_message="Command is empty",
            start_time=start_time,
        )

    if not Path(cwd).exists():
        return _result(
            command,
            cwd,
            error_type="invalid_cwd",
            error_message="Repository root does not exist",
            start_time=start_time,
        )

    allowed = allowed_commands or DEFAULT_ALLOWED_COMMANDS
    command_name = Path(command[0]).name
    if command_name not in allowed:
        return _result(
            command,
            cwd,
            error_type="not_allowed",
            error_message=f"Command '{command_name}' is not allowed",
            start_time=start_time,
        )

    if command_name == "git" and "-i" in command:
        return _result(
            command,
            cwd,
            error_type="not_allowed",
            error_message="Interactive git commands are not allowed",
            start_time=start_time,
        )

    try:
        proc = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, truncated = _truncate_outputs(
            exc.stdout or "",
            exc.stderr or "",
            max_output_chars,
        )
        return _result(
            command,
            cwd,
            stdout=stdout,
            stderr=stderr,
            stdout_len=len(exc.stdout or ""),
            stderr_len=len(exc.stderr or ""),
            truncated=truncated,
            timed_out=True,
            ok=False,
            error_type="timeout",
            error_message="Command execution timed out",
            start_time=start_time,
        )
    except FileNotFoundError:
        return _result(
            command,
            cwd,
            error_type="dependency_missing",
            error_message=f"Executable '{command_name}' not found",
            start_time=start_time,
        )
    except OSError as exc:
        return _result(
            command,
            cwd,
            error_type="execution_failed",
            error_message=str(exc),
            start_time=start_time,
        )

    stdout, stderr, truncated = _truncate_outputs(
        proc.stdout or "",
        proc.stderr or "",
        max_output_chars,
    )

    return _result(
        command,
        cwd,
        exit_code=proc.returncode,
        stdout=stdout,
        stderr=stderr,
        stdout_len=len(proc.stdout or ""),
        stderr_len=len(proc.stderr or ""),
        truncated=truncated,
        timed_out=False,
        ok=True,
        start_time=start_time,
    )


def _truncate_outputs(stdout: str, stderr: str, max_output_chars: int) -> tuple[str, str, bool]:
    if max_output_chars <= 0:
        return "", "", True

    truncated = False
    if len(stdout) > max_output_chars:
        stdout = stdout[:max_output_chars]
        truncated = True
    if len(stderr) > max_output_chars:
        stderr = stderr[:max_output_chars]
        truncated = True
    return stdout, stderr, truncated


def _result(
    command: Sequence[str],
    cwd: str,
    start_time: float,
    exit_code: Optional[int] = None,
    stdout: str = "",
    stderr: str = "",
    stdout_len: int = 0,
    stderr_len: int = 0,
    truncated: bool = False,
    timed_out: bool = False,
    ok: bool = False,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
) -> CommandResult:
    duration_ms = int((time.monotonic() - start_time) * 1000)
    return CommandResult(
        command=command,
        cwd=cwd,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        timed_out=timed_out,
        ok=ok,
        error_type=error_type,
        error_message=error_message,
        truncated=truncated,
        stdout_len=stdout_len,
        stderr_len=stderr_len,
    )
