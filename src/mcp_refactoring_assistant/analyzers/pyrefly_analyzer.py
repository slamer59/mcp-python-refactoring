#!/usr/bin/env python3
"""
Pyrefly-based type checking analyzer
"""

import ast
import os
import subprocess
import tempfile
from typing import List

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class PyreflyAnalyzer(BaseAnalyzer):
    """Analyzer using Pyrefly for type checking and quality analysis"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use pyrefly for type checking and quality analysis"""
        guidance_list = []

        try:
            # Save content to temp file for pyrefly analysis
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(content)
                temp_file = f.name

            try:
                # Run pyrefly check on the temp file
                result = subprocess.run(
                    ["pyrefly", "check", temp_file], capture_output=True, text=True
                )

                if result.returncode != 0 and result.stdout:
                    # Parse pyrefly output for issues
                    issues = self._parse_pyrefly_output(result.stdout)

                    if issues:
                        guidance_list.append(
                            RefactoringGuidance(
                                issue_type="type_errors",
                                severity="medium",
                                location=f"{len(issues)} type issues found",
                                description=f"Pyrefly found {len(issues)} type-related issues that could affect code quality",
                                precise_steps=[
                                    "🔍 TYPE CHECKING ISSUES FOUND:",
                                    *[
                                        f"• {issue}" for issue in issues[:5]
                                    ],  # Show first 5
                                    "Run 'pyrefly check' for full details",
                                    "Fix type annotations and variable assignments",
                                    "Consider adding type hints for better code quality",
                                ],
                                benefits=[
                                    "Improved code reliability",
                                    "Better IDE support",
                                    "Easier debugging",
                                    "Enhanced maintainability",
                                ],
                            )
                        )

            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            # Don't fail the whole analysis if pyrefly has issues
            pass

        return guidance_list

    def _parse_pyrefly_output(self, output: str) -> List[str]:
        """Parse pyrefly output to extract meaningful issues"""
        issues = []
        lines = output.split("\n")

        for line in lines:
            if "ERROR" in line and "[" in line and "]" in line:
                # Extract error type and basic info
                parts = line.split("[")
                if len(parts) > 1:
                    error_type = parts[-1].replace("]", "").strip()
                    if error_type not in ["import-error"]:  # Skip import errors
                        # Clean up the error message
                        clean_line = line.replace("ERROR", "").strip()
                        if "-->" in clean_line:
                            clean_line = clean_line.split("-->")[0].strip()
                        issues.append(
                            f"{error_type.replace('-', ' ').title()}: {clean_line}"
                        )

        return issues[:10]  # Limit to 10 issues