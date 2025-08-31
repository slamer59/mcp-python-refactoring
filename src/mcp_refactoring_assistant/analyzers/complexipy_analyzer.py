#!/usr/bin/env python3
"""
Complexipy-based cognitive complexity analyzer
"""

import ast
import os
import subprocess
import tempfile
from typing import List

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class ComplexipyAnalyzer(BaseAnalyzer):
    """Analyzer using Complexipy for cognitive complexity analysis"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use Complexipy for cognitive complexity analysis"""
        guidance_list = []
        
        try:
            # Create a temporary file for complexipy analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Run complexipy analysis
                result = subprocess.run(
                    ["python", "-m", "complexipy", temp_file_path], 
                    capture_output=True, text=True, cwd="."
                )
                
                if result.returncode == 0 and result.stdout:
                    # Parse complexipy output for cognitive complexity issues
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'cognitive complexity' in line.lower() and any(char.isdigit() for char in line):
                            # Extract function name and complexity value
                            parts = line.split()
                            if len(parts) >= 3:
                                try:
                                    complexity = int(''.join(filter(str.isdigit, line)))
                                    if complexity > 15:  # High cognitive complexity threshold
                                        function_name = parts[0] if parts[0] != 'Function' else parts[1]
                                        guidance_list.append(
                                            RefactoringGuidance(
                                                issue_type="high_cognitive_complexity",
                                                severity="medium",
                                                location=f"Function '{function_name}' in {file_path}",
                                                description=f"High cognitive complexity ({complexity}). This function is hard to understand.",
                                                precise_steps=[
                                                    f"Break down complex logic in '{function_name}'",
                                                    "Extract nested loops and conditions",
                                                    "Use descriptive variable names for complex expressions",
                                                    f"Target: Reduce cognitive complexity from {complexity} to under 15",
                                                    "Consider using guard clauses and early returns"
                                                ],
                                                benefits=[
                                                    "Improved code comprehension",
                                                    "Easier debugging and maintenance",
                                                    "Better code review experience"
                                                ]
                                            )
                                        )
                                except ValueError:
                                    continue
                                    
            finally:
                # Clean up temp file
                os.unlink(temp_file_path)
                
        except Exception as e:
            print(f"Warning: Complexipy analysis failed: {e}")
        
        return guidance_list