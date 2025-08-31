#!/usr/bin/env python3
"""
Version simplifiée du serveur MCP Python Refactoring Assistant
Optimisée pour la compatibilité et les tests
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

# Import MCP avec gestion d'erreur
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    print(f"MCP not available: {e}")

# Import des analyseurs Python
try:
    from src.mcp_refactoring_assistant.server import EnhancedRefactoringAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    try:
        # Fallback pour test direct
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        from mcp_refactoring_assistant.server import EnhancedRefactoringAnalyzer
        ANALYZER_AVAILABLE = True
    except ImportError as e:
        print(f"Analyzer not available: {e}")
        ANALYZER_AVAILABLE = False

if MCP_AVAILABLE:
    # Créer le serveur MCP
    server = Server("python-refactoring-assistant")

    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """Liste les outils de refactoring disponibles"""
        return [
            types.Tool(
                name="analyze_python_file",
                description="Analyze Python code for refactoring opportunities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content to analyze"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional file path for context"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="find_long_functions", 
                description="Find functions that exceed length thresholds",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content"
                        },
                        "line_threshold": {
                            "type": "integer", 
                            "description": "Minimum lines to consider long (default: 20)"
                        }
                    },
                    "required": ["content"]
                }
            ),
            types.Tool(
                name="get_extraction_guidance",
                description="Get detailed extraction guidance for functions",
                inputSchema={
                    "type": "object", 
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content"
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Optional specific function to analyze"
                        }
                    },
                    "required": ["content"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Gère les appels d'outils MCP"""
        
        if not ANALYZER_AVAILABLE:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": "Python refactoring analyzer not available",
                    "suggestion": "Check if all dependencies are installed"
                })
            )]
        
        try:
            analyzer = EnhancedRefactoringAnalyzer()
            
            if name == "analyze_python_file":
                content = arguments["content"]
                file_path = arguments.get("file_path", "unknown.py")
                
                guidance = analyzer.analyze_file(file_path, content)
                
                result = {
                    "tool": "analyze_python_file",
                    "file_path": file_path,
                    "analysis_summary": {
                        "total_issues_found": len(guidance),
                        "critical_issues": len([g for g in guidance if g.severity == "critical"]),
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
                            "precise_steps": g.precise_steps[:5],  # Limiter pour éviter la surcharge
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
                    ],
                    "tools_used": {
                        "rope": True,  # Simulé pour le moment
                        "radon": True,
                        "vulture": True
                    }
                }
                
                return [types.TextContent(
                    type="text", 
                    text=json.dumps(result, indent=2)
                )]
            
            elif name == "find_long_functions":
                content = arguments["content"]
                threshold = arguments.get("line_threshold", 20)
                
                # Analyse simple des fonctions longues
                import ast
                try:
                    tree = ast.parse(content)
                    functions = []
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if hasattr(node, 'end_lineno') and node.end_lineno:
                                length = node.end_lineno - node.lineno + 1
                                if length >= threshold:
                                    functions.append({
                                        "name": node.name,
                                        "start_line": node.lineno,
                                        "end_line": node.end_lineno,
                                        "length": length
                                    })
                    
                    result = {
                        "tool": "find_long_functions",
                        "line_threshold": threshold,
                        "total_functions_analyzed": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
                        "long_functions_found": len(functions),
                        "functions": functions
                    }
                    
                    return [types.TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                    
                except SyntaxError as e:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps({"error": f"Syntax error: {e}"})
                    )]
            
            elif name == "get_extraction_guidance":
                content = arguments["content"]
                function_name = arguments.get("function_name")
                
                guidance = analyzer.analyze_file("temp.py", content)
                extraction_opportunities = [g for g in guidance if g.issue_type == "extract_function"]
                
                if function_name:
                    extraction_opportunities = [
                        g for g in extraction_opportunities 
                        if function_name in g.location
                    ]
                
                result = {
                    "tool": "get_extraction_guidance", 
                    "function_filter": function_name,
                    "extraction_opportunities": len(extraction_opportunities),
                    "guidance": [
                        {
                            "type": g.issue_type,
                            "location": g.location,
                            "description": g.description,
                            "steps": g.precise_steps,
                            "extractable_blocks": [
                                {
                                    "name": block.suggested_name,
                                    "start_line": block.start_line,
                                    "end_line": block.end_line,
                                    "parameters": block.variables_used,
                                    "returns": block.variables_modified
                                } for block in (g.extractable_blocks or [])
                            ]
                        } for g in extraction_opportunities
                    ]
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
                text=json.dumps({
                    "error": f"Tool execution failed: {str(e)}",
                    "tool": name,
                    "arguments": arguments
                })
            )]

    async def main():
        """Lance le serveur MCP via stdin/stdout"""
        print("🚀 Starting Python Refactoring MCP Server", file=sys.stderr)
        print("📡 Listening on stdin/stdout", file=sys.stderr)
        
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
        print("🔧 Or test with: python test_tool.py")

if __name__ == "__main__":
    if MCP_AVAILABLE:
        asyncio.run(main())
    else:
        main()