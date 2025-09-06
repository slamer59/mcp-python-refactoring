#!/usr/bin/env python3
"""
Modern patterns analyzer using Refurb for code modernization suggestions
"""

import ast
import json
import subprocess
import tempfile
from typing import List

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class ModernPatternsAnalyzer(BaseAnalyzer):
    """Analyzer using Refurb for modern Python pattern suggestions"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use Refurb for modern pattern analysis"""
        guidance_list = []

        try:
            # Create temporary file for refurb analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            # Run refurb on the temporary file
            result = subprocess.run(
                ['refurb', '--format', 'json', temp_file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up temporary file
            import os
            os.unlink(temp_file_path)

            if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                if result.stdout:
                    try:
                        # Parse JSON output from refurb
                        refurb_output = result.stdout.strip()
                        if refurb_output:
                            # Refurb outputs JSON lines, one per issue
                            for line in refurb_output.split('\n'):
                                if line.strip():
                                    issue = json.loads(line)
                                    guidance_list.append(self._process_refurb_issue(issue, file_path))
                    except json.JSONDecodeError:
                        # If JSON parsing fails, try to process as text output
                        if result.stdout.strip():
                            guidance_list.append(self._process_text_output(result.stdout, file_path))
                        
            elif result.returncode == 2:
                # Refurb error occurred
                guidance_list.append(
                    RefactoringGuidance(
                        issue_type="modernization_analysis_error",
                        severity="low",
                        location=f"File {file_path}",
                        description=f"Modern patterns analysis failed: {result.stderr}",
                        benefits=["Fix syntax or analysis issues to enable modernization suggestions"],
                        precise_steps=[
                            "1. Check file syntax and structure",
                            "2. Ensure file contains valid Python code",
                            "3. Review refurb configuration if needed"
                        ]
                    )
                )

        except subprocess.TimeoutExpired:
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="modernization_analysis_timeout",
                    severity="low",
                    location=f"File {file_path}",
                    description="Modern patterns analysis timed out - file may be too large or complex",
                    benefits=["Optimize file size and complexity for better analysis"],
                    precise_steps=[
                        "1. Consider breaking large files into smaller modules",
                        "2. Reduce complexity where possible",
                        "3. Run analysis on individual functions"
                    ]
                )
            )
        except FileNotFoundError:
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="modernization_tool_missing",
                    severity="medium",
                    location="System",
                    description="Refurb modernization tool not installed",
                    benefits=["Enable modern Python pattern suggestions"],
                    precise_steps=[
                        "1. Install refurb: pip install refurb",
                        "2. Re-run modernization analysis",
                        "3. Consider integrating refurb into CI/CD pipeline"
                    ]
                )
            )
        except Exception as e:
            print(f"Warning: Modern patterns analysis failed: {e}")

        return guidance_list

    def _process_refurb_issue(self, issue: dict, file_path: str) -> RefactoringGuidance:
        """Process a single refurb issue from JSON output"""
        
        # Extract issue information
        message = issue.get('message', 'Unknown modernization opportunity')
        rule_id = issue.get('id', 'unknown')
        line = issue.get('line', 0)
        column = issue.get('column', 0)
        
        # Determine severity based on rule type
        severity = self._determine_severity(rule_id, message)
        
        return RefactoringGuidance(
            issue_type="modernization_opportunity",
            severity=severity,
            location=f"Line {line}:{column} in {file_path}",
            description=f"Modernization suggestion ({rule_id}): {message}",
            benefits=[
                "Improved code readability and maintainability",
                "Better use of modern Python features",
                "Enhanced performance where applicable",
                "Improved code consistency"
            ],
            precise_steps=self._generate_modernization_steps(rule_id, message),
            metrics={
                "rule_id": rule_id,
                "line": line,
                "column": column,
                "suggestion_type": "modernization"
            }
        )

    def _process_text_output(self, output: str, file_path: str) -> RefactoringGuidance:
        """Process refurb text output when JSON parsing fails"""
        
        return RefactoringGuidance(
            issue_type="modernization_opportunity",
            severity="medium",
            location=f"File {file_path}",
            description=f"Modernization suggestions found: {output[:200]}{'...' if len(output) > 200 else ''}",
            benefits=[
                "Improved code readability and maintainability",
                "Better use of modern Python features",
                "Enhanced code consistency"
            ],
            precise_steps=[
                "1. Review the refurb output for specific suggestions",
                "2. Apply modern Python patterns where appropriate",
                "3. Test changes thoroughly",
                "4. Update documentation if needed"
            ]
        )

    def _determine_severity(self, rule_id: str, message: str) -> str:
        """Determine severity based on refurb rule type"""
        
        # High priority modernizations
        high_priority_patterns = [
            'FURB105',  # Use print() instead of sys.stdout.write()
            'FURB107',  # Use pathlib instead of os.path
            'FURB109',  # Use dict.get() with default
            'FURB110',  # Use any() instead of for loop
            'FURB111',  # Use all() instead of for loop
            'FURB113',  # Use itertools.compress() instead of manual filtering
            'FURB118',  # Use dict comprehension instead of for loop
        ]
        
        # Medium priority modernizations
        medium_priority_patterns = [
            'FURB101',  # Use pathlib
            'FURB102',  # Use enumerate
            'FURB103',  # Use write() mode for file operations
            'FURB104',  # Use ternary operator
            'FURB106',  # Use f-strings
            'FURB108',  # Use dict methods
            'FURB112',  # Use next() builtin
            'FURB114',  # Use repeated f-strings
            'FURB115',  # Use open() with context manager
            'FURB116',  # Use isinstance() for type checking
            'FURB117',  # Use dict comprehension
            'FURB119',  # Use zip() for parallel iteration
            'FURB120',  # Use enumerate() for indexed iteration
        ]
        
        if any(pattern in rule_id for pattern in high_priority_patterns):
            return "high"
        elif any(pattern in rule_id for pattern in medium_priority_patterns):
            return "medium"
        else:
            return "low"

    def _generate_modernization_steps(self, rule_id: str, message: str) -> List[str]:
        """Generate specific modernization steps based on refurb rule"""
        
        # Specific steps for common refurb rules
        step_patterns = {
            'FURB101': [  # Use pathlib
                "1. Import pathlib.Path at the top of the file",
                "2. Replace os.path operations with Path methods",
                "3. Use Path objects for file system operations",
                "4. Update type hints to use Path where appropriate"
            ],
            'FURB102': [  # Use enumerate
                "1. Replace manual index tracking with enumerate()",
                "2. Update loop variable names appropriately",
                "3. Consider using start parameter if needed",
                "4. Test the refactored loop thoroughly"
            ],
            'FURB103': [  # Use write mode for file operations
                "1. Review file opening modes for correctness",
                "2. Use explicit modes ('r', 'w', 'a') instead of defaults",
                "3. Consider using context managers",
                "4. Ensure proper file handling"
            ],
            'FURB104': [  # Use ternary operator
                "1. Replace simple if-else with ternary operator",
                "2. Ensure readability is maintained",
                "3. Consider variable names for clarity",
                "4. Test the refactored logic"
            ],
            'FURB105': [  # Use print() instead of sys.stdout.write()
                "1. Replace sys.stdout.write() with print()",
                "2. Remove unnecessary sys import if not used elsewhere",
                "3. Use print() parameters for formatting",
                "4. Consider using logging for production code"
            ],
            'FURB106': [  # Use f-strings
                "1. Replace .format() or % formatting with f-strings",
                "2. Update variable references within the f-string",
                "3. Ensure proper escaping if needed",
                "4. Test string output for correctness"
            ],
            'FURB107': [  # Use pathlib instead of os.path
                "1. Import pathlib.Path",
                "2. Convert os.path operations to Path methods",
                "3. Update function parameters to accept Path objects",
                "4. Consider backwards compatibility if needed"
            ],
            'FURB108': [  # Use dict methods
                "1. Use dict.get() with default values",
                "2. Replace manual key checking with dict methods",
                "3. Consider using defaultdict for complex cases",
                "4. Test dictionary operations thoroughly"
            ],
            'FURB109': [  # Use dict.get() with default
                "1. Replace if-key-in-dict checks with dict.get()",
                "2. Provide appropriate default values",
                "3. Consider using dict.setdefault() for assignments",
                "4. Test default value behavior"
            ],
            'FURB110': [  # Use any() instead of for loop
                "1. Replace loop that returns True/False with any()",
                "2. Use generator expression for efficiency",
                "3. Consider readability vs performance",
                "4. Test boolean logic thoroughly"
            ],
            'FURB111': [  # Use all() instead of for loop
                "1. Replace loop that checks all conditions with all()",
                "2. Use generator expression for efficiency",
                "3. Handle empty iterables appropriately",
                "4. Test boolean logic thoroughly"
            ],
            'FURB112': [  # Use next() builtin
                "1. Replace loop that finds first match with next()",
                "2. Provide appropriate default value",
                "3. Use generator expression for efficiency",
                "4. Handle StopIteration appropriately"
            ],
            'FURB113': [  # Use itertools.compress()
                "1. Import itertools at the top of the file",
                "2. Replace manual filtering with itertools.compress()",
                "3. Ensure boolean selector sequence is correct",
                "4. Test filtering logic thoroughly"
            ],
            'FURB114': [  # Use repeated f-strings
                "1. Combine repeated string formatting into single f-string",
                "2. Consider extracting complex expressions to variables",
                "3. Ensure readability is maintained",
                "4. Test string concatenation results"
            ],
            'FURB115': [  # Use open() with context manager
                "1. Wrap file operations in with statement",
                "2. Ensure proper exception handling",
                "3. Remove manual file.close() calls",
                "4. Test file operations and cleanup"
            ],
            'FURB116': [  # Use isinstance() for type checking
                "1. Replace type() == comparisons with isinstance()",
                "2. Consider inheritance relationships",
                "3. Use tuple of types for multiple type checks",
                "4. Test type checking logic"
            ],
            'FURB117': [  # Use dict comprehension
                "1. Replace loop that builds dictionary with dict comprehension",
                "2. Consider readability vs performance",
                "3. Handle complex logic appropriately",
                "4. Test dictionary building logic"
            ],
            'FURB118': [  # Use dict comprehension instead of for loop
                "1. Convert for loop to dict comprehension",
                "2. Include appropriate filtering conditions",
                "3. Consider nested comprehensions for complex cases",
                "4. Test dictionary creation logic"
            ],
            'FURB119': [  # Use zip() for parallel iteration
                "1. Replace manual index-based iteration with zip()",
                "2. Handle iterables of different lengths appropriately",
                "3. Consider using itertools.zip_longest() if needed",
                "4. Test parallel iteration logic"
            ],
            'FURB120': [  # Use enumerate() for indexed iteration
                "1. Replace range(len()) patterns with enumerate()",
                "2. Use appropriate start parameter if needed",
                "3. Update variable names for clarity",
                "4. Test indexed iteration logic"
            ]
        }
        
        # Return specific steps if available, otherwise generic steps
        return step_patterns.get(rule_id, [
            "1. Review the modernization suggestion from refurb",
            "2. Apply the suggested modern Python pattern",
            "3. Ensure code readability and maintainability",
            "4. Test the refactored code thoroughly",
            "5. Update related documentation if needed"
        ])