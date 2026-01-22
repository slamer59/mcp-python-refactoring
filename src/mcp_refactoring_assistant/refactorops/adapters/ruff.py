"""Ruff adapter for RefactorOps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, cast

from ..exec import CommandResult, run_command
from ..schema import Evidence, Finding, Fix, FixEdit, Location, Position, RuffMetrics

Category = Literal[
    "duplication",
    "dead_code",
    "style",
    "bug_risk",
    "complexity",
    "security",
    "typing",
    "refactor_opportunity",
    "scope_hint",
]


def run_ruff_check(
    repo_root: str,
    paths: Optional[Sequence[str]] = None,
    select: Optional[Sequence[str]] = None,
    ignore: Optional[Sequence[str]] = None,
    timeout_sec: int = 120,
) -> Tuple[List[Finding], RuffMetrics, List[Dict[str, Any]]]:
    """Run ruff check and map results to standardized findings."""

    errors: List[Dict[str, Any]] = []
    command = _build_ruff_command(paths, select, ignore, fix=False)
    if command is None:
        errors.append(_error("no_paths", "No paths provided for ruff check"))
        return [], RuffMetrics(), errors

    result = run_command(command, repo_root=repo_root, timeout_sec=timeout_sec)
    if not result.ok:
        errors.append(_command_error(result))
        return [], RuffMetrics(), errors

    if result.exit_code not in (0, 1):
        errors.append(_command_error(result))
        return [], RuffMetrics(), errors

    findings, parse_errors = _parse_ruff_output(result.stdout, repo_root)
    errors.extend(parse_errors)
    metrics = _build_metrics(findings)
    return findings, metrics, errors


def run_ruff_fix_safe(
    repo_root: str,
    paths: Optional[Sequence[str]] = None,
    select: Optional[Sequence[str]] = None,
    ignore: Optional[Sequence[str]] = None,
    timeout_sec: int = 120,
    apply: bool = False,
) -> Tuple[List[Finding], RuffMetrics, Dict[str, Any], List[Dict[str, Any]]]:
    """Run safe ruff fixes and return diff information."""

    errors: List[Dict[str, Any]] = []
    command = _build_ruff_command(paths, select, ignore, fix=True, diff=not apply)
    if command is None:
        errors.append(_error("no_paths", "No paths provided for ruff fix"))
        return [], RuffMetrics(), _empty_fix_result(applied=apply), errors

    result = run_command(command, repo_root=repo_root, timeout_sec=timeout_sec)
    if not result.ok:
        errors.append(_command_error(result))
        return [], RuffMetrics(), _empty_fix_result(applied=apply), errors

    if result.exit_code not in (0, 1):
        errors.append(_command_error(result))
        return [], RuffMetrics(), _empty_fix_result(applied=apply), errors

    findings: List[Finding] = []
    parse_errors: List[Dict[str, Any]] = []
    if apply:
        findings, parse_errors = _parse_ruff_output(result.stdout, repo_root)
    errors.extend(parse_errors)
    metrics = _build_metrics(findings)

    diff_text = result.stdout if not apply else ""
    changed_files = _extract_changed_files(diff_text)
    fix_result = {
        "applied": apply,
        "diff": diff_text,
        "changed_files": changed_files,
    }

    return findings, metrics, fix_result, errors


def _build_ruff_command(
    paths: Optional[Sequence[str]],
    select: Optional[Sequence[str]],
    ignore: Optional[Sequence[str]],
    fix: bool,
    diff: bool = False,
) -> Optional[List[str]]:
    resolved_paths = _normalize_paths(paths)
    if not resolved_paths:
        return None

    command = ["ruff", "check", "--output-format=json"]
    if fix:
        command.append("--fix")
    if diff:
        command.append("--diff")
    if select:
        command.extend(["--select", ",".join(select)])
    if ignore:
        command.extend(["--ignore", ",".join(ignore)])

    command.extend(resolved_paths)
    return command


def _normalize_paths(paths: Optional[Sequence[str]]) -> List[str]:
    if paths is None:
        return ["."]
    return list(paths)


def _parse_ruff_output(
    stdout: str,
    repo_root: str,
) -> Tuple[List[Finding], List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    if not stdout.strip():
        return [], errors

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        errors.append(_error("parse_error", f"Failed to parse Ruff JSON: {exc}"))
        return [], errors

    if not isinstance(payload, list):
        errors.append(_error("parse_error", "Unexpected Ruff output format"))
        return [], errors

    findings: List[Finding] = []
    for item in payload:
        finding = _map_ruff_item(item, repo_root)
        if finding is not None:
            findings.append(finding)

    return findings, errors


def _map_ruff_item(item: Dict[str, Any], repo_root: str) -> Optional[Finding]:
    if not isinstance(item, dict):
        return None

    code = str(item.get("code", ""))
    message = str(item.get("message", ""))
    filename = str(item.get("filename", ""))
    location = item.get("location", {}) or {}
    end_location = item.get("end_location", {}) or location

    start = _position_from(location)
    end = _position_from(end_location)
    normalized_file = _normalize_filename(filename, repo_root)

    return Finding(
        tool="ruff",
        category=_category_for_code(code),
        severity="error",
        confidence="high",
        rule_id=code,
        message=message,
        location=Location(file=normalized_file, start=start, end=end),
        evidence=Evidence(summary=message, extra={"raw": item}),
        fix=_build_fix(item, normalized_file),
    )


def _build_fix(item: Dict[str, Any], filename: str) -> Fix:
    fix_data = item.get("fix")
    if not isinstance(fix_data, dict):
        return Fix()

    edits_raw = fix_data.get("edits")
    if not isinstance(edits_raw, list) or not edits_raw:
        return Fix()

    applicability = str(fix_data.get("applicability", "")).lower()
    safe = applicability not in {"unsafe", "manual"}
    edits: List[FixEdit] = []
    for edit in edits_raw:
        if not isinstance(edit, dict):
            continue
        start_loc = edit.get("location") or edit.get("start") or {}
        end_loc = edit.get("end_location") or edit.get("end") or start_loc
        edits.append(
            FixEdit(
                file=filename,
                start=_position_from(start_loc),
                end=_position_from(end_loc),
                content=str(edit.get("content", "")),
            )
        )

    if not edits:
        return Fix()

    return Fix(
        kind="edit",
        safe=safe,
        edits=edits,
        notes=fix_data.get("message"),
    )


def _position_from(location: Dict[str, Any]) -> Position:
    line = int(location.get("row") or location.get("line") or 1)
    col = int(location.get("column") or location.get("col") or 1)
    return Position(line=max(1, line), col=max(1, col))


def _normalize_filename(filename: str, repo_root: str) -> str:
    if not filename:
        return filename

    path = Path(filename)
    if path.is_absolute():
        root = Path(repo_root).resolve()
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return path.as_posix()
    return path.as_posix()


def _category_for_code(code: str) -> Category:
    if code.startswith(("F", "B", "E9")):
        return cast(Category, "bug_risk")
    return cast(Category, "style")


def _build_metrics(findings: List[Finding]) -> RuffMetrics:
    files_scanned = len({finding.location.file for finding in findings if finding.location.file})
    return RuffMetrics(errors=len(findings), warnings=0, files_scanned=files_scanned)


def _command_error(result: CommandResult) -> Dict[str, Any]:
    return {
        "type": result.error_type or "command_failed",
        "message": result.error_message or "Command execution failed",
        "command": list(result.command),
        "exit_code": result.exit_code,
        "stderr": result.stderr,
    }


def _error(error_type: str, message: str) -> Dict[str, Any]:
    return {
        "type": error_type,
        "message": message,
    }


def _extract_changed_files(diff_text: str) -> List[str]:
    if not diff_text:
        return []

    files: List[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path == "/dev/null":
                continue
            if path.startswith("b/"):
                path = path[2:]
            files.append(path)
    return sorted(set(files))


def _empty_fix_result(applied: bool) -> Dict[str, Any]:
    return {
        "applied": applied,
        "diff": "",
        "changed_files": [],
    }
