"""AST-based long-function detection, shared by the MCP server and CLI."""

import ast
from typing import Any, Dict


def find_long_functions(content: str, line_threshold: int = 20) -> Dict[str, Any]:
    """Find functions in `content` whose line count is >= line_threshold.

    Raises SyntaxError if `content` cannot be parsed; callers decide how to report it.
    """
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

    return {
        "total_functions_analyzed": len(
            [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        ),
        "long_functions_found": len(long_functions),
        "line_threshold": line_threshold,
        "functions": long_functions,
    }
