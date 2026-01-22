"""RefactorOps standardized schema models."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class BaseSchemaModel(BaseModel):
    """Base schema model with consistent serialization."""

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Position(BaseSchemaModel):
    """1-based position in a file."""

    line: int = Field(..., ge=1)
    col: int = Field(..., ge=1)


class Location(BaseSchemaModel):
    """Span of a finding within a file."""

    file: str
    start: Position
    end: Position


class FixEdit(BaseSchemaModel):
    """Single edit for a fix."""

    file: str
    start: Position
    end: Position
    content: str


class Fix(BaseSchemaModel):
    """Structured fix metadata."""

    kind: Literal["none", "edit", "patch", "command"] = "none"
    safe: bool = True
    edits: Optional[List[FixEdit]] = None
    command: Optional[str] = None
    notes: Optional[str] = None


class Evidence(BaseSchemaModel):
    """Supporting evidence for a finding."""

    summary: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class Finding(BaseSchemaModel):
    """Tool-agnostic normalized finding."""

    tool: str
    category: Literal[
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
    severity: Literal["error", "warn", "info"]
    confidence: Literal["high", "medium", "low"]
    rule_id: str
    message: str
    location: Location
    evidence: Evidence = Field(default_factory=Evidence)
    fix: Fix = Field(default_factory=Fix)


class HotspotRange(BaseSchemaModel):
    """Line range for a hotspot region."""

    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class Hotspot(BaseSchemaModel):
    """Hotspot summary for a file."""

    file: str
    reasons: List[str] = Field(default_factory=list)
    score: float = Field(..., ge=0.0, le=1.0)
    top_ranges: List[HotspotRange] = Field(default_factory=list)


class RuffMetrics(BaseSchemaModel):
    errors: int = Field(default=0, ge=0)
    warnings: int = Field(default=0, ge=0)
    files_scanned: int = Field(default=0, ge=0)


class DuplicationMetrics(BaseSchemaModel):
    percentage: float = Field(default=0.0, ge=0.0)
    duplicated_lines: int = Field(default=0, ge=0)
    clones: int = Field(default=0, ge=0)
    sources: int = Field(default=0, ge=0)


class DeadCodeMetrics(BaseSchemaModel):
    count: int = Field(default=0, ge=0)
    high_confidence: int = Field(default=0, ge=0)


class ComplexityMetrics(BaseSchemaModel):
    hotspots: int = Field(default=0, ge=0)
    max_cyclomatic: int = Field(default=0, ge=0)
    max_cognitive: int = Field(default=0, ge=0)
    long_functions: int = Field(default=0, ge=0)


class Metrics(BaseSchemaModel):
    ruff: RuffMetrics = Field(default_factory=RuffMetrics)
    duplication: DuplicationMetrics = Field(default_factory=DuplicationMetrics)
    dead_code: DeadCodeMetrics = Field(default_factory=DeadCodeMetrics)
    complexity: ComplexityMetrics = Field(default_factory=ComplexityMetrics)


class ScopeGit(BaseSchemaModel):
    base: str
    head: str


class ScopeSpec(BaseSchemaModel):
    type: Literal["repo", "changed", "paths"]
    paths: List[str] = Field(default_factory=list)
    git: Optional[ScopeGit] = None


class Budgets(BaseSchemaModel):
    timeout_sec: int = Field(default=120, ge=1)
    max_findings: int = Field(default=2000, ge=1)


class RunInfo(BaseSchemaModel):
    id: str
    timestamp: str
    repo_root: str
    scope: ScopeSpec
    budgets: Budgets = Field(default_factory=Budgets)


class Summary(BaseSchemaModel):
    status: Literal["pass", "warn", "fail"]
    gate_reasons: List[str] = Field(default_factory=list)


class RepoQualityResult(BaseSchemaModel):
    run: RunInfo
    metrics: Metrics = Field(default_factory=Metrics)
    findings: List[Finding] = Field(default_factory=list)
    hotspots: List[Hotspot] = Field(default_factory=list)
    summary: Summary
