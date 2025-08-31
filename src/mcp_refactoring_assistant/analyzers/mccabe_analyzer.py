#!/usr/bin/env python3
"""
McCabe-based cyclomatic complexity analyzer
"""

import ast
import contextlib
import io
import os
import tempfile
from typing import List

import mccabe

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class McCabeAnalyzer(BaseAnalyzer):
    """Analyzer using McCabe for cyclomatic complexity analysis"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use McCabe for cyclomatic complexity analysis"""
        guidance_list = []
        
        try:
            # Create a temporary file for McCabe analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Capture McCabe output
                output_buffer = io.StringIO()
                with contextlib.redirect_stdout(output_buffer):
                    mccabe.get_code_complexity(content, threshold=10)
                
                output = output_buffer.getvalue()
                
                # Parse the output to extract complexity information
                lines = output.strip().split('\n')
                for line in lines:
                    if line and 'C901' in line and 'too complex' in line:
                        # Parse format: "stdin:33:1: C901 'extremely_complex_function' is too complex (44)"
                        parts = line.split(':')
                        if len(parts) >= 4:
                            try:
                                line_number = int(parts[1])
                                message_part = ':'.join(parts[3:]).strip()
                                
                                # Extract function name and complexity from message
                                if "'" in message_part:
                                    func_start = message_part.find("'") + 1
                                    func_end = message_part.find("'", func_start)
                                    function_name = message_part[func_start:func_end]
                                    
                                    # Extract complexity number
                                    if '(' in message_part and ')' in message_part:
                                        complexity_start = message_part.rfind('(') + 1
                                        complexity_end = message_part.rfind(')')
                                        complexity = int(message_part[complexity_start:complexity_end])
                                        
                                        guidance_list.append(
                                            RefactoringGuidance(
                                                issue_type="high_cyclomatic_complexity",
                                                severity="high",
                                                location=f"Function '{function_name}' at line {line_number} in {file_path}",
                                                description=f"High cyclomatic complexity ({complexity}). Consider breaking down this function.",
                                                precise_steps=[
                                                    f"Function has {complexity} different execution paths (recommended: ≤10)",
                                                    "Look for nested if/elif/else statements and loops",
                                                    "Extract complex conditional logic into separate functions",
                                                    "Use early returns to reduce nesting levels",
                                                    "Consider the Single Responsibility Principle"
                                                ],
                                                benefits=[
                                                    "Improved code readability and maintainability",
                                                    "Easier testing with fewer code paths",
                                                    "Reduced cognitive load for developers",
                                                    "Better debugging experience"
                                                ]
                                            )
                                        )
                            except (ValueError, IndexError):
                                continue
                    
            finally:
                # Clean up temp file
                os.unlink(temp_file_path)
        
        except Exception as e:
            print(f"Warning: McCabe analysis failed: {e}")
        
        return guidance_list