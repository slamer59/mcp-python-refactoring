#!/usr/bin/env python3
"""
File structure analyzer for splitting large files
"""

import ast
from typing import List

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class StructureAnalyzer(BaseAnalyzer):
    """Analyzer for file structure and organization"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Analyze file structure and recommend splitting large files"""
        guidance_list = []
        
        try:
            lines = content.split('\n')
            line_count = len(lines)
            
            if tree is None:
                tree = ast.parse(content)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append({
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': getattr(node, 'end_lineno', node.lineno),
                        'methods': len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                    })
                elif isinstance(node, ast.FunctionDef) and not any(node.lineno >= cls['line_start'] and node.lineno <= cls['line_end'] for cls in classes):
                    # Only count top-level functions (not methods)
                    functions.append({
                        'name': node.name,
                        'line_start': node.lineno,
                        'line_end': getattr(node, 'end_lineno', node.lineno)
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(node.lineno)
            
            # Large file analysis (>500 lines)
            if line_count > 500:
                splitting_suggestions = []
                
                # Suggest splitting by classes if there are many
                if len(classes) > 3:
                    splitting_suggestions.extend([
                        f"Extract class '{cls['name']}' (lines {cls['line_start']}-{cls['line_end']}) to separate module",
                        f"Consider creating '{cls['name'].lower()}.py'"
                    ] for cls in classes[:3])
                
                # Suggest splitting by related functions
                if len(functions) > 10:
                    splitting_suggestions.extend([
                        "Group related utility functions into separate modules",
                        "Consider creating separate files for different functional areas",
                        f"You have {len(functions)} top-level functions - consider organizing into modules"
                    ])
                
                guidance_list.append(
                    RefactoringGuidance(
                        issue_type="large_file",
                        severity="medium",
                        location=f"File {file_path} ({line_count} lines)",
                        description=f"Large file ({line_count} lines) with {len(classes)} classes and {len(functions)} functions. Consider splitting.",
                        precise_steps=[
                            f"File has {line_count} lines (recommended: <500 lines)",
                            f"Contains {len(classes)} classes and {len(functions)} top-level functions",
                            "Identify logical groupings of classes and functions",
                            *splitting_suggestions[:5],  # Limit suggestions
                            "Update imports after splitting files"
                        ],
                        benefits=[
                            "Improved code organization and navigation",
                            "Faster IDE performance and loading times",
                            "Better separation of concerns",
                            "Easier testing and maintenance"
                        ]
                    )
                )
            
            # Too many imports analysis
            if len(imports) > 20:
                guidance_list.append(
                    RefactoringGuidance(
                        issue_type="too_many_imports",
                        severity="low",
                        location=f"File {file_path}",
                        description=f"High number of imports ({len(imports)}). Consider restructuring dependencies.",
                        precise_steps=[
                            f"File has {len(imports)} import statements",
                            "Review if all imports are actually used",
                            "Group related functionality to reduce import count",
                            "Consider creating utility modules for common imports",
                            "Use import organization tools (isort, black)"
                        ],
                        benefits=[
                            "Cleaner file headers",
                            "Reduced coupling between modules",
                            "Faster import resolution"
                        ]
                    )
                )
                
        except Exception as e:
            print(f"Warning: Structure analysis failed: {e}")
            
        return guidance_list