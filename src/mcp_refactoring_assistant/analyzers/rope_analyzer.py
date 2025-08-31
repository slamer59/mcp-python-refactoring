#!/usr/bin/env python3
"""
Rope-based refactoring analyzer for function extraction
"""

import ast
import os
import tempfile
from typing import Any, List, Optional

from rope.base.project import Project

from ..models import ExtractableBlock, RefactoringGuidance
from .base import BaseAnalyzer


class RopeAnalyzer(BaseAnalyzer):
    """Analyzer using Rope for professional refactoring analysis"""

    def __init__(self):
        super().__init__()
        self.project_path = tempfile.mkdtemp()
        self.rope_project = None

        # Initialize Rope project
        try:
            self.rope_project = Project(self.project_path)
        except Exception as e:
            print(f"Warning: Could not initialize Rope project: {e}")
            self.rope_project = None

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use Rope for professional refactoring analysis"""
        guidance_list = []

        if not self.rope_project:
            return guidance_list

        try:
            if tree is None:
                tree = ast.parse(content)

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