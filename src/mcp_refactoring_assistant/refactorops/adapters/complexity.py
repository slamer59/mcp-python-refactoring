"""Complexity adapter for RefactorOps."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from radon.complexity import cc_visit  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised via runtime error handling
    cc_visit = None

try:
    from complexipy import code_complexity  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised via runtime error handling
    code_complexity = None

from ..schema import ComplexityMetrics, Evidence, Finding, Location, Position


@dataclass
class _FunctionSpan:
    name: str
    start_line: int
    end_line: int
    line_count: int


def run_complexity_scan(
    repo_root: str,
    files: Sequence[str],
    max_cyclomatic: int = 10,
    max_cognitive: int = 15,
    max_function_lines: int = 30,
    timeout_sec: int = 120,
) -> Tuple[List[Finding], ComplexityMetrics, List[Dict[str, Any]]]:
    """Run complexity analysis and map results to findings."""

    errors: List[Dict[str, Any]] = []
    if not files:
        errors.append(_error("no_files", "No files provided for complexity scan"))
        return [], ComplexityMetrics(), errors

    if timeout_sec <= 0:
        errors.append(_error("timeout", "Complexity scan timed out"))
        return [], ComplexityMetrics(), errors

    if cc_visit is None:
        errors.append(_error("dependency_missing", "radon is not installed"))
    if code_complexity is None:
        errors.append(_error("dependency_missing", "complexipy is not installed"))

    root = Path(repo_root).resolve()
    start_time = time.monotonic()
    findings: List[Finding] = []
    hotspots: set[Tuple[str, int, str]] = set()
    max_cyclomatic_seen = 0
    max_cognitive_seen = 0
    long_functions = 0

    for rel_path in files:
        if time.monotonic() - start_time > timeout_sec:
            errors.append(_error("timeout", "Complexity scan timed out"))
            break

        if not _is_python_file(rel_path):
            continue

        full_path = root / rel_path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(_error("read_failed", f"Failed to read {rel_path}: {exc}"))
            continue

        if cc_visit is not None:
            try:
                blocks = cc_visit(content)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(_error("radon_failed", f"Failed to analyze {rel_path}: {exc}"))
            else:
                for block in blocks:
                    if not _is_function_block(block):
                        continue
                    complexity = int(getattr(block, "complexity", 0) or 0)
                    if complexity > max_cyclomatic_seen:
                        max_cyclomatic_seen = complexity
                    if complexity <= max_cyclomatic:
                        continue
                    name = _format_block_name(block)
                    lineno = int(getattr(block, "lineno", 1) or 1)
                    endline = int(getattr(block, "endline", lineno) or lineno)
                    message = f"High cyclomatic complexity ({complexity}) in '{name}'"
                    findings.append(
                        Finding(
                            tool="radon",
                            category="complexity",
                            severity="warn",
                            confidence="high",
                            rule_id="radon:cyclomatic",
                            message=message,
                            location=Location(
                                file=rel_path,
                                start=Position(line=lineno, col=1),
                                end=Position(line=endline, col=1),
                            ),
                            evidence=Evidence(
                                summary=message,
                                extra={
                                    "complexity": complexity,
                                    "threshold": max_cyclomatic,
                                    "function": name,
                                },
                            ),
                        )
                    )
                    hotspots.add((rel_path, lineno, name))

        if code_complexity is not None:
            try:
                report = code_complexity(content)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(_error("complexipy_failed", f"Failed to analyze {rel_path}: {exc}"))
            else:
                for func in getattr(report, "functions", []):
                    complexity = int(getattr(func, "complexity", 0) or 0)
                    if complexity > max_cognitive_seen:
                        max_cognitive_seen = complexity
                    if complexity <= max_cognitive:
                        continue
                    name = str(getattr(func, "name", ""))
                    line_start = int(getattr(func, "line_start", 1) or 1)
                    line_end = int(getattr(func, "line_end", line_start) or line_start)
                    message = f"High cognitive complexity ({complexity}) in '{name}'"
                    findings.append(
                        Finding(
                            tool="complexipy",
                            category="complexity",
                            severity="warn",
                            confidence="high",
                            rule_id="complexipy:cognitive",
                            message=message,
                            location=Location(
                                file=rel_path,
                                start=Position(line=line_start, col=1),
                                end=Position(line=line_end, col=1),
                            ),
                            evidence=Evidence(
                                summary=message,
                                extra={
                                    "complexity": complexity,
                                    "threshold": max_cognitive,
                                    "function": name,
                                },
                            ),
                        )
                    )
                    hotspots.add((rel_path, line_start, name))

        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            errors.append(_error("parse_failed", f"Failed to parse {rel_path}: {exc}"))
            continue

        visitor = _FunctionLengthVisitor()
        visitor.visit(tree)
        for span in visitor.functions:
            if span.line_count <= max_function_lines:
                continue
            long_functions += 1
            findings.append(
                _build_long_function_finding(span, rel_path, max_function_lines)
            )
            hotspots.add((rel_path, span.start_line, span.name))

    findings = sorted(findings, key=_finding_sort_key)
    metrics = ComplexityMetrics(
        hotspots=len(hotspots),
        max_cyclomatic=max_cyclomatic_seen,
        max_cognitive=max_cognitive_seen,
        long_functions=long_functions,
    )
    return findings, metrics, errors




def _build_long_function_finding(
    span: _FunctionSpan,
    rel_path: str,
    threshold: int,
) -> Finding:
    message = f"Long function ({span.line_count} lines) in '{span.name}'"
    return Finding(
        tool="refactorops",
        category="complexity",
        severity="warn",
        confidence="high",
        rule_id="complexity:long-function",
        message=message,
        location=Location(
            file=rel_path,
            start=Position(line=span.start_line, col=1),
            end=Position(line=span.end_line, col=1),
        ),
        evidence=Evidence(
            summary=message,
            extra={
                "lines": span.line_count,
                "threshold": threshold,
                "function": span.name,
            },
        ),
    )




def _finding_sort_key(finding: Finding) -> Tuple:
    return (
        finding.location.file,
        finding.location.start.line,
        finding.rule_id,
        finding.message,
    )


def _is_function_block(block: Any) -> bool:
    letter = getattr(block, "letter", "")
    if letter in {"F", "M"}:
        return True
    if getattr(block, "is_method", False):
        return True
    return False


def _format_block_name(block: Any) -> str:
    name = getattr(block, "name", "")
    classname = getattr(block, "classname", None)
    if classname:
        return f"{classname}.{name}"
    return name


def _is_python_file(path: str) -> bool:
    lower = path.lower()
    return lower.endswith(".py") or lower.endswith(".pyi") or lower.endswith(".pyw")


def _error(error_type: str, message: str) -> Dict[str, Any]:
    return {
        "type": error_type,
        "message": message,
    }


class _FunctionLengthVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.class_stack: List[str] = []
        self.func_stack: List[str] = []
        self.functions: List[_FunctionSpan] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_function(node)
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_function(node)
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    def _record_function(self, node: ast.AST) -> None:
        name = self._qualified_name(getattr(node, "name", ""))
        start_line = int(getattr(node, "lineno", 1) or 1)
        end_line = int(getattr(node, "end_lineno", start_line) or start_line)
        line_count = max(1, end_line - start_line + 1)
        self.functions.append(
            _FunctionSpan(
                name=name,
                start_line=start_line,
                end_line=end_line,
                line_count=line_count,
            )
        )

    def _qualified_name(self, name: str) -> str:
        parts = []
        if self.class_stack:
            parts.extend(self.class_stack)
        if self.func_stack:
            parts.extend(self.func_stack)
        parts.append(name)
        return ".".join([part for part in parts if part])
