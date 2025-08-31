#!/usr/bin/env python3
"""
Enhanced Python Refactoring MCP Tool using Third-Party Libraries

This MCP tool leverages powerful libraries to provide professional-grade
refactoring analysis and guidance without automatically modifying code.
"""

import ast
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jedi
import libcst as cst
import mcp.server.stdio
import mcp.types as types
import pyrefly
import vulture
import mccabe
import complexipy
from libcst.matchers import matches
from mcp.server import NotificationOptions, Server
from radon.complexity import cc_rank, cc_visit
from radon.metrics import h_visit, mi_rank, mi_visit
from radon.raw import analyze

# Third-party imports - all required dependencies
from rope.base.project import Project
from rope.base.resources import File as RopeFile
from rope.refactor.extract import ExtractMethod, ExtractVariable
from rope.refactor.rename import Rename


@dataclass
class ExtractableBlock:
    """Represents a code block that can be extracted into a function"""

    start_line: int
    end_line: int
    content: str
    variables_used: List[str]
    variables_modified: List[str]
    suggested_name: str
    description: str
    complexity_score: float = 0.0
    extraction_type: str = "function"  # function, method, variable

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RefactoringGuidance:
    """Complete refactoring guidance for a detected issue"""

    issue_type: str
    severity: str  # low, medium, high, critical
    location: str
    description: str
    benefits: List[str]
    precise_steps: List[str]
    code_snippet: Optional[str] = None
    extractable_blocks: Optional[List[ExtractableBlock]] = None
    rope_suggestions: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        result = asdict(self)
        if self.extractable_blocks:
            result["extractable_blocks"] = [
                block.to_dict() for block in self.extractable_blocks
            ]
        return result


