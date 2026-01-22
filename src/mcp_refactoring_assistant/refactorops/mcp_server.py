#!/usr/bin/env python3
"""RefactorOps MCP server."""

# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from pydantic import ValidationError

from .adapters import (
    run_complexity_scan,
    run_dead_code_scan,
    run_jscpd,
    run_ruff_check,
    run_ruff_fix_safe,
)
from .schema import ScopeSpec
from .scope import resolve_scope
from .tools import analyze_repo_quality

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp.server import Server as MCPServer  # type: ignore[import-not-found]
    from mcp.server.stdio import stdio_server as MCPStdioServer  # type: ignore[import-not-found]
    from mcp import types as MCPTypes  # type: ignore[import-not-found]

MCP_IMPORT_ERROR: Optional[Exception] = None
MCPServer: Any = None
MCPStdioServer: Any = None
MCPTypes: Any = None

try:  # pragma: no cover - import path varies by environment
    from mcp.server import Server as MCPServer  # type: ignore[import-not-found]
    from mcp.server.stdio import stdio_server as MCPStdioServer  # type: ignore[import-not-found]
    from mcp import types as MCPTypes  # type: ignore[import-not-found]

    MCP_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - exercised in runtime only
    MCP_AVAILABLE = False
    MCP_IMPORT_ERROR = exc


SCOPE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["repo", "changed", "paths"]},
        "paths": {"type": "array", "items": {"type": "string"}},
        "git": {
            "type": "object",
            "properties": {
                "base": {"type": "string"},
                "head": {"type": "string"},
            },
        },
    },
}


def list_tools_data() -> List[Dict[str, Any]]:
    return [
        {
            "name": "analyze_repo_quality",
            "description": "Run RefactorOps analysis across repo scope",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "scope": SCOPE_SCHEMA,
                    "modes": {"type": "array", "items": {"type": "string"}},
                    "options": {"type": "object"},
                    "budgets": {"type": "object"},
                },
            },
        },
        {
            "name": "run_ruff_check",
            "description": "Run ruff check and return standardized findings",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "scope": SCOPE_SCHEMA,
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "globs": {"type": "array", "items": {"type": "string"}},
                    "select": {"type": "array", "items": {"type": "string"}},
                    "ignore": {"type": "array", "items": {"type": "string"}},
                    "timeout_sec": {"type": "integer"},
                },
            },
        },
        {
            "name": "run_ruff_fix_safe",
            "description": "Run ruff safe fixes and return diff",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "scope": SCOPE_SCHEMA,
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "select": {"type": "array", "items": {"type": "string"}},
                    "ignore": {"type": "array", "items": {"type": "string"}},
                    "timeout_sec": {"type": "integer"},
                    "apply": {"type": "boolean"},
                },
            },
        },
        {
            "name": "run_jscpd",
            "description": "Run jscpd duplication scan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "scope": SCOPE_SCHEMA,
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "min_lines": {"type": "integer"},
                    "min_tokens": {"type": "integer"},
                    "ignore": {"type": "array", "items": {"type": "string"}},
                    "timeout_sec": {"type": "integer"},
                    "use_npx": {"type": "boolean"},
                    "gitignore": {"type": "boolean"},
                    "no_symlinks": {"type": "boolean"},
                    "include_fragments": {"type": "boolean"},
                    "max_fragment_chars": {"type": "integer"},
                },
            },
        },
        {
            "name": "dead_code_scan",
            "description": "Run vulture-based dead code scan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "scope": SCOPE_SCHEMA,
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "min_confidence": {"type": "integer"},
                    "timeout_sec": {"type": "integer"},
                    "include_low_confidence": {"type": "boolean"},
                },
            },
        },
        {
            "name": "run_complexity_scan",
            "description": "Run complexity scan (cyclomatic/cognitive/long function)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "repo_root": {"type": "string"},
                    "scope": SCOPE_SCHEMA,
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "max_cyclomatic": {"type": "integer"},
                    "max_cognitive": {"type": "integer"},
                    "max_function_lines": {"type": "integer"},
                    "timeout_sec": {"type": "integer"},
                },
            },
        },
    ]


