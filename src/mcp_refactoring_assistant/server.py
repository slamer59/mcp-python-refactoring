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

# Third-party imports with graceful fallbacks
try:
    from rope.base.project import Project
    from rope.refactor.extract import ExtractMethod, ExtractVariable
    from rope.refactor.rename import Rename
    ROPE_AVAILABLE = True
    # Handle rope resource types
    try:
        from rope.base.resources import File as RopeFile
    except ImportError:
        RopeFile = None
except ImportError:
    ROPE_AVAILABLE = False
    RopeFile = None

try:
    from radon.complexity import cc_rank, cc_visit
    from radon.metrics import h_visit, mi_rank, mi_visit
    from radon.raw import analyze
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False

try:
    import vulture
    VULTURE_AVAILABLE = True
except ImportError:
    VULTURE_AVAILABLE = False

try:
    import jedi
    JEDI_AVAILABLE = True
except ImportError:
    JEDI_AVAILABLE = False

try:
    import libcst as cst
    from libcst.matchers import matches
    LIBCST_AVAILABLE = True
except ImportError:
    LIBCST_AVAILABLE = False

try:
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP not available - running in standalone mode")


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
            result['extractable_blocks'] = [block.to_dict() for block in self.extractable_blocks]
        return result


class EnhancedRefactoringAnalyzer:
    """Professional refactoring analyzer using multiple third-party libraries"""
    
    def __init__(self, project_path: str = None):
        self.project_path = project_path or tempfile.mkdtemp()
        self.rope_project = None
        
        # Initialize Rope project if available
        if ROPE_AVAILABLE:
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
            if RADON_AVAILABLE:
                guidance_list.extend(self._analyze_with_radon(content, file_path))
            
            # 2. Analyze with Rope for extraction opportunities
            if ROPE_AVAILABLE and self.rope_project:
                guidance_list.extend(self._analyze_with_rope(file_path, content, tree))
            
            # 3. Analyze with Vulture for dead code
            if VULTURE_AVAILABLE:
                guidance_list.extend(self._analyze_with_vulture(content, file_path))
            
            # 4. Manual AST analysis for patterns not caught by other tools
            guidance_list.extend(self._analyze_ast_patterns(tree, content, file_path))
            
        except SyntaxError as e:
            guidance_list.append(RefactoringGuidance(
                issue_type="syntax_error",
                severity="critical",
                location=f"Line {e.lineno}",
                description=f"Syntax error prevents analysis: {e}",
                benefits=["Enable proper code analysis"],
                precise_steps=["Fix syntax error before proceeding with refactoring"]
            ))
        
        return guidance_list

    def _analyze_with_radon(self, content: str, file_path: str) -> List[RefactoringGuidance]:
        """Use Radon for complexity analysis"""
        guidance_list = []
        
        try:
            # Cyclomatic complexity analysis
            complexity_blocks = cc_visit(content)
            
            for block in complexity_blocks:
                if block.complexity > 10:  # High complexity threshold
                    guidance_list.append(RefactoringGuidance(
                        issue_type="high_complexity",
                        severity="high" if block.complexity > 15 else "medium",
                        location=f"Function '{block.name}' at line {block.lineno}",
                        description=f"Function has high cyclomatic complexity: {block.complexity}",
                        benefits=[
                            "Improved readability and maintainability",
                            "Easier testing and debugging",
                            "Reduced cognitive load"
                        ],
                        precise_steps=[
                            "1. Identify decision points (if, for, while, except)",
                            "2. Look for logical groupings of conditions",
                            "3. Extract complex conditions into separate functions",
                            "4. Consider using strategy pattern for complex branching",
                            "5. Add unit tests for each extracted function"
                        ],
                        metrics={"complexity": block.complexity, "type": block.type}
                    ))
                        
            # Maintainability Index
            mi_score = mi_visit(content, multi=True)
            for item in mi_score:
                if item.mi < 20:  # Low maintainability
                    guidance_list.append(RefactoringGuidance(
                        issue_type="low_maintainability",
                        severity="medium",
                        location=f"Function '{item.name}' at line {item.lineno}",
                        description=f"Low maintainability index: {item.mi:.1f}",
                        benefits=[
                            "Improved code maintainability",
                            "Easier future modifications",
                            "Better code quality"
                        ],
                        precise_steps=[
                            "1. Reduce function length (aim for < 20 lines)",
                            "2. Simplify complex expressions",
                            "3. Add meaningful variable names",
                            "4. Extract nested logic into helper functions",
                            "5. Add comprehensive documentation"
                        ],
                        metrics={"maintainability_index": item.mi}
                    ))
            
        except Exception as e:
            print(f"Warning: Radon analysis failed: {e}")
        
        return guidance_list

    def _analyze_with_rope(self, file_path: str, content: str, tree: ast.AST) -> List[RefactoringGuidance]:
        """Use Rope for professional refactoring analysis"""
        guidance_list = []
        
        if not self.rope_project:
            return guidance_list
            
        try:
            # Create temporary file for Rope analysis
            temp_file_path = os.path.join(self.project_path, 'temp_analysis.py')
            with open(temp_file_path, 'w') as f:
                f.write(content)
            
            rope_file = self.rope_project.get_resource('temp_analysis.py')
            
            # Find long functions that could benefit from extraction
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        function_length = node.end_lineno - node.lineno + 1
                        
                        if function_length > 20:  # Long function threshold
                            extractable_blocks = self._find_extractable_blocks_with_rope(
                                rope_file, node, content.split('\n')
                            )
                            
                            if extractable_blocks:
                                guidance_list.append(RefactoringGuidance(
                                    issue_type="extract_function",
                                    severity="medium",
                                    location=f"Function '{node.name}' lines {node.lineno}-{node.end_lineno}",
                                    description=f"Long function ({function_length} lines) with extractable blocks",
                                    benefits=[
                                        "Improved readability",
                                        "Better testability",
                                        "Code reusability",
                                        "Easier maintenance"
                                    ],
                                    precise_steps=self._generate_extraction_steps(extractable_blocks),
                                    extractable_blocks=extractable_blocks
                                ))
            
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
        except Exception as e:
            print(f"Warning: Rope analysis failed: {e}")
        
        return guidance_list

    def _find_extractable_blocks_with_rope(self, rope_file: Any, function_node: ast.FunctionDef, 
                                         lines: List[str]) -> List[ExtractableBlock]:
        """Find extractable blocks using Rope's analysis capabilities"""
        blocks = []
        
        try:
            # Analyze the function body for logical blocks
            function_start = function_node.lineno - 1
            function_end = getattr(function_node, 'end_lineno', function_node.lineno) - 1
            
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

    def _create_extractable_block(self, statements: List[ast.stmt], lines: List[str], 
                                block_type: str) -> Optional[ExtractableBlock]:
        """Create an ExtractableBlock from AST statements"""
        if not statements:
            return None
        
        start_line = statements[0].lineno
        end_line = getattr(statements[-1], 'end_lineno', statements[-1].lineno)
        
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
        content = '\n'.join(lines[start_line-1:end_line])
        suggested_name = self._suggest_function_name(statements, block_type)
        description = self._describe_block_purpose(statements, block_type)
        
        return ExtractableBlock(
            start_line=start_line,
            end_line=end_line,
            content=content,
            variables_used=parameters,
            variables_modified=list(variables_modified),
            suggested_name=suggested_name,
            description=description,
            complexity_score=len(statements) * 0.5,  # Simple complexity metric
            extraction_type="function"
        )

    def _suggest_function_name(self, statements: List[ast.stmt], block_type: str) -> str:
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
        if any('validate' in call.lower() for call in method_calls):
            return 'validate_data'
        elif any('process' in call.lower() for call in method_calls):
            return 'process_data'  
        elif any('calculate' in call.lower() for call in method_calls):
            return 'calculate_result'
        elif any('format' in call.lower() for call in method_calls):
            return 'format_output'
        elif block_type == "conditional_logic":
            return 'handle_condition'
        elif block_type == "loop_logic":
            return 'process_items'
        else:
            return 'extracted_function'

    def _describe_block_purpose(self, statements: List[ast.stmt], block_type: str) -> str:
        """Describe what the block does"""
        stmt_count = len(statements)
        if block_type == "conditional_logic":
            return f"Handle conditional logic ({stmt_count} statements)"
        elif block_type == "loop_logic":
            return f"Process loop iterations ({stmt_count} statements)"
        else:
            return f"Execute {stmt_count} sequential operations"

    def _remove_overlapping_blocks(self, blocks: List[ExtractableBlock]) -> List[ExtractableBlock]:
        """Remove overlapping blocks, keeping the most specific ones"""
        if not blocks:
            return blocks
        
        blocks.sort(key=lambda b: b.start_line)
        non_overlapping = []
        
        for block in blocks:
            overlaps = False
            for existing in non_overlapping:
                if (block.start_line <= existing.end_line and 
                    block.end_line >= existing.start_line):
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
                "6. Test to ensure behavior unchanged"
            ]
        
        steps = ["📋 PRECISION EXTRACTION PLAN:"]
        
        for i, block in enumerate(blocks, 1):
            steps.extend([
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
                f"   • At the cut location, type: {self._format_function_call(block)}"
            ])
        
        steps.extend([
            "\n✅ VERIFICATION:",
            "• Run your tests",
            "• Check for undefined variable errors",
            "• Verify function behavior is identical",
            "• Confirm all edge cases still work"
        ])
        
        return steps

    def _format_parameters(self, variables: List[str]) -> str:
        """Format function parameters"""
        return ', '.join(variables) if variables else ''

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
        params = ', '.join(block.variables_used) if block.variables_used else ''
        
        if not block.variables_modified:
            return f"{block.suggested_name}({params})"
        elif len(block.variables_modified) == 1:
            return f"{block.variables_modified[0]} = {block.suggested_name}({params})"
        else:
            vars_str = ', '.join(block.variables_modified)
            return f"{vars_str} = {block.suggested_name}({params})"

    def _analyze_with_vulture(self, content: str, file_path: str) -> List[RefactoringGuidance]:
        """Use Vulture to find dead code"""
        guidance_list = []
        
        try:
            v = vulture.Vulture()
            v.scan(content, filename=file_path)
            
            for unused_item in v.get_unused_code():
                guidance_list.append(RefactoringGuidance(
                    issue_type="dead_code",
                    severity="low",
                    location=f"Line {unused_item.first_lineno}",
                    description=f"Unused {unused_item.typ}: {unused_item.name}",
                    benefits=[
                        "Cleaner codebase",
                        "Reduced complexity",
                        "Better maintainability"
                    ],
                    precise_steps=[
                        f"1. Verify '{unused_item.name}' is truly unused",
                        "2. Check if it's part of a public API",
                        "3. Remove the unused code if confirmed",
                        "4. Run tests to ensure nothing breaks"
                    ],
                    metrics={"confidence": unused_item.confidence}
                ))
        
        except Exception as e:
            print(f"Warning: Vulture analysis failed: {e}")
        
        return guidance_list

    def _analyze_ast_patterns(self, tree: ast.AST, content: str, file_path: str) -> List[RefactoringGuidance]:
        """Manual AST analysis for patterns not caught by other tools"""
        guidance_list = []
        lines = content.split('\n')
        
        # Find functions with too many parameters
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                param_count = len(node.args.args)
                if param_count > 5:
                    guidance_list.append(RefactoringGuidance(
                        issue_type="too_many_parameters",
                        severity="medium",
                        location=f"Function '{node.name}' at line {node.lineno}",
                        description=f"Function has {param_count} parameters (consider max 5)",
                        benefits=[
                            "Improved function signature readability",
                            "Easier function calls",
                            "Better parameter management"
                        ],
                        precise_steps=[
                            "1. Group related parameters into a dataclass or dict",
                            "2. Consider using **kwargs for optional parameters",
                            "3. Split function if it does too many things",
                            "4. Use parameter objects for complex data"
                        ]
                    ))
        
        return guidance_list

