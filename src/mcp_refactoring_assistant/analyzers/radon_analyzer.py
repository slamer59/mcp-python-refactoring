#!/usr/bin/env python3
"""
Radon-based complexity analyzer
"""

import ast
from typing import List

from radon.complexity import cc_visit
from radon.metrics import mi_visit

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class RadonAnalyzer(BaseAnalyzer):
    """Analyzer using Radon for complexity and maintainability metrics"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use Radon for complexity analysis"""
        guidance_list = []

        try:
            # Cyclomatic complexity analysis
            complexity_blocks = cc_visit(content)

            for block in complexity_blocks:
                if block.complexity > 10:  # High complexity threshold
                    guidance_list.append(
                        RefactoringGuidance(
                            issue_type="high_complexity",
                            severity="high" if block.complexity > 15 else "medium",
                            location=f"Function '{block.name}' at line {block.lineno}",
                            description=f"Function has high cyclomatic complexity: {block.complexity}",
                            benefits=[
                                "Improved readability and maintainability",
                                "Easier testing and debugging",
                                "Reduced cognitive load",
                            ],
                            precise_steps=[
                                "1. Identify decision points (if, for, while, except)",
                                "2. Look for logical groupings of conditions",
                                "3. Extract complex conditions into separate functions",
                                "4. Consider using strategy pattern for complex branching",
                                "5. Add unit tests for each extracted function",
                            ],
                            metrics={
                                "complexity": block.complexity,
                                "type": block.type,
                            },
                        )
                    )

            # Maintainability Index
            mi_score = mi_visit(content, multi=True)
            for item in mi_score:
                if item.mi < 20:  # Low maintainability
                    guidance_list.append(
                        RefactoringGuidance(
                            issue_type="low_maintainability",
                            severity="medium",
                            location=f"Function '{item.name}' at line {item.lineno}",
                            description=f"Low maintainability index: {item.mi:.1f}",
                            benefits=[
                                "Improved code maintainability",
                                "Easier future modifications",
                                "Better code quality",
                            ],
                            precise_steps=[
                                "1. Reduce function length (aim for < 20 lines)",
                                "2. Simplify complex expressions",
                                "3. Add meaningful variable names",
                                "4. Extract nested logic into helper functions",
                                "5. Add comprehensive documentation",
                            ],
                            metrics={"maintainability_index": item.mi},
                        )
                    )

        except Exception as e:
            print(f"Warning: Radon analysis failed: {e}")

        return guidance_list