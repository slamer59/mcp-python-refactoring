#!/usr/bin/env python3
"""
Type-check a *line selection* of a file, with Django support and resource caps.

Why this is not a plain BaseAnalyzer
------------------------------------
mypy/dmypy/pyrefly cannot type-check a line range in isolation: they must see
the whole module to resolve types. So "check the selection" really means
"check the whole module, then keep only diagnostics whose line falls in
[start_line, end_line]".

Why it does NOT copy to a temp file (unlike PyreflyAnalyzer)
------------------------------------------------------------
Django code only type-checks correctly when the file stays in its package on
sys.path, the project config (mypy.ini with the django plugin) is passed, and
the checker runs from the project root. Copying to /tmp strips all of that.
We therefore run on the file *in place*, from ``project_root``.

Default backend: dmypy (warm daemon)
------------------------------------
The interactive refactoring loop is "check -> see error -> edit -> check again".
dmypy keeps a resident daemon so the re-check is incremental (~0.09s here) vs
re-parsing everything (~0.7s for one-shot mypy). That speed is the whole point.

Resource safety - and the dmypy-specific trap
----------------------------------------------
For one-shot checkers (pyrefly, plain mypy) we wrap each call in a transient
systemd user scope with MemoryMax + CPUQuota; an OOM then kills only that scope.

dmypy is different: its RAM lives in the *daemon*, not the client. If we wrapped
each ``dmypy check`` in a per-call scope, the daemon would be born into that
scope's cgroup and killed the instant the client exits - destroying the warm
daemon every time. So for dmypy we cap the **daemon's lifetime** instead: start
it once inside a capped ``Type=forking`` systemd service (MemoryMax + CPUQuota on
the daemon cgroup, verified enforced), give it ``--timeout`` so it self-reaps when
idle, and let subsequent checks be thin, fast, unwrapped clients.
"""

import hashlib
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional, Tuple

Severity = Literal["low", "medium", "high", "critical"]

from ..models import RefactoringGuidance

# mypy / dmypy:  path:line: error: msg   or   path:line:col: error: msg
_DIAG_RE = re.compile(r"^(?P<path>.+?):(?P<line>\d+):(?:(?P<col>\d+):)?\s*(?P<sev>error|warning|note):\s*(?P<msg>.*)$")

# pyrefly (>=0.30) is a two-line, rustc-style diagnostic:
#   ERROR <message> [<code>]
#    --> path:line:col
_PYREFLY_HDR_RE = re.compile(r"^\s*(?P<sev>ERROR|WARN(?:ING)?)\s+(?P<msg>.*\S)\s*$")
_PYREFLY_LOC_RE = re.compile(r"^\s*-->\s*(?P<path>.+?):(?P<line>\d+):(?P<col>\d+)\s*$")


@dataclass
class _Diag:
    line: int
    severity: str
    message: str


# --------------------------------------------------------------------------- #
# Diagnostic parsing
# --------------------------------------------------------------------------- #
def _parse(output: str, target: Path) -> List[_Diag]:
    """Parse mypy/dmypy single-line and pyrefly two-line diagnostics.

    Only diagnostics about ``target`` are kept; errors in imported modules
    (e.g. a Django dependency) are dropped as noise.
    """
    diags: List[_Diag] = []
    pending: Optional[Tuple[str, str]] = None  # (severity, message) awaiting `-->`

    for raw in output.splitlines():
        m = _DIAG_RE.match(raw)
        if m:
            pending = None
            if Path(m.group("path")).name == target.name:
                diags.append(_Diag(int(m.group("line")), m.group("sev").lower(), m.group("msg").strip()))
            continue

        hdr = _PYREFLY_HDR_RE.match(raw)
        if hdr:
            sev = "error" if hdr.group("sev").startswith("ERROR") else "warning"
            pending = (sev, hdr.group("msg").strip())
            continue
        loc = _PYREFLY_LOC_RE.match(raw)
        if loc and pending:
            if Path(loc.group("path")).name == target.name:
                diags.append(_Diag(int(loc.group("line")), pending[0], pending[1]))
            pending = None

    return diags


# --------------------------------------------------------------------------- #
# Resource caps
# --------------------------------------------------------------------------- #
def _scope_caps(memory_max: str, cpu_quota: str) -> List[str]:
    """Per-call systemd user scope for one-shot checkers (pyrefly / plain mypy)."""
    nice = ["nice", "-n", "10"] if shutil.which("nice") else []
    if shutil.which("systemd-run"):
        return [
            "systemd-run", "--user", "--scope", "--quiet",
            "-p", f"MemoryMax={memory_max}", "-p", "MemorySwapMax=0",
            "-p", f"CPUQuota={cpu_quota}",
        ] + nice
    return nice


# --------------------------------------------------------------------------- #
# dmypy daemon lifecycle (capped once, reused warm)
# --------------------------------------------------------------------------- #
def _dmypy_ids(project_root: str, config_file: Optional[str]) -> Tuple[str, str]:
    """Deterministic (status_file, unit_name) per (project_root, config) so
    different projects get their own daemon instead of fighting over one."""
    key = f"{Path(project_root).resolve()}::{config_file or ''}"
    h = hashlib.sha1(key.encode()).hexdigest()[:12]
    status = str(Path(tempfile.gettempdir()) / f"mcp-dmypy-{h}.json")
    return status, f"mcp-dmypy-{h}"