# MCP Server Implementation
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
                            "description": "Path to Python file to analyze"
                        },
                        "content": {
                            "type": "string", 
                            "description": "Python file content to analyze"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="get_extraction_guidance",
                description="Get detailed step-by-step guidance for extracting functions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file"
                        },
                        "content": {
                            "type": "string",
                            "description": "Python file content"
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to analyze for extraction"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="find_long_functions",
                description="Find functions that are candidates for extraction",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python file content to analyze"
                        },
                        "line_threshold": {
                            "type": "integer",
                            "description": "Minimum lines to consider a function long (default: 20)"
                        }
                    },
                    "required": ["content"]
                }
            )
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
                        "critical_issues": len([g for g in guidance if g.severity == "critical"]),
                        "high_priority": len([g for g in guidance if g.severity == "high"]),
                        "medium_priority": len([g for g in guidance if g.severity == "medium"]),
                        "low_priority": len([g for g in guidance if g.severity == "low"])
                    },
                    "refactoring_guidance": [g.to_dict() for g in guidance],
                    "tools_used": {
                        "rope": ROPE_AVAILABLE,
                        "radon": RADON_AVAILABLE,
                        "vulture": VULTURE_AVAILABLE,
                        "jedi": JEDI_AVAILABLE,
                        "libcst": LIBCST_AVAILABLE
                    }
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            
            elif name == "find_long_functions":
                content = arguments["content"]
                line_threshold = arguments.get("line_threshold", 20)
                
                try:
                    tree = ast.parse(content)
                    long_functions = []
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if hasattr(node, 'end_lineno') and node.end_lineno:
                                length = node.end_lineno - node.lineno + 1
                                if length >= line_threshold:
                                    long_functions.append({
                                        "name": node.name,
                                        "start_line": node.lineno,
                                        "end_line": node.end_lineno,
                                        "length": length,
                                        "location": f"lines {node.lineno}-{node.end_lineno}"
                                    })
                    
                    result = {
                        "total_functions_analyzed": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
                        "long_functions_found": len(long_functions),
                        "line_threshold": line_threshold,
                        "functions": long_functions
                    }
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                    
                except SyntaxError as e:
                    return [types.TextContent(
                        type="text", 
                        text=json.dumps({"error": f"Syntax error: {e}"}, indent=2)
                    )]
            
            elif name == "get_extraction_guidance":
                content = arguments["content"]
                function_name = arguments.get("function_name")
                
                guidance = analyzer.analyze_file("temp.py", content)
                extraction_guidance = [g for g in guidance if g.issue_type == "extract_function"]
                
                if function_name:
                    extraction_guidance = [g for g in extraction_guidance if function_name in g.location]
                
                result = {
                    "extraction_opportunities": len(extraction_guidance),
                    "guidance": [g.to_dict() for g in extraction_guidance]
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            
            else:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"})
                )]
                
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Analysis failed: {str(e)}"})
            )]

    async def main():
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

else:
    print("MCP not available. Running in standalone mode for testing.")
    
    def main():
        """Standalone mode for testing without MCP"""
        if len(sys.argv) < 2:
            print("Usage: python server.py <python_file>")
            return
        
        file_path = sys.argv[1]
        with open(file_path, 'r') as f:
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