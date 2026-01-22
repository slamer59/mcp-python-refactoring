"""RefactorOps core package."""

from .dedup import deduplicate_findings
from .exec import CommandResult, run_command
from .scope import ResolvedScope, resolve_scope
from .schema import (
    Budgets,
    ComplexityMetrics,
    DeadCodeMetrics,
    DuplicationMetrics,
    Evidence,
    Finding,
    Fix,
    FixEdit,
    Hotspot,
    HotspotRange,
    Location,
    Metrics,
    Position,
    RepoQualityResult,
    RuffMetrics,
    RunInfo,
    ScopeGit,
    ScopeSpec,
    Summary,
)

__all__ = [
    "Budgets",
    "ComplexityMetrics",
    "DeadCodeMetrics",
    "DuplicationMetrics",
    "Evidence",
    "Finding",
    "Fix",
    "FixEdit",
    "Hotspot",
    "HotspotRange",
    "Location",
    "Metrics",
    "Position",
    "RepoQualityResult",
    "RuffMetrics",
    "RunInfo",
    "ScopeGit",
    "ScopeSpec",
    "Summary",
    "CommandResult",
    "deduplicate_findings",
    "ResolvedScope",
    "run_command",
    "resolve_scope",
]
