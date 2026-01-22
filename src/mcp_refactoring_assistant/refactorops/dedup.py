"""Finding deduplication helpers."""

import hashlib
from typing import Dict, List, Tuple

from .schema import Finding


def _message_hash(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def _sort_key(finding: Finding) -> Tuple:
    return (
        finding.location.file,
        finding.location.start.line,
        finding.location.start.col,
        finding.category,
        finding.severity,
        finding.rule_id,
        finding.tool,
        finding.message,
    )


def _dedup_key(finding: Finding) -> Tuple:
    if finding.rule_id:
        return (
            finding.category,
            finding.location.file,
            finding.location.start.line,
            finding.rule_id,
        )

    return (
        finding.category,
        finding.location.file,
        finding.location.start.line,
        _message_hash(finding.message),
    )


def _merge_evidence(primary: Finding, duplicate: Finding) -> None:
    merged_entry = {
        "tool": duplicate.tool,
        "category": duplicate.category,
        "severity": duplicate.severity,
        "confidence": duplicate.confidence,
        "rule_id": duplicate.rule_id,
        "message": duplicate.message,
        "location": duplicate.location.to_dict(),
        "evidence": duplicate.evidence.to_dict(),
        "fix": duplicate.fix.to_dict(),
    }

    merged_list = primary.evidence.extra.setdefault("merged", [])
    merged_list.append(merged_entry)


def deduplicate_findings(findings: List[Finding]) -> List[Finding]:
    """Deduplicate findings using category/file/start/rule_id priority."""

    if not findings:
        return []

    sorted_findings = sorted(findings, key=_sort_key)
    unique: Dict[Tuple, Finding] = {}
    result: List[Finding] = []

    for finding in sorted_findings:
        key = _dedup_key(finding)
        existing = unique.get(key)
        if existing is None:
            unique[key] = finding
            result.append(finding)
            continue

        _merge_evidence(existing, finding)

    return result
