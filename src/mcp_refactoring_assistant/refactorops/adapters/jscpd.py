"""jscpd adapter for RefactorOps."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..exec import CommandResult, run_command
from ..schema import DuplicationMetrics, Evidence, Finding, Location, Position


def run_jscpd(
    repo_root: str,
    paths: Optional[Sequence[str]] = None,
    min_lines: int = 10,
    min_tokens: int = 50,
    ignore: Optional[Sequence[str]] = None,
    timeout_sec: int = 120,
    use_npx: bool = False,
    gitignore: bool = True,
    no_symlinks: bool = True,
    include_fragments: bool = False,
    max_fragment_chars: int = 2000,
) -> Tuple[List[Finding], DuplicationMetrics, List[Dict[str, Any]]]:
    """Run jscpd and map report to standardized findings."""

    errors: List[Dict[str, Any]] = []
    resolved_paths = _normalize_paths(paths)
    if resolved_paths is None:
        errors.append(_error("no_paths", "No paths provided for jscpd"))
        return [], DuplicationMetrics(), errors

    with tempfile.TemporaryDirectory(prefix="refactorops-jscpd-") as output_dir:
        command = _build_jscpd_command(
            resolved_paths,
            output_dir,
            min_lines=min_lines,
            min_tokens=min_tokens,
            ignore=ignore,
            gitignore=gitignore,
            no_symlinks=no_symlinks,
            use_npx=False,
        )
        result = run_command(command, repo_root=repo_root, timeout_sec=timeout_sec)
        if not result.ok and result.error_type == "dependency_missing" and use_npx:
            command = _build_jscpd_command(
                resolved_paths,
                output_dir,
                min_lines=min_lines,
                min_tokens=min_tokens,
                ignore=ignore,
                gitignore=gitignore,
                no_symlinks=no_symlinks,
                use_npx=True,
            )
            result = run_command(command, repo_root=repo_root, timeout_sec=timeout_sec)

        if not result.ok:
            errors.append(_command_error(result))
            return [], DuplicationMetrics(), errors

        if result.exit_code not in (0, 1):
            errors.append(_command_error(result))

        report_path = Path(output_dir) / "jscpd-report.json"
        if not report_path.exists():
            errors.append(_error("report_missing", "jscpd report file not found"))
            return [], DuplicationMetrics(), errors

        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(_error("parse_error", f"Failed to parse jscpd report: {exc}"))
            return [], DuplicationMetrics(), errors

        findings, metrics = _map_report(
            report,
            repo_root=repo_root,
            include_fragments=include_fragments,
            max_fragment_chars=max_fragment_chars,
        )
        return findings, metrics, errors


def _build_jscpd_command(
    paths: Sequence[str],
    output_dir: str,
    min_lines: int,
    min_tokens: int,
    ignore: Optional[Sequence[str]],
    gitignore: bool,
    no_symlinks: bool,
    use_npx: bool,
) -> List[str]:
    command = ["jscpd"]
    if use_npx:
        command = ["npx", "jscpd"]

    command.extend([
        "--reporters",
        "json",
        "--output",
        output_dir,
        "--min-lines",
        str(min_lines),
        "--min-tokens",
        str(min_tokens),
        "--silent",
    ])

    if gitignore:
        command.append("--gitignore")
    if no_symlinks:
        command.append("--noSymlinks")
    if ignore:
        command.extend(["--ignore", ",".join(ignore)])

    command.extend([str(path) for path in paths])
    return command


def _normalize_paths(paths: Optional[Sequence[str]]) -> Optional[List[str]]:
    if paths is None:
        return ["."]
    if len(paths) == 0:
        return None
    return list(paths)


def _map_report(
    report: Dict[str, Any],
    repo_root: str,
    include_fragments: bool,
    max_fragment_chars: int,
) -> Tuple[List[Finding], DuplicationMetrics]:
    if not isinstance(report, dict):
        return [], DuplicationMetrics()

    duplicates = report.get("duplicates", [])
    if not isinstance(duplicates, list):
        duplicates = []

    sorted_dupes = sorted(duplicates, key=_dup_sort_key)
    findings: List[Finding] = []
    for dup in sorted_dupes:
        finding = _map_duplicate(dup, repo_root, include_fragments, max_fragment_chars)
        if finding is not None:
            findings.append(finding)

    metrics = _extract_metrics(report, sorted_dupes)
    return findings, metrics


def _dup_sort_key(dup: Dict[str, Any]) -> Tuple:
    first = dup.get("firstFile", {}) if isinstance(dup, dict) else {}
    second = dup.get("secondFile", {}) if isinstance(dup, dict) else {}
    return (
        str(first.get("name", "")),
        int(first.get("start", 0) or 0),
        str(second.get("name", "")),
        int(second.get("start", 0) or 0),
        int(dup.get("lines", 0) or 0),
        int(dup.get("tokens", 0) or 0),
        str(dup.get("format", "")),
    )


def _map_duplicate(
    dup: Dict[str, Any],
    repo_root: str,
    include_fragments: bool,
    max_fragment_chars: int,
) -> Optional[Finding]:
    if not isinstance(dup, dict):
        return None

    first = dup.get("firstFile")
    second = dup.get("secondFile")
    if not isinstance(first, dict) or not isinstance(second, dict):
        return None

    first_name = _normalize_filename(str(first.get("name", "")), repo_root)
    start = _position_from_clone(first, "startLoc", "start")
    end = _position_from_clone(first, "endLoc", "end")

    summary = _build_summary(dup)
    evidence_extra = {
        "firstFile": _normalize_file_info(first, repo_root),
        "secondFile": _normalize_file_info(second, repo_root),
        "format": dup.get("format"),
        "lines": dup.get("lines"),
        "tokens": dup.get("tokens"),
    }

    fragment = dup.get("fragment")
    if include_fragments and isinstance(fragment, str):
        truncated_fragment = fragment[:max_fragment_chars]
        evidence_extra["fragment"] = truncated_fragment
        evidence_extra["fragment_len"] = len(fragment)
        evidence_extra["fragment_truncated"] = len(fragment) > max_fragment_chars

    return Finding(
        tool="jscpd",
        category="duplication",
        severity="warn",
        confidence="high",
        rule_id="jscpd",
        message=summary,
        location=Location(file=first_name, start=start, end=end),
        evidence=Evidence(summary=summary, extra=evidence_extra),
    )


def _normalize_file_info(file_info: Dict[str, Any], repo_root: str) -> Dict[str, Any]:
    normalized = dict(file_info)
    name = file_info.get("name")
    if isinstance(name, str):
        normalized["name"] = _normalize_filename(name, repo_root)
    return normalized


def _position_from_clone(file_info: Dict[str, Any], loc_key: str, fallback_key: str) -> Position:
    loc = file_info.get(loc_key) or {}
    if not isinstance(loc, dict):
        loc = {}
    line = loc.get("line") or file_info.get(fallback_key) or 1
    col = loc.get("column") or 1
    return Position(line=max(1, int(line)), col=max(1, int(col)))


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


def _build_summary(dup: Dict[str, Any]) -> str:
    lines = dup.get("lines")
    tokens = dup.get("tokens")
    if lines is not None and tokens is not None:
        return f"Duplicated block ({lines} lines, {tokens} tokens)"
    if lines is not None:
        return f"Duplicated block ({lines} lines)"
    return "Duplicated block"


def _extract_metrics(report: Dict[str, Any], duplicates: List[Dict[str, Any]]) -> DuplicationMetrics:
    statistic = report.get("statistic", {}) if isinstance(report, dict) else {}
    total = statistic.get("total", {}) if isinstance(statistic, dict) else {}

    percentage = _to_float(total.get("percentage"), 0.0)
    duplicated_lines = _to_int(total.get("duplicatedLines"), 0)
    clones = _to_int(total.get("clones"), len(duplicates))
    sources = _to_int(total.get("sources"), _count_sources(duplicates))

    return DuplicationMetrics(
        percentage=percentage,
        duplicated_lines=duplicated_lines,
        clones=clones,
        sources=sources,
    )


def _count_sources(duplicates: List[Dict[str, Any]]) -> int:
    sources: set[str] = set()
    for dup in duplicates:
        if not isinstance(dup, dict):
            continue
        for key in ("firstFile", "secondFile"):
            file_info = dup.get(key)
            if isinstance(file_info, dict):
                name = file_info.get("name")
                if isinstance(name, str):
                    sources.add(name)
    return len(sources)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
