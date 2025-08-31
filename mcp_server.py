#!/usr/bin/env python3
"""
Python Refactoring MCP Server
Single server with both guide_only and apply_changes modes
"""

import asyncio
import json
import sys
import ast
import re
from typing import Any, Dict, List, Optional

# Import MCP with SSE support
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.server.sse import SseServerTransport
    from mcp import types
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    print(f"MCP not available: {e}")

# Import analyzer
try:
    from src.mcp_refactoring_assistant.server import EnhancedRefactoringAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        from mcp_refactoring_assistant.server import EnhancedRefactoringAnalyzer
        ANALYZER_AVAILABLE = True
    except ImportError:
        ANALYZER_AVAILABLE = False

class CodeRefactorer:
    """Performs actual code modifications for apply_changes mode"""
    
    def extract_function(self, content: str, start_line: int, end_line: int, 
                        function_name: str, parameters: List[str], 
                        return_vars: List[str], insertion_line: int) -> str:
        """Extract a function from the given code"""
        lines = content.split('\n')
        
        # Extract the code block
        extracted_lines = lines[start_line-1:end_line]
        
        # Create function signature
        params_str = ', '.join(parameters) if parameters else ''
        function_def = f"def {function_name}({params_str}):\n"
        
        # Indent extracted code
        indented_code = '\n'.join(f"    {line}" for line in extracted_lines)
        
        # Add return statement
        if return_vars:
            if len(return_vars) == 1:
                return_stmt = f"    return {return_vars[0]}"
            else:
                return_stmt = f"    return {', '.join(return_vars)}"
        else:
            return_stmt = ""
        
        # Complete function
        new_function = function_def + indented_code
        if return_stmt:
            new_function += "\n" + return_stmt
        
        # Create function call
        if return_vars:
            if len(return_vars) == 1:
                function_call = f"{return_vars[0]} = {function_name}({params_str})"
            else:
                vars_str = ', '.join(return_vars)
                function_call = f"{vars_str} = {function_name}({params_str})"
        else:
            function_call = f"{function_name}({params_str})"
        
        # Rebuild the code
        new_lines = (
            lines[:insertion_line-1] +
            [new_function, ""] +
            lines[insertion_line-1:start_line-1] +
            [function_call] +
            lines[end_line:]
        )
        
        return '\n'.join(new_lines)
    
    def apply_extraction(self, content: str, extraction_block: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a single extraction to the code"""
        try:
            new_code = self.extract_function(
                content=content,
                start_line=extraction_block['start_line'],
                end_line=extraction_block['end_line'],
                function_name=extraction_block['suggested_name'],
                parameters=extraction_block['variables_used'],
                return_vars=extraction_block['variables_modified'],
                insertion_line=extraction_block.get('insertion_line', 1)
            )
            
            return {
                "success": True,
                "new_code": new_code,
                "extracted_function": extraction_block['suggested_name'],
                "location": f"lines {extraction_block['start_line']}-{extraction_block['end_line']}",
                "summary": f"Extracted {extraction_block['suggested_name']}() from {extraction_block['description']}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "extraction_block": extraction_block
            }

# MCP Tools setup
if MCP_AVAILABLE:
    server = Server("python-refactoring")

    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """List all refactoring tools"""
        return [
            types.Tool(
                name="analyze_python_code",
                description="Analyze Python code with optional automatic refactoring",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content to analyze"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["guide_only", "apply_changes"],
                            "default": "guide_only",
                            "description": "Mode: guide_only (instructions) or apply_changes (automatic)"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional file path for context"
                        },
                        "line_threshold": {
                            "type": "integer",
                            "default": 20,
                            "description": "Minimum lines to consider a function long"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="extract_function",
                description="Extract function with guide or apply mode",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content"
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Function to extract from"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["guide_only", "apply_changes"],
                            "default": "guide_only"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Start line for extraction (apply_changes mode)"
                        },
                        "end_line": {
                            "type": "integer", 
                            "description": "End line for extraction (apply_changes mode)"
                        },
                        "new_function_name": {
                            "type": "string",
                            "description": "Name for extracted function (apply_changes mode)"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="quick_analyze",
                description="Quick analysis to find immediate refactoring opportunities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content"
                        }
                    },
                    "required": ["content"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle all tool calls"""
        
        if not ANALYZER_AVAILABLE:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Python refactoring analyzer not available",
                    "suggestion": "Run: uv sync"
                })
            )]
        
        try:
            analyzer = EnhancedRefactoringAnalyzer()
            refactorer = CodeRefactorer()
            
            if name == "analyze_python_code":
                content = arguments["content"]
                mode = arguments.get("mode", "guide_only")
                file_path = arguments.get("file_path", "temp.py")
                line_threshold = arguments.get("line_threshold", 20)
                
                # Analyze code
                guidance = analyzer.analyze_file(file_path, content)
                
                if mode == "guide_only":
                    # Guide mode
                    result = {
                        "mode": "guide_only",
                        "analysis_summary": {
                            "total_issues_found": len(guidance),
                            "high_priority": len([g for g in guidance if g.severity == "high"]),
                            "medium_priority": len([g for g in guidance if g.severity == "medium"]),
                            "low_priority": len([g for g in guidance if g.severity == "low"])
                        },
                        "refactoring_guidance": [
                            {
                                "issue_type": g.issue_type,
                                "severity": g.severity,
                                "location": g.location,
                                "description": g.description,
                                "precise_steps": g.precise_steps,
                                "benefits": g.benefits,
                                "extractable_blocks": [
                                    {
                                        "suggested_name": block.suggested_name,
                                        "start_line": block.start_line,
                                        "end_line": block.end_line,
                                        "variables_used": block.variables_used,
                                        "variables_modified": block.variables_modified
                                    } for block in (g.extractable_blocks or [])
                                ] if hasattr(g, 'extractable_blocks') and g.extractable_blocks else []
                            } for g in guidance
                        ]
                    }
                
                elif mode == "apply_changes":
                    # Apply mode
                    applied_changes = []
                    current_code = content
                    
                    # Apply extractions automatically
                    extract_opportunities = [g for g in guidance if g.issue_type == "extract_function"]
                    
                    for opportunity in extract_opportunities:
                        if hasattr(opportunity, 'extractable_blocks') and opportunity.extractable_blocks:
                            for block in opportunity.extractable_blocks:
                                change_result = refactorer.apply_extraction(current_code, {
                                    'start_line': block.start_line,
                                    'end_line': block.end_line,
                                    'suggested_name': block.suggested_name,
                                    'variables_used': block.variables_used,
                                    'variables_modified': block.variables_modified,
                                    'description': block.description,
                                    'insertion_line': 1
                                })
                                
                                if change_result['success']:
                                    applied_changes.append(change_result)
                                    current_code = change_result['new_code']
                    
                    result = {
                        "mode": "apply_changes",
                        "changes_applied": len(applied_changes),
                        "new_code": current_code,
                        "original_issues": len(guidance),
                        "applied_extractions": [
                            {
                                "function_name": change['extracted_function'],
                                "location": change['location'],
                                "summary": change['summary']
                            } for change in applied_changes if change['success']
                        ],
                        "errors": [
                            change['error'] for change in applied_changes if not change['success']
                        ]
                    }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            
            elif name == "extract_function":
                content = arguments["content"]
                mode = arguments.get("mode", "guide_only")
                function_name = arguments.get("function_name")
                
                # Find extraction opportunities
                guidance = analyzer.analyze_file("temp.py", content)
                extract_opportunities = [g for g in guidance if g.issue_type == "extract_function"]
                
                if function_name:
                    extract_opportunities = [g for g in extract_opportunities if function_name in g.location]
                
                if mode == "guide_only":
                    result = {
                        "mode": "guide_only",
                        "function_filter": function_name,
                        "extraction_opportunities": len(extract_opportunities),
                        "guidance": [
                            {
                                "location": g.location,
                                "description": g.description,
                                "precise_steps": g.precise_steps,
                                "extractable_blocks": [
                                    {
                                        "suggested_name": block.suggested_name,
                                        "start_line": block.start_line,
                                        "end_line": block.end_line,
                                        "parameters": block.variables_used,
                                        "returns": block.variables_modified,
                                        "cut_instructions": [
                                            f"✂️ SELECT lines {block.start_line}-{block.end_line}",
                                            f"✂️ CUT selected lines (Ctrl+X)",
                                            f"📝 CREATE function: def {block.suggested_name}({', '.join(block.variables_used)}):",
                                            f"📝 PASTE code (Ctrl+V)",
                                            f"🔄 REPLACE with: {block.suggested_name}({', '.join(block.variables_used)})"
                                        ]
                                    } for block in (g.extractable_blocks or [])
                                ]
                            } for g in extract_opportunities
                        ]
                    }
                
                elif mode == "apply_changes":
                    applied_changes = []
                    current_code = content
                    
                    for opportunity in extract_opportunities:
                        if hasattr(opportunity, 'extractable_blocks') and opportunity.extractable_blocks:
                            for block in opportunity.extractable_blocks:
                                change_result = refactorer.apply_extraction(current_code, {
                                    'start_line': block.start_line,
                                    'end_line': block.end_line,
                                    'suggested_name': block.suggested_name,
                                    'variables_used': block.variables_used,
                                    'variables_modified': block.variables_modified,
                                    'description': block.description,
                                    'insertion_line': 1
                                })
                                
                                if change_result['success']:
                                    applied_changes.append(change_result)
                                    current_code = change_result['new_code']
                                    break  # One extraction at a time
                    
                    result = {
                        "mode": "apply_changes",
                        "function_filter": function_name,
                        "changes_applied": len(applied_changes),
                        "new_code": current_code,
                        "extractions": [
                            {
                                "function_name": change['extracted_function'],
                                "location": change['location'],
                                "summary": change['summary']
                            } for change in applied_changes if change['success']
                        ],
                        "errors": [change['error'] for change in applied_changes if not change['success']]
                    }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            
            elif name == "quick_analyze":
                content = arguments["content"]
                
                # Quick AST analysis
                try:
                    tree = ast.parse(content)
                    quick_results = {
                        "total_functions": 0,
                        "long_functions": [],
                        "complex_functions": [],
                        "too_many_params": []
                    }
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            quick_results["total_functions"] += 1
                            
                            # Check length
                            if hasattr(node, 'end_lineno') and node.end_lineno:
                                length = node.end_lineno - node.lineno + 1
                                if length > 20:
                                    quick_results["long_functions"].append({
                                        "name": node.name,
                                        "lines": f"{node.lineno}-{node.end_lineno}",
                                        "length": length,
                                        "quick_fix": f"Consider extracting logical blocks from {node.name}()"
                                    })
                            
                            # Check parameters
                            param_count = len(node.args.args)
                            if param_count > 5:
                                quick_results["too_many_params"].append({
                                    "name": node.name,
                                    "param_count": param_count,
                                    "quick_fix": f"Group {node.name}() parameters into a data structure"
                                })
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps(quick_results, indent=2)
                    )]
                    
                except SyntaxError as e:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({"syntax_error": str(e)})
                    )]
            
            else:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"})
                )]
                
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Tool execution failed: {str(e)}",
                    "tool": name
                })
            )]

    async def main():
        """Launch the unified MCP server"""
        print("🚀 Starting Python Refactoring MCP Server", file=sys.stderr)
        print("📡 Modes: guide_only (default) | apply_changes", file=sys.stderr)
        
        # Check for SSE mode via command line args
        if len(sys.argv) > 1 and sys.argv[1] == "--sse":
            port = int(sys.argv[2]) if len(sys.argv) > 2 else 3001
            print(f"🌐 Starting SSE server on port {port}", file=sys.stderr)
            
            transport = SseServerTransport("/messages")
            
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            
            app = FastAPI()
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            
            # Mount the SSE transport
            app.mount("/", transport.create_app())
            
            # Run the server
            uvicorn.run(app, host="0.0.0.0", port=port)
        else:
            print("🔄 Listening on stdin/stdout", file=sys.stderr)
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )

else:
    def main():
        print("❌ MCP not available")
        print("💡 Install with: uv add mcp")

if __name__ == "__main__":
    if MCP_AVAILABLE:
        asyncio.run(main())
    else:
        main()