#!/usr/bin/env python3
"""
Core data models for refactoring analysis using Pydantic
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ExtractableBlock(BaseModel):
    """Represents a code block that can be extracted into a function"""

    start_line: int = Field(..., description="Starting line number", gt=0)
    end_line: int = Field(..., description="Ending line number", gt=0)
    content: str = Field(..., description="Code content of the block")
    variables_used: List[str] = Field(default_factory=list, description="Variables used in the block")
    variables_modified: List[str] = Field(default_factory=list, description="Variables modified by the block")
    suggested_name: str = Field(..., description="Suggested function name")
    description: str = Field(..., description="Description of what the block does")
    complexity_score: float = Field(default=0.0, description="Complexity score", ge=0.0)
    extraction_type: Literal["function", "method", "variable"] = Field(default="function", description="Type of extraction")

    @model_validator(mode='after')
    def validate_line_numbers(self):
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self

    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()

    model_config = {"json_encoders": {}}


class RefactoringGuidance(BaseModel):
    """Complete refactoring guidance for a detected issue"""

    issue_type: str = Field(..., description="Type of refactoring issue")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Issue severity level")
    location: str = Field(..., description="Location of the issue in code")
    description: str = Field(..., description="Detailed description of the issue")
    benefits: List[str] = Field(default_factory=list, description="Benefits of applying this refactoring")
    precise_steps: List[str] = Field(default_factory=list, description="Step-by-step refactoring instructions")
    code_snippet: Optional[str] = Field(default=None, description="Relevant code snippet")
    extractable_blocks: Optional[List[ExtractableBlock]] = Field(default=None, description="Blocks that can be extracted")
    rope_suggestions: Optional[Dict[str, Any]] = Field(default=None, description="Rope refactoring suggestions")
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="Associated metrics")

    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()

    model_config = {"json_encoders": {}}