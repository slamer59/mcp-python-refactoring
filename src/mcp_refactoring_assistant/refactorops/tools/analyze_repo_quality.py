"""RefactorOps all-in-one analysis orchestration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import time
import uuid
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, cast

from pydantic import ValidationError

from ..adapters import (
    run_complexity_scan,
    run_dead_code_scan,
    run_jscpd,
    run_ruff_check,
)
from ..dedup import deduplicate_findings
from ..schema import (
    Budgets,
    ComplexityMetrics,
    DeadCodeMetrics,
    DuplicationMetrics,
    Evidence,
    Finding,
    Hotspot,
    HotspotRange,
    Location,
    Metrics,
    Position,
    RepoQualityResult,
    RuffMetrics,
    RunInfo,
    ScopeSpec,
    Summary,
)
from ..scope import ResolvedScope, resolve_scope


DEFAULT_MODES = ["ruff", "duplication", "dead_code", "complexity"]
DEFAULT_JSCPD_IGNORE = ["**/venv/**", "**/node_modules/**"]
DEFAULT_JSCPD_MIN_LINES = 10
DEFAULT_JSCPD_MIN_TOKENS = 50
DEFAULT_DEAD_CODE_CONFIDENCE = 80
DEFAULT_MAX_CYCLOMATIC = 10
DEFAULT_MAX_COGNITIVE = 15
DEFAULT_MAX_FUNCTION_LINES = 30


def analyze_repo_quality(payload: Dict[str, Any]) -> RepoQualityResult:
    """Run RefactorOps analysis pipeline and return a standardized result."""

    repo_root = str(payload.get("repo_root") or ".")
    scope_spec, scope_errors = _parse_scope(payload.get("scope"))
    budgets, budget_errors = _parse_budgets(payload.get("budgets"))
    modes = _parse_modes(payload.get("modes"))
    options = payload.get("options") or {}

    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    resolved_root = _resolve_repo_root(repo_root)

    resolved_scope = resolve_scope(
        resolved_root,
        scope_spec,
        fallback_paths=scope_spec.paths,
        git_timeout_sec=min(10, budgets.timeout_sec),
    )

    findings: List[Finding] = []
    metrics = Metrics()
    errors_by_tool: Dict[str, List[Dict[str, Any]]] = {
        "scope": _build_scope_errors(scope_errors, resolved_scope),
    }

    for error in errors_by_tool["scope"]:
        findings.append(_error_to_finding("refactorops", error, severity="warn"))

    if not resolved_scope.files:
        summary = _build_summary(
            metrics,
            modes,
            errors_by_tool,
            options,
            findings_truncated=False,
        )
        return RepoQualityResult(
            run=RunInfo(
                id=run_id,
                timestamp=timestamp,
                repo_root=resolved_root,
                scope=scope_spec,
                budgets=budgets,
            ),
            metrics=metrics,
            findings=deduplicate_findings(findings),
            hotspots=[],
            summary=summary,
        )

    deadline = time.monotonic() + budgets.timeout_sec
    python_files = _filter_python_files(resolved_scope.files)

    adapter_results: Dict[str, Tuple[List[Finding], Any, List[Dict[str, Any]]]] = {}
    parallel_modes = [mode for mode in modes if mode in {"ruff", "dead_code", "complexity"}]
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {}
        for mode in parallel_modes:
            timeout_sec = _remaining_seconds(deadline)
            if timeout_sec <= 0:
                errors_by_tool.setdefault(mode, []).append(
                    _error("timeout", f"{mode} scan timed out")
                )
                continue
            if mode == "ruff":
                if not python_files:
                    errors_by_tool.setdefault(mode, []).append(
                        _error("no_python_files", "No Python files to scan with ruff")
                    )
                    continue
                future_map[mode] = executor.submit(
                    run_ruff_check,
                    resolved_root,
                    python_files,
                    _as_list(options.get("ruff", {}).get("select")),
                    _as_list(options.get("ruff", {}).get("ignore")),
                    timeout_sec,
                )
            elif mode == "dead_code":
                if not python_files:
                    errors_by_tool.setdefault(mode, []).append(
                        _error("no_python_files", "No Python files to scan for dead code")
                    )
                    continue
                dead_code_opts = options.get("dead_code", {})
                future_map[mode] = executor.submit(
                    run_dead_code_scan,
                    resolved_root,
                    python_files,
                    int(dead_code_opts.get("vulture_min_confidence", DEFAULT_DEAD_CODE_CONFIDENCE)),
                    timeout_sec,
                    bool(dead_code_opts.get("include_low_confidence", False)),
                )
            elif mode == "complexity":
                if not python_files:
                    errors_by_tool.setdefault(mode, []).append(
                        _error("no_python_files", "No Python files to scan for complexity")
                    )
                    continue
                complexity_opts = options.get("complexity", {})
                future_map[mode] = executor.submit(
                    run_complexity_scan,
                    resolved_root,
                    python_files,
                    int(complexity_opts.get("max_cyclomatic", DEFAULT_MAX_CYCLOMATIC)),
                    int(complexity_opts.get("max_cognitive", DEFAULT_MAX_COGNITIVE)),
                    int(complexity_opts.get("max_function_lines", DEFAULT_MAX_FUNCTION_LINES)),
                    timeout_sec,
                )

        for mode, future in future_map.items():
            try:
                adapter_results[mode] = future.result()
            except Exception as exc:  # pragma: no cover - defensive
                errors_by_tool.setdefault(mode, []).append(
                    _error("exception", f"{mode} scan failed: {exc}")
                )
                adapter_results[mode] = ([], _default_metrics(mode), [])

    if "duplication" in modes:
        timeout_sec = _remaining_seconds(deadline)
        if timeout_sec <= 0:
            errors_by_tool.setdefault("duplication", []).append(
                _error("timeout", "duplication scan timed out")
            )
        else:
            duplication_opts = options.get("jscpd", {})
            ignore = duplication_opts.get("ignore")
            if ignore is None:
                ignore = DEFAULT_JSCPD_IGNORE
            findings_dup, metrics_dup, errors_dup = run_jscpd(
                resolved_root,
                resolved_scope.files,
                int(duplication_opts.get("min_lines", DEFAULT_JSCPD_MIN_LINES)),
                int(duplication_opts.get("min_tokens", DEFAULT_JSCPD_MIN_TOKENS)),
                _as_list(ignore),
                timeout_sec,
                bool(duplication_opts.get("use_npx", False)),
                bool(duplication_opts.get("gitignore", True)),
                bool(duplication_opts.get("no_symlinks", True)),
                bool(duplication_opts.get("include_fragments", False)),
                int(duplication_opts.get("max_fragment_chars", 2000)),
            )
            adapter_results["duplication"] = (findings_dup, metrics_dup, errors_dup)

    for mode, (mode_findings, mode_metrics, mode_errors) in adapter_results.items():
        findings.extend(mode_findings)
        if mode_errors:
            errors_by_tool.setdefault(mode, []).extend(mode_errors)
        if mode == "ruff" and isinstance(mode_metrics, RuffMetrics):
            metrics.ruff = mode_metrics
        elif mode == "duplication" and isinstance(mode_metrics, DuplicationMetrics):
            metrics.duplication = mode_metrics
        elif mode == "dead_code" and isinstance(mode_metrics, DeadCodeMetrics):
            metrics.dead_code = mode_metrics
        elif mode == "complexity" and isinstance(mode_metrics, ComplexityMetrics):
            metrics.complexity = mode_metrics

    for tool, tool_errors in errors_by_tool.items():
        for error in tool_errors:
            severity = _error_severity(tool, error)
            findings.append(
                _error_to_finding(
                    tool,
                    error,
                    severity=cast(Literal["error", "warn", "info"], severity),
                )
            )

    findings = deduplicate_findings(sorted(findings, key=_finding_sort_key))
    findings, truncated = _apply_findings_budget(findings, budgets.max_findings)
    if truncated:
        findings.append(_truncation_finding(truncated))

    hotspots = _build_hotspots(findings)
    summary = _build_summary(metrics, modes, errors_by_tool, options, truncated > 0)

    return RepoQualityResult(
        run=RunInfo(
            id=run_id,
            timestamp=timestamp,
            repo_root=resolved_root,
            scope=scope_spec,
            budgets=budgets,
        ),
        metrics=metrics,
        findings=findings,
        hotspots=hotspots,
        summary=summary,
    )


def _parse_scope(scope_input: Any) -> Tuple[ScopeSpec, List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    if scope_input is None:
        return ScopeSpec(type="repo"), errors
    try:
        return ScopeSpec.model_validate(scope_input), errors
    except ValidationError as exc:
        errors.append(_error("invalid_scope", str(exc)))
        return ScopeSpec(type="repo"), errors


def _parse_budgets(budget_input: Any) -> Tuple[Budgets, List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    if budget_input is None:
        return Budgets(), errors
    try:
        return Budgets.model_validate(budget_input), errors
    except ValidationError as exc:
        errors.append(_error("invalid_budgets", str(exc)))
        return Budgets(), errors


def _parse_modes(modes_input: Any) -> List[str]:
    if not modes_input:
        return list(DEFAULT_MODES)
    if isinstance(modes_input, list):
        return [str(mode) for mode in modes_input]
    return list(DEFAULT_MODES)


def _resolve_repo_root(repo_root: str) -> str:
    return str(Path(repo_root).resolve())


def _build_scope_errors(
    parse_errors: List[Dict[str, Any]],
    resolved: ResolvedScope,
) -> List[Dict[str, Any]]:
    errors = list(parse_errors)
    for code in resolved.errors:
        errors.append(_error(code, f"Scope resolution reported {code}"))
    for skipped in resolved.skipped:
        errors.append(
            _error(
                skipped.get("reason", "skipped"),
                f"Skipped {skipped.get('path', '')}",
            )
        )
    return errors


def _default_metrics(mode: str) -> Any:
    if mode == "ruff":
        return RuffMetrics()
    if mode == "duplication":
        return DuplicationMetrics()
    if mode == "dead_code":
        return DeadCodeMetrics()
    if mode == "complexity":
        return ComplexityMetrics()
    return {}


def _filter_python_files(files: Sequence[str]) -> List[str]:
    python_files = []
    for path in files:
        lower = path.lower()
        if lower.endswith(".py") or lower.endswith(".pyi") or lower.endswith(".pyw"):
            python_files.append(path)
    return python_files


def _remaining_seconds(deadline: float) -> int:
    remaining = int(deadline - time.monotonic())
    return remaining if remaining > 0 else 0


def _as_list(value: Optional[Sequence[str]]) -> List[str]:
    if value is None:
        return []
    return list(value)


def _error_to_finding(
    tool: str,
    error: Dict[str, Any],
    severity: Literal["error", "warn", "info"],
) -> Finding:
    error_type = str(error.get("type") or "error")
    message = str(error.get("message") or f"{tool} error: {error_type}")
    return Finding(
        tool=str(tool),
        category="refactor_opportunity",
        severity=severity,
        confidence="high",
        rule_id=f"{tool}:{error_type}",
        message=message,
        location=Location(
            file=str(error.get("file") or ""),
            start=Position(line=1, col=1),
            end=Position(line=1, col=1),
        ),
        evidence=Evidence(summary=message, extra={"error": error}),
    )


def _error_severity(tool: str, error: Dict[str, Any]) -> Literal["error", "warn", "info"]:
    error_type = str(error.get("type") or "")
    if tool == "ruff" and error_type in {
        "dependency_missing",
        "timeout",
        "command_failed",
        "parse_error",
        "exception",
    }:
        return "error"
    return "warn"


def _apply_findings_budget(findings: List[Finding], max_findings: int) -> Tuple[List[Finding], int]:
    if max_findings <= 0 or len(findings) <= max_findings:
        return findings, 0
    keep = max_findings - 1 if max_findings > 1 else 0
    truncated = len(findings) - keep
    return findings[:keep], truncated


def _truncation_finding(truncated: int) -> Finding:
    message = f"Findings truncated: {truncated} items omitted"
    return Finding(
        tool="refactorops",
        category="refactor_opportunity",
        severity="warn",
        confidence="high",
        rule_id="refactorops:findings_truncated",
        message=message,
        location=Location(
            file="",
            start=Position(line=1, col=1),
            end=Position(line=1, col=1),
        ),
        evidence=Evidence(summary=message, extra={"truncated": truncated}),
    )


def _finding_sort_key(finding: Finding) -> Tuple:
    return (
        finding.location.file,
        finding.location.start.line,
        finding.rule_id,
        finding.message,
    )


def _build_hotspots(findings: List[Finding]) -> List[Hotspot]:
    dup_counts: Dict[str, int] = {}
    ruff_counts: Dict[str, int] = {}
    complexity_counts: Dict[str, int] = {}
    ranges_by_file: Dict[str, List[Tuple[int, int]]] = {}

    for finding in findings:
        file_path = finding.location.file
        if file_path:
            ranges_by_file.setdefault(file_path, []).append(
                (finding.location.start.line, finding.location.end.line)
            )

        if finding.tool == "ruff":
            _bump_count(ruff_counts, file_path)
        elif finding.category == "complexity":
            _bump_count(complexity_counts, file_path)
        elif finding.tool == "jscpd" and finding.category == "duplication":
            _bump_count(dup_counts, file_path)
            extra = finding.evidence.extra
            for key in ("firstFile", "secondFile"):
                file_info = extra.get(key)
                if isinstance(file_info, dict):
                    name = file_info.get("name")
                    if isinstance(name, str):
                        _bump_count(dup_counts, name)

    max_dup = max(dup_counts.values(), default=0)
    max_ruff = max(ruff_counts.values(), default=0)
    max_complexity = max(complexity_counts.values(), default=0)

    files = sorted({*dup_counts.keys(), *ruff_counts.keys(), *complexity_counts.keys()})
    hotspots: List[Hotspot] = []
    for file_path in files:
        dup_score = (dup_counts.get(file_path, 0) / max_dup) if max_dup else 0.0
        ruff_score = (ruff_counts.get(file_path, 0) / max_ruff) if max_ruff else 0.0
        complexity_score = (
            (complexity_counts.get(file_path, 0) / max_complexity)
            if max_complexity
            else 0.0
        )
        score = 0.5 * dup_score + 0.3 * ruff_score + 0.2 * complexity_score
        reasons = []
        if dup_counts.get(file_path, 0):
            reasons.append("duplication")
        if ruff_counts.get(file_path, 0):
            reasons.append("ruff")
        if complexity_counts.get(file_path, 0):
            reasons.append("complexity")
        top_ranges = _build_hotspot_ranges(ranges_by_file.get(file_path, []))
        hotspots.append(
            Hotspot(file=file_path, reasons=reasons, score=round(score, 4), top_ranges=top_ranges)
        )

    return hotspots


def _build_hotspot_ranges(ranges: List[Tuple[int, int]]) -> List[HotspotRange]:
    if not ranges:
        return []
    normalized = sorted({(start, end) for start, end in ranges})
    top = normalized[:3]
    return [HotspotRange(start_line=start, end_line=end) for start, end in top]


def _bump_count(counter: Dict[str, int], key: str) -> None:
    if not key:
        return
    counter[key] = counter.get(key, 0) + 1


def _build_summary(
    metrics: Metrics,
    modes: List[str],
    errors_by_tool: Dict[str, List[Dict[str, Any]]],
    options: Dict[str, Any],
    findings_truncated: bool,
) -> Summary:
    reasons: List[str] = []

    ruff_errors = metrics.ruff.errors if "ruff" in modes else 0
    ruff_failed = _has_errors(errors_by_tool.get("ruff", []))
    if "ruff" in modes and (ruff_errors > 0 or ruff_failed):
        if ruff_errors > 0:
            reasons.append("ruff_errors")
        if ruff_failed:
            reasons.append("ruff_failed")
        return Summary(status="fail", gate_reasons=sorted(set(reasons)))

    if errors_by_tool.get("duplication"):
        reasons.append("duplication_failed")
    if errors_by_tool.get("dead_code"):
        reasons.append("dead_code_failed")
    if errors_by_tool.get("complexity"):
        reasons.append("complexity_failed")
    if errors_by_tool.get("scope"):
        reasons.append("scope_failed")

    if metrics.dead_code.high_confidence > 0:
        reasons.append("dead_code_high_confidence")

    complexity_opts = options.get("complexity", {})
    max_cyclomatic = int(complexity_opts.get("max_cyclomatic", DEFAULT_MAX_CYCLOMATIC))
    max_cognitive = int(complexity_opts.get("max_cognitive", DEFAULT_MAX_COGNITIVE))
    max_function_lines = int(
        complexity_opts.get("max_function_lines", DEFAULT_MAX_FUNCTION_LINES)
    )
    if metrics.complexity.max_cyclomatic > max_cyclomatic:
        reasons.append("complexity_cyclomatic")
    if metrics.complexity.max_cognitive > max_cognitive:
        reasons.append("complexity_cognitive")
    if metrics.complexity.long_functions > 0 and max_function_lines > 0:
        reasons.append("long_functions")

    if findings_truncated:
        reasons.append("findings_truncated")

    status = "warn" if reasons else "pass"
    return Summary(status=status, gate_reasons=sorted(set(reasons)))


def _has_errors(errors: Optional[List[Dict[str, Any]]]) -> bool:
    if not errors:
        return False
    for error in errors:
        if error.get("type") in {"no_python_files", "no_files"}:
            continue
        return True
    return False


def _error(error_type: str, message: str) -> Dict[str, Any]:
    return {
        "type": error_type,
        "message": message,
    }
