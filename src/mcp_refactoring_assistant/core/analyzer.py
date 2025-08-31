#!/usr/bin/env python3
"""
Enhanced refactoring analyzer orchestrator
"""

import ast
import tempfile
from typing import List, Optional

from ..models import RefactoringGuidance
from ..analyzers import (
    RadonAnalyzer,
    RopeAnalyzer,
    VultureAnalyzer,
    PyreflyAnalyzer,
    McCabeAnalyzer,
    ComplexipyAnalyzer,
    StructureAnalyzer,
    AstAnalyzer,
)


class EnhancedRefactoringAnalyzer:
    """Professional refactoring analyzer orchestrating multiple third-party libraries"""

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = project_path or tempfile.mkdtemp()
        
        # Initialize all analyzers
        self.analyzers = [
            RadonAnalyzer(),
            VultureAnalyzer(),
            PyreflyAnalyzer(),
            McCabeAnalyzer(),
            ComplexipyAnalyzer(),
            StructureAnalyzer(),
            AstAnalyzer(),
            RopeAnalyzer(),  # Initialize last as it needs project setup
        ]

    def analyze_file(self, file_path: str, content: str) -> List[RefactoringGuidance]:
        """Comprehensive file analysis using all available tools"""
        guidance_list = []

        try:
            # Parse AST once for efficiency
            tree = ast.parse(content)
            
            # Run all analyzers
            for analyzer in self.analyzers:
                try:
                    analyzer_guidance = analyzer._safe_analyze(content, file_path, tree)
                    guidance_list.extend(analyzer_guidance)
                except Exception as e:
                    print(f"Warning: {analyzer.name} failed: {e}")
                    continue

        except SyntaxError as e:
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="syntax_error",
                    severity="critical",
                    location=f"Line {e.lineno}",
                    description=f"Syntax error prevents analysis: {e}",
                    benefits=["Enable proper code analysis"],
                    precise_steps=[
                        "Fix syntax error before proceeding with refactoring"
                    ],
                )
            )

        return guidance_list