def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "analyze_repo_quality":
        result = analyze_repo_quality(arguments)
        return _serialize(result)

    repo_root = str(arguments.get("repo_root") or ".")
    scope_files, scope_errors = _resolve_scope_files(repo_root, arguments)

    if name == "run_ruff_check":
        python_files = _filter_python_files(scope_files)
        findings, metrics, errors = run_ruff_check(
            repo_root,
            python_files,
            _as_list(arguments.get("select")),
            _as_list(arguments.get("ignore")),
            int(arguments.get("timeout_sec", 120)),
        )
        return _tool_result(findings, metrics, scope_errors + errors)

    if name == "run_ruff_fix_safe":
        python_files = _filter_python_files(scope_files)
        findings, metrics, fix_result, errors = run_ruff_fix_safe(
            repo_root,
            python_files,
            _as_list(arguments.get("select")),
            _as_list(arguments.get("ignore")),
            int(arguments.get("timeout_sec", 120)),
            bool(arguments.get("apply", False)),
        )
        payload = _tool_result(findings, metrics, scope_errors + errors)
        payload["fix"] = fix_result
        return payload

    if name == "run_jscpd":
        findings, metrics, errors = run_jscpd(
            repo_root,
            scope_files,
            int(arguments.get("min_lines", 10)),
            int(arguments.get("min_tokens", 50)),
            _as_list(arguments.get("ignore")),
            int(arguments.get("timeout_sec", 120)),
            bool(arguments.get("use_npx", False)),
            bool(arguments.get("gitignore", True)),
            bool(arguments.get("no_symlinks", True)),
            bool(arguments.get("include_fragments", False)),
            int(arguments.get("max_fragment_chars", 2000)),
        )
        return _tool_result(findings, metrics, scope_errors + errors)

    if name == "dead_code_scan":
        python_files = _filter_python_files(scope_files)
        findings, metrics, errors = run_dead_code_scan(
            repo_root,
            python_files,
            int(arguments.get("min_confidence", 80)),
            int(arguments.get("timeout_sec", 120)),
            bool(arguments.get("include_low_confidence", False)),
        )
        return _tool_result(findings, metrics, scope_errors + errors)

    if name == "run_complexity_scan":
        python_files = _filter_python_files(scope_files)
        findings, metrics, errors = run_complexity_scan(
            repo_root,
            python_files,
            int(arguments.get("max_cyclomatic", 10)),
            int(arguments.get("max_cognitive", 15)),
            int(arguments.get("max_function_lines", 30)),
            int(arguments.get("timeout_sec", 120)),
        )
        return _tool_result(findings, metrics, scope_errors + errors)

    return {"error": f"Unknown tool: {name}"}


def _resolve_scope_files(repo_root: str, arguments: Dict[str, Any]) -> Tuple[List[str], List[Dict[str, Any]]]:
    errors: List[Dict[str, Any]] = []
    scope_input = arguments.get("scope")
    if scope_input is None:
        paths = _as_list(arguments.get("paths") or arguments.get("files"))
        if paths:
            scope_spec = ScopeSpec(type="paths", paths=paths)
        else:
            scope_spec = ScopeSpec(type="repo")
    else:
        try:
            scope_spec = ScopeSpec.model_validate(scope_input)
        except ValidationError as exc:
            errors.append(_error("invalid_scope", str(exc)))
            scope_spec = ScopeSpec(type="repo")

    resolved = resolve_scope(repo_root, scope_spec, fallback_paths=scope_spec.paths)
    errors.extend(_build_scope_errors(resolved))
    return resolved.files, errors


def _build_scope_errors(resolved) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []
    for code in resolved.errors:
        errors.append(_error(code, f"Scope resolution reported {code}"))
    for skipped in resolved.skipped:
        errors.append(
            _error(
                skipped.get("reason", "skipped"),
                f"Skipped {skipped.get('path', '')}",
            )
        )
    return errors


def _tool_result(findings, metrics, errors):
    return {
        "findings": [_serialize(finding) for finding in findings],
        "metrics": _serialize(metrics),
        "errors": errors,
    }


def _serialize(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _as_list(value: Optional[Sequence[str]]) -> List[str]:
    if value is None:
        return []
    return list(value)


def _filter_python_files(files: Sequence[str]) -> List[str]:
    python_files = []
    for path in files:
        lower = path.lower()
        if lower.endswith(".py") or lower.endswith(".pyi") or lower.endswith(".pyw"):
            python_files.append(path)
    return python_files


def _error(error_type: str, message: str) -> Dict[str, Any]:
    return {"type": error_type, "message": message}


if MCP_AVAILABLE:
    server = MCPServer("refactorops")

    @server.list_tools()
    async def handle_list_tools() -> List[Any]:
        return [MCPTypes.Tool(**tool) for tool in list_tools_data()]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[Any]:
        result = call_tool(name, arguments)
        payload = json.dumps(result, ensure_ascii=True)
        return [MCPTypes.TextContent(type="text", text=payload)]


async def run_server() -> None:
    if not MCP_AVAILABLE:
        raise RuntimeError(f"MCP not available: {MCP_IMPORT_ERROR}")
    async with MCPStdioServer() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    if not MCP_AVAILABLE:
        raise SystemExit("MCP not available. Install with: pip install mcp")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
