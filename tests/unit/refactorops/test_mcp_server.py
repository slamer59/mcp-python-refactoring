#!/usr/bin/env python3
"""Unit tests for RefactorOps MCP server helpers."""

from mcp_refactoring_assistant.refactorops import mcp_server


def test_list_tools_contains_refactorops_tools():
    tools = mcp_server.list_tools_data()
    names = {tool["name"] for tool in tools}
    assert "analyze_repo_quality" in names
    assert "run_ruff_check" in names
    assert "run_ruff_fix_safe" in names
    assert "run_jscpd" in names
    assert "dead_code_scan" in names
    assert "run_complexity_scan" in names


def test_call_tool_analyze_repo_quality(monkeypatch):
    class DummyResult:
        def to_dict(self):
            return {"summary": {"status": "pass"}}

    monkeypatch.setattr(mcp_server, "analyze_repo_quality", lambda *_args, **_kwargs: DummyResult())

    result = mcp_server.call_tool("analyze_repo_quality", {"repo_root": "."})

    assert result["summary"]["status"] == "pass"


def test_call_tool_unknown_returns_error():
    result = mcp_server.call_tool("unknown_tool", {})

    assert "error" in result
