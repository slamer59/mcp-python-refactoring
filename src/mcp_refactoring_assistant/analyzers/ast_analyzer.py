#!/usr/bin/env python3
"""
AST-based pattern analyzer
"""

import ast
from typing import List

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class AstAnalyzer(BaseAnalyzer):
    """Analyzer using AST for pattern analysis"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Manual AST analysis for patterns not caught by other tools"""
        guidance_list = []
        
        if tree is None:
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return guidance_list

        # Find functions with too many parameters
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                param_count = len(node.args.args)
                if param_count > 5:
                    guidance_list.append(
                        RefactoringGuidance(
                            issue_type="too_many_parameters",
                            severity="medium",
                            location=f"Function '{node.name}' at line {node.lineno}",
                            description=f"Function has {param_count} parameters (consider max 5)",
                            benefits=[
                                "Improved function signature readability",
                                "Easier function calls",
                                "Better parameter management",
                            ],
                            precise_steps=[
                                "1. Group related parameters into a Pydantic model, dataclass or dict",
                                "2. Consider using **kwargs for optional parameters",
                                "3. Split function if it does too many things",
                                "4. Use parameter objects for complex data",
                            ],
                        )
                    )

        return guidance_list