def _dmypy_up(dmypy: str, status_file: str) -> bool:
    return subprocess.run(
        [dmypy, "--status-file", status_file, "status"],
        capture_output=True, text=True,
    ).returncode == 0


def _ensure_capped_daemon(
    dmypy: str, status_file: str, unit: str, config_file: Optional[str], cwd: str,
    memory_max: str, cpu_quota: str, idle_timeout: int,
) -> None:
    """Start the dmypy daemon once, inside a capped systemd service. No-op if up."""
    if _dmypy_up(dmypy, status_file):
        return

    mypy_flags = ["--show-column-numbers"]
    if config_file:
        mypy_flags = ["--config-file", config_file, *mypy_flags]
    start = [dmypy, "--status-file", status_file, "start", "--timeout", str(idle_timeout), "--", *mypy_flags]

    if shutil.which("systemd-run"):
        subprocess.run(["systemctl", "--user", "reset-failed", f"{unit}.service"],
                       capture_output=True, text=True)  # clear any stale unit
        subprocess.run(
            ["systemd-run", "--user", "--quiet", f"--unit={unit}",
             f"--working-directory={cwd}",
             "-p", f"MemoryMax={memory_max}", "-p", "MemorySwapMax=0",
             "-p", f"CPUQuota={cpu_quota}", "-p", "Type=forking", *start],
            capture_output=True, text=True,
        )
    else:
        # No systemd: still get the warm daemon, just uncapped.
        subprocess.Popen(start, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for _ in range(50):  # wait up to ~5s for readiness
        if _dmypy_up(dmypy, status_file):
            return
        time.sleep(0.1)


def _guidance(issue_type: str, severity: Severity, location: str, description: str, steps: List[str]) -> RefactoringGuidance:
    return RefactoringGuidance(
        issue_type=issue_type, severity=severity, location=location,
        description=description, precise_steps=steps,
    )


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def analyze_types_on_selection(
    file_path: str,
    start_line: int,
    end_line: int,
    *,
    config_file: Optional[str] = None,
    project_root: Optional[str] = None,
    checker: str = "dmypy",
    memory_max: str = "1500M",
    cpu_quota: str = "80%",
    timeout_seconds: int = 120,
    daemon_idle_timeout: int = 600,
) -> List[RefactoringGuidance]:
    """Type-check ``file_path`` and return only diagnostics on lines [start,end].

    Args:
        file_path: Real path to the file (NOT a temp copy - Django needs it
            in place on sys.path).
        start_line, end_line: 1-based inclusive selection range.
        config_file: e.g. the project's ``mypy.ini`` carrying the django plugin.
        project_root: cwd to run from; for Django, where settings import from.
            Defaults to the file's parent.
        checker: ``"dmypy"`` (default - warm daemon, fast incremental re-checks),
            ``"mypy"`` (one-shot, no resident RAM), or ``"pyrefly"`` (Rust, fast).
    """
    target = Path(file_path)
    if not target.is_file():
        return [_guidance("type_check_error", "low", file_path,
                          f"File not found: {file_path}", ["Pass an existing, in-place file path."])]
    checker_bin = shutil.which(checker)
    if not checker_bin:
        return [_guidance("type_check_unavailable", "low", file_path,
                          f"Type checker '{checker}' is not installed.",
                          ["Install it, or pass checker= one of dmypy/mypy/pyrefly."])]

    cwd = project_root or str(target.parent)

    try:
        if checker == "dmypy":
            status_file, unit = _dmypy_ids(cwd, config_file)
            _ensure_capped_daemon(checker_bin, status_file, unit, config_file, cwd,
                                  memory_max, cpu_quota, daemon_idle_timeout)
            if not _dmypy_up(checker_bin, status_file):
                return [_guidance("type_check_error", "medium", file_path,
                                  "dmypy daemon failed to start.",
                                  ["Try checker='mypy' for a one-shot run."])]
            cmd = [checker_bin, "--status-file", status_file, "check", str(target)]
        elif checker == "pyrefly":
            cmd = [*_scope_caps(memory_max, cpu_quota), "pyrefly", "check", str(target)]
        else:  # one-shot mypy
            mypy_cmd = ["mypy", "--show-column-numbers"]
            if config_file:
                mypy_cmd = ["mypy", "--config-file", config_file, "--show-column-numbers"]
            cmd = [*_scope_caps(memory_max, cpu_quota), *mypy_cmd, str(target)]

        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return [_guidance("type_check_timeout", "medium", file_path,
                          f"Type check exceeded {timeout_seconds}s and was killed.",
                          ["Increase timeout_seconds, or use checker='pyrefly' for speed."])]

    in_range = [d for d in _parse(proc.stdout + "\n" + proc.stderr, target)
                if start_line <= d.line <= end_line]
    if not in_range:
        return []

    return [RefactoringGuidance(
        issue_type="type_errors",
        severity="medium",
        location=f"lines {start_line}-{end_line} ({len(in_range)} issue(s))",
        description=f"{checker} reported {len(in_range)} type issue(s) in the selection.",
        precise_steps=[
            "🔍 TYPE ISSUES IN SELECTION:",
            *[f"• L{d.line} [{d.severity}] {d.message}" for d in in_range[:10]],
        ],
        benefits=["Catches type regressions before runtime", "Fast incremental re-checks while editing"],
        metrics={"checker": checker, "issues_in_range": len(in_range)},
    )]