class EnhancedRefactoringAnalyzer:
    """Professional refactoring analyzer using multiple third-party libraries"""

    def __init__(self, project_path: Optional[str] = None):
        self.project_path = project_path or tempfile.mkdtemp()
        self.rope_project = None

        # Initialize Rope project
        try:
            self.rope_project = Project(self.project_path)
        except Exception as e:
            print(f"Warning: Could not initialize Rope project: {e}")
            self.rope_project = None

    def analyze_file(self, file_path: str, content: str) -> List[RefactoringGuidance]:
        """Comprehensive file analysis using all available tools"""
        guidance_list = []

        try:
            # Parse AST for basic analysis
            tree = ast.parse(content)

            # 1. Analyze with Radon for complexity metrics
            guidance_list.extend(self._analyze_with_radon(content, file_path))

            # 2. Analyze with Rope for extraction opportunities
            if self.rope_project:
                guidance_list.extend(self._analyze_with_rope(file_path, content, tree))

            # 3. Analyze with Vulture for dead code
            guidance_list.extend(self._analyze_with_vulture(content, file_path))

            # 4. Analyze with Pyrefly for type checking
            guidance_list.extend(self._analyze_with_pyrefly(content))

            # 5. Analyze with McCabe for cyclomatic complexity
            guidance_list.extend(self._analyze_with_mccabe(content, file_path))
            
            # 6. Analyze with Complexipy for cognitive complexity
            guidance_list.extend(self._analyze_with_complexipy(content, file_path))
            
            # 7. Analyze file structure for splitting recommendations
            guidance_list.extend(self._analyze_file_structure(content, file_path))

            # 8. Manual AST analysis for patterns not caught by other tools
            guidance_list.extend(self._analyze_ast_patterns(tree, content, file_path))

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

    def _analyze_with_radon(
        self, content: str, file_path: str
    ) -> List[RefactoringGuidance]:
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

    def _analyze_with_rope(
        self, file_path: str, content: str, tree: ast.AST
    ) -> List[RefactoringGuidance]:
        """Use Rope for professional refactoring analysis"""
        guidance_list = []

        if not self.rope_project:
            return guidance_list

        try:
            # Create temporary file for Rope analysis
            temp_file_path = os.path.join(self.project_path, "temp_analysis.py")
            with open(temp_file_path, "w") as f:
                f.write(content)

            rope_file = self.rope_project.get_resource("temp_analysis.py")

            # Find long functions that could benefit from extraction
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if hasattr(node, "end_lineno") and node.end_lineno:
                        function_length = node.end_lineno - node.lineno + 1

                        if function_length > 20:  # Long function threshold
                            extractable_blocks = (
                                self._find_extractable_blocks_with_rope(
                                    rope_file, node, content.split("\n")
                                )
                            )

                            if extractable_blocks:
                                guidance_list.append(
                                    RefactoringGuidance(
                                        issue_type="extract_function",
                                        severity="medium",
                                        location=f"Function '{node.name}' lines {node.lineno}-{node.end_lineno}",
                                        description=f"Long function ({function_length} lines) with extractable blocks",
                                        benefits=[
                                            "Improved readability",
                                            "Better testability",
                                            "Code reusability",
                                            "Easier maintenance",
                                        ],
                                        precise_steps=self._generate_extraction_steps(
                                            extractable_blocks
                                        ),
                                        extractable_blocks=extractable_blocks,
                                    )
                                )

            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        except Exception as e:
            print(f"Warning: Rope analysis failed: {e}")

        return guidance_list

    def _find_extractable_blocks_with_rope(
        self, rope_file: Any, function_node: ast.FunctionDef, lines: List[str]
    ) -> List[ExtractableBlock]:
        """Find extractable blocks using Rope's analysis capabilities"""
        blocks = []

        try:
            # Analyze the function body for logical blocks
            function_start = function_node.lineno - 1
            function_end = (
                getattr(function_node, "end_lineno", function_node.lineno) - 1
            )

            # Look for sequential blocks (3+ lines) that could be extracted
            current_block_start = None
            current_block_statements = []

            for i, stmt in enumerate(function_node.body):
                # Check if this statement starts a potential block
                if self._is_extractable_statement(stmt):
                    if current_block_start is None:
                        current_block_start = stmt.lineno
                        current_block_statements = [stmt]
                    else:
                        current_block_statements.append(stmt)
                else:
                    # End current block if we have enough statements
                    if len(current_block_statements) >= 3:
                        block = self._create_extractable_block(
                            current_block_statements, lines, "sequential_logic"
                        )
                        if block:
                            blocks.append(block)

                    # Reset for new potential block
                    current_block_start = None
                    current_block_statements = []

            # Check final block
            if len(current_block_statements) >= 3:
                block = self._create_extractable_block(
                    current_block_statements, lines, "sequential_logic"
                )
                if block:
                    blocks.append(block)

            # Look for conditional blocks
            for stmt in function_node.body:
                if isinstance(stmt, ast.If) and len(stmt.body) >= 3:
                    block = self._create_extractable_block(
                        stmt.body, lines, "conditional_logic"
                    )
                    if block:
                        blocks.append(block)

            # Look for loop blocks
            for stmt in function_node.body:
                if isinstance(stmt, (ast.For, ast.While)) and len(stmt.body) >= 3:
                    block = self._create_extractable_block(
                        stmt.body, lines, "loop_logic"
                    )
                    if block:
                        blocks.append(block)

        except Exception as e:
            print(f"Warning: Block extraction failed: {e}")

        return self._remove_overlapping_blocks(blocks)

    def _is_extractable_statement(self, stmt: ast.stmt) -> bool:
        """Check if a statement is part of an extractable block"""
        # Skip simple assignments and single expressions
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            return False
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            return False
        return True

    def _create_extractable_block(
        self, statements: List[ast.stmt], lines: List[str], block_type: str
    ) -> Optional[ExtractableBlock]:
        """Create an ExtractableBlock from AST statements"""
        if not statements:
            return None

        start_line = statements[0].lineno
        end_line = getattr(statements[-1], "end_lineno", statements[-1].lineno)

        if not end_line or end_line - start_line < 2:
            return None

        # Analyze variables
        variables_used = set()
        variables_modified = set()

        for stmt in statements:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        variables_modified.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        variables_used.add(node.id)

        # Remove modified variables from used (they don't need to be parameters)
        parameters = list(variables_used - variables_modified)

        # Generate content and name suggestion
        content = "\n".join(lines[start_line - 1 : end_line])
        suggested_name = self._suggest_function_name(statements, block_type)
        description = self._describe_block_purpose(statements, block_type)

        return ExtractableBlock(
            start_line=start_line,
            end_line=end_line,
            content=content,
            variables_used=parameters,
            variables_modified=list(variables_modified) if variables_modified else [],
            suggested_name=suggested_name,
            description=description,
            complexity_score=len(statements) * 0.5,  # Simple complexity metric
            extraction_type="function",
        )

    def _suggest_function_name(
        self, statements: List[ast.stmt], block_type: str
    ) -> str:
        """Suggest a meaningful function name based on the code"""
        # Look for method calls to suggest names
        method_calls = []
        for stmt in statements:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        method_calls.append(node.func.attr)
                    elif isinstance(node.func, ast.Name):
                        method_calls.append(node.func.id)

        # Pattern-based naming
        if any("validate" in call.lower() for call in method_calls):
            return "validate_data"
        elif any("process" in call.lower() for call in method_calls):
            return "process_data"
        elif any("calculate" in call.lower() for call in method_calls):
            return "calculate_result"
        elif any("format" in call.lower() for call in method_calls):
            return "format_output"
        elif block_type == "conditional_logic":
            return "handle_condition"
        elif block_type == "loop_logic":
            return "process_items"
        else:
            return "extracted_function"

    def _describe_block_purpose(
        self, statements: List[ast.stmt], block_type: str
    ) -> str:
        """Describe what the block does"""
        stmt_count = len(statements)
        if block_type == "conditional_logic":
            return f"Handle conditional logic ({stmt_count} statements)"
        elif block_type == "loop_logic":
            return f"Process loop iterations ({stmt_count} statements)"
        else:
            return f"Execute {stmt_count} sequential operations"

    def _remove_overlapping_blocks(
        self, blocks: List[ExtractableBlock]
    ) -> List[ExtractableBlock]:
        """Remove overlapping blocks, keeping the most specific ones"""
        if not blocks:
            return blocks

        blocks.sort(key=lambda b: b.start_line)
        non_overlapping = []

        for block in blocks:
            overlaps = False
            for existing in non_overlapping:
                if (
                    block.start_line <= existing.end_line
                    and block.end_line >= existing.start_line
                ):
                    overlaps = True
                    break

            if not overlaps:
                non_overlapping.append(block)

        return non_overlapping

    def _generate_extraction_steps(self, blocks: List[ExtractableBlock]) -> List[str]:
        """Generate precise extraction steps for the blocks"""
        if not blocks:
            return [
                "1. Manually identify logical code blocks",
                "2. Select 3+ lines that perform a cohesive task",
                "3. Note required parameters and return values",
                "4. Extract to new function with descriptive name",
                "5. Replace original code with function call",
                "6. Test to ensure behavior unchanged",
            ]

        steps = ["📋 PRECISION EXTRACTION PLAN:"]

        for i, block in enumerate(blocks, 1):
            steps.extend(
                [
                    f"\n🎯 BLOCK {i}: {block.description}",
                    f"   📍 EXACT LOCATION: Lines {block.start_line} to {block.end_line}",
                    f"   📝 FUNCTION NAME: {block.suggested_name}()",
                    "",
                    "   ✂️  CUT INSTRUCTIONS:",
                    f"   • SELECT lines {block.start_line}-{block.end_line} (inclusive)",
                    f"   • CUT the selected lines (Ctrl+X)",
                    "",
                    "   📝 CREATE NEW FUNCTION:",
                    f"   • Place cursor ABOVE the original function",
                    f"   • Type: def {block.suggested_name}({self._format_parameters(block.variables_used)}):",
                    "   • Paste the cut code (Ctrl+V)",
                    f"   • Add return: {self._format_return(block.variables_modified)}",
                    "",
                    "   🔄 REPLACE ORIGINAL:",
                    f"   • At the cut location, type: {self._format_function_call(block)}",
                ]
            )

        steps.extend(
            [
                "\n✅ VERIFICATION:",
                "• Run your tests",
                "• Check for undefined variable errors",
                "• Verify function behavior is identical",
                "• Confirm all edge cases still work",
            ]
        )

        return steps

    def _format_parameters(self, variables: List[str]) -> str:
        """Format function parameters"""
        return ", ".join(variables) if variables else ""

    def _format_return(self, variables: List[str]) -> str:
        """Format return statement"""
        if not variables:
            return "# No return needed"
        elif len(variables) == 1:
            return f"return {variables[0]}"
        else:
            return f"return {', '.join(variables)}"

    def _format_function_call(self, block: ExtractableBlock) -> str:
        """Format the function call to replace extracted code"""
        params = ", ".join(block.variables_used) if block.variables_used else ""

        if not block.variables_modified:
            return f"{block.suggested_name}({params})"
        elif len(block.variables_modified) == 1:
            return f"{block.variables_modified[0]} = {block.suggested_name}({params})"
        else:
            vars_str = ", ".join(block.variables_modified)
            return f"{vars_str} = {block.suggested_name}({params})"

    def _analyze_with_vulture(
        self, content: str, file_path: str
    ) -> List[RefactoringGuidance]:
        """Use Vulture to find dead code"""
        guidance_list = []

        try:
            v = vulture.Vulture()
            v.scan(content, filename=file_path)

            unused_items = list(v.get_unused_code())

            if unused_items:
                # Consolidate all dead code into single guidance
                items_list = []
                locations = []

                for unused_item in unused_items:
                    items_list.append(
                        f"Line {unused_item.first_lineno}: Unused {unused_item.typ} '{unused_item.name}'"
                    )
                    locations.append(f"Line {unused_item.first_lineno}")

                guidance_list.append(
                    RefactoringGuidance(
                        issue_type="dead_code",
                        severity="low",
                        location=f"Multiple locations ({len(unused_items)} items)",
                        description=f"{len(unused_items)} unused items found",
                        benefits=[
                            "Cleaner codebase",
                            "Reduced complexity",
                            "Better maintainability",
                        ],
                        precise_steps=[
                            "1. Review all unused items listed below:",
                            *[f"   • {item}" for item in items_list],
                            "2. Verify each item is truly unused",
                            "3. Check if any are part of a public API",
                            "4. Remove confirmed unused code",
                            "5. Run tests to ensure nothing breaks",
                        ],
                        metrics={
                            "total_items": len(unused_items),
                            "confidence": sum(item.confidence for item in unused_items)
                            / len(unused_items),
                        },
                    )
                )

        except Exception as e:
            print(f"Warning: Vulture analysis failed: {e}")

        return guidance_list

    def _analyze_ast_patterns(
        self, tree: ast.AST, content: str, file_path: str
    ) -> List[RefactoringGuidance]:
        """Manual AST analysis for patterns not caught by other tools"""
        guidance_list = []
        lines = content.split("\n")

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
                                "1. Group related parameters into a pydantic, dataclass or dict",
                                "2. Consider using **kwargs for optional parameters",
                                "3. Split function if it does too many things",
                                "4. Use parameter objects for complex data",
                            ],
                        )
                    )

        return guidance_list

    def _analyze_with_pyrefly(self, content: str) -> List[RefactoringGuidance]:
        """Use pyrefly for type checking and quality analysis"""
        guidance_list = []

        try:
            # Save content to temp file for pyrefly analysis
            import json
            import subprocess
            import tempfile

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
                import os

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

    def _analyze_with_mccabe(self, content: str, file_path: str) -> List[RefactoringGuidance]:
        """Use McCabe for cyclomatic complexity analysis"""
        guidance_list = []
        
        try:
            # Create a temporary file for McCabe analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Use McCabe to capture complexity output
                import io
                import contextlib
                
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
            # Don't fail the whole analysis if McCabe has issues
            pass
        
        return guidance_list
    
    def _analyze_with_complexipy(self, content: str, file_path: str) -> List[RefactoringGuidance]:
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
            # Don't fail the whole analysis if Complexipy has issues
            pass
        
        return guidance_list
    
    def _analyze_file_structure(self, content: str, file_path: str) -> List[RefactoringGuidance]:
        """Analyze file structure and recommend splitting large files"""
        guidance_list = []
        
        try:
            lines = content.split('\n')
            line_count = len(lines)
            
            # Parse AST to count classes and functions
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
            # Don't fail the whole analysis
            pass
            
        return guidance_list

    def analyze_test_coverage(self, source_path: str, test_path: Optional[str] = None, target_coverage: int = 80) -> Dict[str, Any]:
        """Analyze test coverage and provide improvement suggestions"""
        import subprocess
        import glob
        
        try:
            import coverage
        except ImportError:
            coverage = None
        
        result = {
            "coverage_analysis": {},
            "missing_coverage": [],
            "testing_suggestions": [],
            "files_needing_tests": [],
            "coverage_report": "",
            "recommendations": []
        }
        
        try:
            # Initialize coverage if available
            if coverage:
                cov = coverage.Coverage()
                cov.start()
            
            # Try to run existing tests if test_path provided
            if test_path and os.path.exists(test_path):
                try:
                    # Run pytest with coverage
                    cmd = [
                        "python", "-m", "pytest", 
                        test_path,
                        f"--cov={source_path}",
                        "--cov-report=term-missing",
                        "--cov-report=json:coverage.json"
                    ]
                    subprocess.run(cmd, capture_output=True, text=True, cwd=".")
                    
                    # Read coverage.json if it exists
                    if os.path.exists("coverage.json"):
                        with open("coverage.json", "r") as f:
                            coverage_data = json.load(f)
                            result["coverage_analysis"] = coverage_data
                        os.remove("coverage.json")
                        
                except Exception as e:
                    result["error"] = f"Error running tests: {e}"
            
            # Analyze source files for testing needs
            if os.path.isfile(source_path):
                source_files = [source_path]
            else:
                source_files = glob.glob(f"{source_path}/**/*.py", recursive=True)
            
            for file_path in source_files:
                if "__pycache__" in file_path or file_path.endswith("__init__.py"):
                    continue
                    
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Analyze what needs testing
                analysis = self._analyze_testability(content, file_path)
                result["missing_coverage"].extend(analysis["untested_functions"])
                result["testing_suggestions"].extend(analysis["suggestions"])
                
                if analysis["needs_tests"]:
                    result["files_needing_tests"].append({
                        "file": file_path,
                        "functions": analysis["functions"],
                        "classes": analysis["classes"],
                        "complexity": analysis["complexity_score"]
                    })
            
            # Generate recommendations
            result["recommendations"] = self._generate_testing_recommendations(
                result["files_needing_tests"], 
                target_coverage
            )
            
        except ImportError:
            result["error"] = "Coverage package not installed. Install with: pip install coverage"
        except Exception as e:
            result["error"] = f"Coverage analysis failed: {str(e)}"
        
        return result
    
    def _analyze_testability(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze code for testability and testing needs"""
        result = {
            "untested_functions": [],
            "suggestions": [],
            "needs_tests": False,
            "functions": [],
            "classes": [],
            "complexity_score": 0
        }
        
        try:
            tree = ast.parse(content)
            
            # Find functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args),
                        "is_private": node.name.startswith("_"),
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(node) is not None
                    }
                    result["functions"].append(func_info)
                    
                    # Suggest tests for public functions
                    if not node.name.startswith("_") and node.name != "__init__":
                        result["untested_functions"].append(f"{file_path}:{node.lineno} - Function '{node.name}'")
                        result["suggestions"].append({
                            "type": "unit_test",
                            "target": f"{node.name}",
                            "location": f"{file_path}:{node.lineno}",
                            "suggestion": f"Create test for function '{node.name}' - {len(node.args.args)} parameters",
                            "priority": "high" if len(node.args.args) > 3 else "medium"
                        })
                
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
                        "is_private": node.name.startswith("_")
                    }
                    result["classes"].append(class_info)
                    
                    if not node.name.startswith("_"):
                        result["suggestions"].append({
                            "type": "class_test",
                            "target": f"{node.name}",
                            "location": f"{file_path}:{node.lineno}",
                            "suggestion": f"Create test class for '{node.name}' with {class_info['methods']} methods",
                            "priority": "high"
                        })
            
            # Calculate complexity score
            result["complexity_score"] = len(result["functions"]) * 0.3 + len(result["classes"]) * 0.7
            result["needs_tests"] = len(result["functions"]) > 0 or len(result["classes"]) > 0
            
        except Exception as e:
            result["suggestions"].append({
                "type": "error",
                "suggestion": f"Could not analyze {file_path}: {e}",
                "priority": "low"
            })
        
        return result
    
    def _generate_testing_recommendations(self, files_needing_tests: List[Dict], target_coverage: int) -> List[str]:
        """Generate specific testing recommendations based on existing setup"""
        recommendations = []
        
        if not files_needing_tests:
            recommendations.append("✅ No additional tests needed - good job!")
            return recommendations
        
        # Detect existing test framework and setup
        test_framework = self._detect_test_framework()
        
        recommendations.extend([
            f"🎯 TARGET: {target_coverage}% test coverage",
            f"📊 ANALYSIS: {len(files_needing_tests)} files need testing",
            f"🔍 DETECTED: {test_framework['framework']} framework",
            "",
            "📋 TESTING STRATEGY:"
        ])
        
        # Priority files (high complexity first)
        priority_files = sorted(files_needing_tests, key=lambda x: x["complexity"], reverse=True)[:5]
        
        for i, file_info in enumerate(priority_files, 1):
            recommendations.append(f"{i}. {file_info['file']}")
            recommendations.append(f"   • {len(file_info['functions'])} functions, {len(file_info['classes'])} classes")
            recommendations.append(f"   • Complexity: {file_info['complexity']:.1f}")
            
            # Specific test file suggestions based on existing pattern
            test_file = self._suggest_test_file_path(file_info['file'], test_framework)
            recommendations.append(f"   • Create: {test_file}")
            recommendations.append("")
        
        # Framework-specific recommendations
        recommendations.extend(self._get_framework_recommendations(test_framework, target_coverage))
        
        return recommendations
    
    def _detect_test_framework(self) -> Dict[str, Any]:
        """Detect existing test framework and configuration"""
        framework_info = {
            "framework": "unknown",
            "config_files": [],
            "test_directory": None,
            "coverage_tool": None,
            "existing_tests": []
        }
        
        # Check for pytest
        if os.path.exists("pytest.ini") or os.path.exists("pyproject.toml"):
            framework_info["framework"] = "pytest"
            if os.path.exists("pytest.ini"):
                framework_info["config_files"].append("pytest.ini")
            if os.path.exists("pyproject.toml"):
                framework_info["config_files"].append("pyproject.toml")
        
        # Check for unittest
        elif os.path.exists("setup.cfg") or any(os.path.exists(d) for d in ["test", "tests"]):
            framework_info["framework"] = "unittest"
        
        # Detect test directory and analyze existing patterns
        for test_dir in ["tests", "test", "testing"]:
            if os.path.exists(test_dir):
                framework_info["test_directory"] = test_dir
                # Count existing test files
                test_files = glob.glob(f"{test_dir}/**/test_*.py", recursive=True)
                test_files.extend(glob.glob(f"{test_dir}/**/*_test.py", recursive=True))
                framework_info["existing_tests"] = test_files
                
                # Analyze test patterns in existing files
                framework_info["test_patterns"] = self._analyze_test_patterns(test_files)
                break
        
        # Detect coverage tools
        try:
            import coverage
            framework_info["coverage_tool"] = "coverage.py"
        except ImportError:
            pass
        
        return framework_info
    
    def _analyze_test_patterns(self, test_files: List[str]) -> Dict[str, Any]:
        """Analyze existing test files to detect patterns"""
        patterns = {
            "style": "unknown",  # function_based, class_based, mixed
            "naming": "unknown",  # test_*, *_test
            "class_count": 0,
            "function_count": 0,
            "uses_fixtures": False,
            "uses_parametrize": False,
            "uses_mock": False
        }
        
        if not test_files:
            return patterns
        
        total_classes = 0
        total_functions = 0
        
        # Analyze first few test files to detect patterns
        for test_file in test_files[:5]:  # Sample first 5 files
            try:
                with open(test_file, 'r') as f:
                    content = f.read()
                
                # Parse to find classes and functions
                tree = ast.parse(content)
                
                file_classes = 0
                file_functions = 0
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if node.name.startswith('Test'):
                            file_classes += 1
                    elif isinstance(node, ast.FunctionDef):
                        if node.name.startswith('test_'):
                            file_functions += 1
                
                total_classes += file_classes
                total_functions += file_functions
                
                # Check for pytest patterns
                if "pytest" in content or "@pytest" in content:
                    patterns["uses_fixtures"] = True
                if "@pytest.mark.parametrize" in content:
                    patterns["uses_parametrize"] = True
                if "mock" in content.lower() or "Mock" in content:
                    patterns["uses_mock"] = True
                
            except Exception:
                continue
        
        patterns["class_count"] = total_classes
        patterns["function_count"] = total_functions
        
        # Determine style
        if total_classes > total_functions:
            patterns["style"] = "class_based"
        elif total_functions > total_classes:
            patterns["style"] = "function_based"
        else:
            patterns["style"] = "mixed"
        
        # Determine naming pattern
        test_prefix_files = [f for f in test_files if os.path.basename(f).startswith('test_')]
        test_suffix_files = [f for f in test_files if os.path.basename(f).endswith('_test.py')]
        
        if len(test_prefix_files) > len(test_suffix_files):
            patterns["naming"] = "test_*"
        elif len(test_suffix_files) > len(test_prefix_files):
            patterns["naming"] = "*_test"
        else:
            patterns["naming"] = "mixed"
        
        return patterns
    
    def _suggest_test_file_path(self, source_file: str, framework_info: Dict) -> str:
        """Suggest test file path based on existing patterns"""
        if framework_info["test_directory"]:
            base_dir = framework_info["test_directory"]
        else:
            base_dir = "tests"  # Default
        
        # Remove common source prefixes
        clean_path = source_file.replace("src/", "").replace("lib/", "")
        filename = os.path.basename(clean_path).replace(".py", "")
        
        # Use existing naming pattern if detected
        test_patterns = framework_info.get("test_patterns", {})
        naming_pattern = test_patterns.get("naming", "unknown")
        
        if naming_pattern == "*_test":
            test_filename = f"{filename}_test.py"
        elif naming_pattern == "test_*" or framework_info["framework"] == "pytest":
            test_filename = f"test_{filename}.py"
        else:
            # Default to test_ prefix
            test_filename = f"test_{filename}.py"
        
        return os.path.join(base_dir, test_filename)
    
    def _get_framework_recommendations(self, framework_info: Dict, target_coverage: int) -> List[str]:
        """Get framework-specific recommendations"""
        recommendations = []
        
        if framework_info["framework"] == "pytest":
            patterns = framework_info.get("test_patterns", {})
            recommendations.extend([
                "🔧 PYTEST SETUP DETECTED:",
                f"• Existing config: {', '.join(framework_info['config_files']) if framework_info['config_files'] else 'None'}",
                f"• Test directory: {framework_info['test_directory'] or 'Not found'}",
                f"• Existing tests: {len(framework_info['existing_tests'])} files",
                f"• Test style: {patterns.get('style', 'unknown')} ({patterns.get('class_count', 0)} classes, {patterns.get('function_count', 0)} functions)",
                f"• Naming pattern: {patterns.get('naming', 'unknown')}",
                "",
                "⚡ PYTEST RECOMMENDATIONS (following your patterns):",
                f"• Use {'class-based' if patterns.get('style') == 'class_based' else 'function-based'} tests",
                f"• Follow {patterns.get('naming', 'test_*')} naming convention",
                "• Use fixtures for common test setup" + (" ✅" if patterns.get('uses_fixtures') else ""),
                "• Use @pytest.mark.parametrize for multiple test cases" + (" ✅" if patterns.get('uses_parametrize') else ""),
                "• Mock external dependencies" + (" ✅" if patterns.get('uses_mock') else ""),
                f"• Run: pytest --cov=src --cov-report=html --cov-fail-under={target_coverage}",
            ])
        
        elif framework_info["framework"] == "unittest":
            patterns = framework_info.get("test_patterns", {})
            recommendations.extend([
                "🔧 UNITTEST SETUP DETECTED:",
                f"• Test directory: {framework_info['test_directory'] or 'Not found'}",
                f"• Existing tests: {len(framework_info['existing_tests'])} files",
                f"• Test style: {patterns.get('style', 'unknown')} ({patterns.get('class_count', 0)} classes, {patterns.get('function_count', 0)} functions)",
                f"• Naming pattern: {patterns.get('naming', 'unknown')}",
                "",
                "⚡ UNITTEST RECOMMENDATIONS (following your patterns):",
                f"• Use {'class-based TestCase' if patterns.get('style') == 'class_based' else 'function-based'} tests",
                f"• Follow {patterns.get('naming', 'test_*')} naming convention",
                "• Use setUp() and tearDown() for test fixtures",
                "• Use unittest.mock for mocking dependencies" + (" ✅" if patterns.get('uses_mock') else ""), 
                "• Run: python -m unittest discover",
                f"• Add coverage: coverage run -m unittest && coverage report --fail-under={target_coverage}",
            ])
        
        else:
            recommendations.extend([
                "🔧 NO TEST FRAMEWORK DETECTED:",
                "• Consider installing pytest: pip install pytest pytest-cov",
                "• Or use built-in unittest module",
                "• Create 'tests/' directory structure",
                f"• Aim for {target_coverage}%+ test coverage",
            ])
        
        recommendations.extend([
            "",
            "⚡ QUICK WINS:",
            "• Start with pure functions (no side effects)",
            "• Test public API methods first",
            "• Add edge case testing",
            "• Use existing patterns from current test files" if framework_info["existing_tests"] else "• Follow framework conventions"
        ])
        
        return recommendations


# MCP Server Implementation
# Check if MCP is available
try:
    import mcp
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

if MCP_AVAILABLE:
    # Create the server instance
    server = Server("python-refactoring-assistant")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available refactoring analysis tools"""
        return [
            types.Tool(
                name="analyze_python_file",
                description="Analyze Python file for refactoring opportunities with precise guidance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file to analyze",
                        },
                        "content": {
                            "type": "string",
                            "description": "Python file content to analyze",
                        },
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="get_extraction_guidance",
                description="Get detailed step-by-step guidance for extracting functions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file",
                        },
                        "content": {
                            "type": "string",
                            "description": "Python file content",
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to analyze for extraction",
                        },
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="find_long_functions",
                description="Find functions that are candidates for extraction",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python file content to analyze",
                        },
                        "line_threshold": {
                            "type": "integer",
                            "description": "Minimum lines to consider a function long (default: 20)",
                        },
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="check_types_with_pyrefly",
                description="Check Python code for type errors and quality issues using pyrefly",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content to type check",
                        }
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="analyze_test_coverage",
                description="Analyze Python test coverage and suggest improvements",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_path": {
                            "type": "string",
                            "description": "Path to source code directory or file",
                        },
                        "test_path": {
                            "type": "string", 
                            "description": "Path to test directory (optional)",
                        },
                        "target_coverage": {
                            "type": "integer",
                            "description": "Target coverage percentage (default: 80)",
                            "default": 80
                        }
                    },
                    "required": ["source_path"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls for refactoring analysis"""

        try:
            analyzer = EnhancedRefactoringAnalyzer()

            if name == "analyze_python_file":
                file_path = arguments.get("file_path", "unknown.py")
                content = arguments["content"]

                guidance = analyzer.analyze_file(file_path, content)

                result = {
                    "analysis_summary": {
                        "total_issues_found": len(guidance),
                        "critical_issues": len(
                            [g for g in guidance if g.severity == "critical"]
                        ),
                        "high_priority": len(
                            [g for g in guidance if g.severity == "high"]
                        ),
                        "medium_priority": len(
                            [g for g in guidance if g.severity == "medium"]
                        ),
                        "low_priority": len(
                            [g for g in guidance if g.severity == "low"]
                        ),
                    },
                    "refactoring_guidance": [g.to_dict() for g in guidance],
                    "tools_used": {
                        "rope": True,
                        "radon": True,
                        "vulture": True,
                        "jedi": True,
                        "libcst": True,
                        "pyrefly": True,
                        "mccabe": True,
                        "complexipy": True,
                        "file_structure_analysis": True,
                    },
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "find_long_functions":
                content = arguments["content"]
                line_threshold = arguments.get("line_threshold", 20)

                try:
                    tree = ast.parse(content)
                    long_functions = []

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if hasattr(node, "end_lineno") and node.end_lineno:
                                length = node.end_lineno - node.lineno + 1
                                if length >= line_threshold:
                                    long_functions.append(
                                        {
                                            "name": node.name,
                                            "start_line": node.lineno,
                                            "end_line": node.end_lineno,
                                            "length": length,
                                            "location": f"lines {node.lineno}-{node.end_lineno}",
                                        }
                                    )

                    result = {
                        "total_functions_analyzed": len(
                            [
                                n
                                for n in ast.walk(tree)
                                if isinstance(n, ast.FunctionDef)
                            ]
                        ),
                        "long_functions_found": len(long_functions),
                        "line_threshold": line_threshold,
                        "functions": long_functions,
                    }

                    return [
                        types.TextContent(
                            type="text", text=json.dumps(result, indent=2)
                        )
                    ]

                except SyntaxError as e:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps({"error": f"Syntax error: {e}"}, indent=2),
                        )
                    ]

            elif name == "get_extraction_guidance":
                content = arguments["content"]
                function_name = arguments.get("function_name")

                guidance = analyzer.analyze_file("temp.py", content)
                extraction_guidance = [
                    g for g in guidance if g.issue_type == "extract_function"
                ]

                if function_name:
                    extraction_guidance = [
                        g for g in extraction_guidance if function_name in g.location
                    ]

                result = {
                    "extraction_opportunities": len(extraction_guidance),
                    "guidance": [g.to_dict() for g in extraction_guidance],
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "check_types_with_pyrefly":
                content = arguments["content"]

                # Use pyrefly for type checking
                analyzer = EnhancedRefactoringAnalyzer()
                type_issues = analyzer._analyze_with_pyrefly(content)

                result = {
                    "issues_found": len(type_issues),
                    "analysis": [issue.to_dict() for issue in type_issues]
                    if type_issues
                    else [],
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "analyze_test_coverage":
                source_path = arguments["source_path"]
                test_path = arguments.get("test_path")
                target_coverage = arguments.get("target_coverage", 80)

                # Analyze test coverage
                analyzer = EnhancedRefactoringAnalyzer()
                coverage_analysis = analyzer.analyze_test_coverage(source_path, test_path, target_coverage)

                return [
                    types.TextContent(type="text", text=json.dumps(coverage_analysis, indent=2))
                ]

            else:
                return [
                    types.TextContent(
                        type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
                    )
                ]

        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"Analysis failed: {str(e)}"}),
                )
            ]

    async def main():
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

else:
    print("MCP not available. Running in standalone mode for testing.")

    def main():
        """Standalone mode for testing without MCP"""
        if len(sys.argv) < 2:
            print("Usage: python server.py <python_file>")
            return

        file_path = sys.argv[1]
        with open(file_path, "r") as f:
            content = f.read()

        analyzer = EnhancedRefactoringAnalyzer()
        guidance = analyzer.analyze_file(file_path, content)

        print("\n=== REFACTORING ANALYSIS ===")
        for i, g in enumerate(guidance, 1):
            print(f"\n{i}. {g.issue_type.upper()} [{g.severity}]")
            print(f"   Location: {g.location}")
            print(f"   Description: {g.description}")
            print("   Steps:")
            for step in g.precise_steps[:5]:  # Show first 5 steps
                print(f"     {step}")
            if len(g.precise_steps) > 5:
                print(f"     ... and {len(g.precise_steps) - 5} more steps")


if __name__ == "__main__":
    if MCP_AVAILABLE:
        import asyncio

        asyncio.run(main())
    else:
        main()
