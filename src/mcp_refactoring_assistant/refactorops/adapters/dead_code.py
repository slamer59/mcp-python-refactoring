"""Vulture-based dead code adapter for RefactorOps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import vulture
except ImportError:  # pragma: no cover - exercised via runtime error handling
    vulture = None

from ..schema import DeadCodeMetrics, Evidence, Finding, Location, Position


@dataclass
class _UnusedItem:
    name: str
    typ: str
    confidence: int
    filename: str
    first_lineno: int
    last_lineno: Optional[int]
    message: str


def run_dead_code_scan(
    repo_root: str,
    files: Sequence[str],
    min_confidence: int = 80,
    timeout_sec: int = 120,
    include_low_confidence: bool = False,
) -> Tuple[List[Finding], DeadCodeMetrics, List[Dict[str, Any]]]:
    """Run vulture dead code scan and map results to findings."""

    errors: List[Dict[str, Any]] = []
    if vulture is None:
        errors.append(_error("dependency_missing", "vulture is not installed"))
        return [], DeadCodeMetrics(), errors

    if not files:
        errors.append(_error("no_files", "No files provided for dead code scan"))
        return [], DeadCodeMetrics(), errors

    if timeout_sec <= 0:
        errors.append(_error("timeout", "Dead code scan timed out"))
        return [], DeadCodeMetrics(), errors

    root = Path(repo_root).resolve()
    scanner = vulture.Vulture()
    start_time = time.monotonic()
    scanned_items: List[_UnusedItem] = []

    for rel_path in files:
        if time.monotonic() - start_time > timeout_sec:
            errors.append(_error("timeout", "Dead code scan timed out"))
            break

        if not _is_python_file(rel_path):
            continue

        full_path = root / rel_path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(_error("read_failed", f"Failed to read {rel_path}: {exc}"))
            continue

        try:
            scanner.scan(content, filename=str(full_path))
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(_error("scan_failed", f"Failed to scan {rel_path}: {exc}"))
            continue

    try:
        unused_items = list(scanner.get_unused_code())
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(_error("scan_failed", f"Failed to retrieve dead code: {exc}"))
        return [], DeadCodeMetrics(), errors

    for item in unused_items:
        scanned_items.append(_normalize_item(item))

    sorted_items = sorted(scanned_items, key=_item_sort_key)
    total_count = len(sorted_items)
    high_confidence_count = len([item for item in sorted_items if item.confidence >= min_confidence])

    findings: List[Finding] = []
    for item in sorted_items:
        if item.confidence < min_confidence and not include_low_confidence:
            continue
        findings.append(_item_to_finding(item, repo_root, min_confidence))

    metrics = DeadCodeMetrics(count=total_count, high_confidence=high_confidence_count)
    return findings, metrics, errors


def _normalize_item(item: Any) -> _UnusedItem:
    name = getattr(item, "name", "")
    typ = getattr(item, "typ", "unknown")
    confidence = int(getattr(item, "confidence", 0))
    filename = getattr(item, "filename", "")
    first_lineno = int(getattr(item, "first_lineno", 1) or 1)
    last_lineno = getattr(item, "last_lineno", None)
    message = getattr(item, "message", "")
    return _UnusedItem(
        name=name,
        typ=typ,
        confidence=confidence,
        filename=filename,
        first_lineno=first_lineno,
        last_lineno=last_lineno if last_lineno is None else int(last_lineno),
        message=message,
    )


def _item_sort_key(item: _UnusedItem) -> Tuple:
    return (
        item.filename,
        item.first_lineno,
        item.last_lineno or item.first_lineno,
        item.typ,
        item.name,
    )


def _item_to_finding(item: _UnusedItem, repo_root: str, min_confidence: int) -> Finding:
    normalized_file = _normalize_filename(item.filename, repo_root)
    end_line = item.last_lineno or item.first_lineno
    confidence_label = _confidence_label(item.confidence)
    severity = "warn" if item.confidence >= min_confidence else "info"
    message = item.message or f"Unused {item.typ} '{item.name}'"
    rule_id = f"vulture:unused-{item.typ.replace(' ', '-')}"
    evidence_extra = {
        "name": item.name,
        "type": item.typ,
        "confidence_score": item.confidence,
        "raw_message": item.message,
    }

    return Finding(
        tool="vulture",
        category="dead_code",
        severity=severity,
        confidence=confidence_label,
        rule_id=rule_id,
        message=message,
        location=Location(
            file=normalized_file,
            start=Position(line=item.first_lineno, col=1),
            end=Position(line=end_line, col=1),
        ),
        evidence=Evidence(summary=message, extra=evidence_extra),
    )


def _confidence_label(confidence: int) -> str:
    if confidence >= 80:
        return "high"
    if confidence >= 60:
        return "medium"
    return "low"


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


def _is_python_file(path: str) -> bool:
    lower = path.lower()
    return lower.endswith(".py") or lower.endswith(".pyi")


def _error(error_type: str, message: str) -> Dict[str, Any]:
    return {
        "type": error_type,
        "message": message,
    }
