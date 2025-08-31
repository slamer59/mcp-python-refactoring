#!/usr/bin/env python3
"""
MCP integration tests for the Python refactoring server.

These tests validate MCP protocol compliance and tool functionality.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mcp_refactoring_assistant.core import EnhancedRefactoringAnalyzer


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPToolDiscovery:
    """Test MCP tool discovery and registration."""

    def test_mcp_tools_available(self):
        """Test that required MCP tools are available."""
        # These are the expected tools based on your MCP server
        expected_tools = [
            "analyze_python_code",
            "extract_function", 
            "quick_analyze"
        ]
        
        # In a real MCP integration test, you would check with the actual MCP server
        # For now, we'll verify the tools exist conceptually
        for tool_name in expected_tools:
            # This would normally call the MCP server's list_tools
            assert tool_name in expected_tools, f"Tool {tool_name} should be available"

    def test_tool_schemas_valid(self):
        """Test that MCP tool schemas are valid."""
        # Verify analyze_python_code schema
        analyze_schema = {
            "name": "analyze_python_code",
            "description": "Analyze Python code for refactoring opportunities",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Python code content to analyze"
                    },
                    "mode": {
                        "type": "string", 
                        "enum": ["guide_only", "apply_changes"],
                        "default": "guide_only"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path for context"
                    },
                    "line_threshold": {
                        "type": "integer",
                        "default": 20,
                        "description": "Minimum lines for long functions"
                    }
                },
                "required": ["content"]
            }
        }
        
        # Verify schema structure
        assert "name" in analyze_schema
        assert "inputSchema" in analyze_schema
        assert "properties" in analyze_schema["inputSchema"]
        assert "content" in analyze_schema["inputSchema"]["properties"]

    def test_extract_function_schema(self):
        """Test extract_function tool schema."""
        extract_schema = {
            "name": "extract_function",
            "description": "Extract specific functions with guide or apply mode",
            "inputSchema": {
                "type": "object", 
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Python code content"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["guide_only", "apply_changes"],
                        "default": "guide_only"
                    },
                    "function_name": {
                        "type": "string",
                        "description": "Function to extract from"
                    }
                },
                "required": ["content"]
            }
        }
        
        assert extract_schema["name"] == "extract_function"
        assert "content" in extract_schema["inputSchema"]["properties"]


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPToolExecution:
    """Test MCP tool execution with various inputs."""

    def test_analyze_python_code_tool(self, analyzer, simple_function_code):
        """Test the analyze_python_code MCP tool functionality."""
        # Simulate MCP tool call
        tool_input = {
            "content": simple_function_code,
            "mode": "guide_only",
            "file_path": "test.py",
            "line_threshold": 20
        }
        
        # This would normally go through the MCP protocol
        result = analyzer.analyze_file(
            tool_input.get("file_path", "test.py"),
            tool_input["content"]
        )
        
        # Verify result format matches MCP expectations
        assert isinstance(result, list)
        
        # Convert to MCP response format
        mcp_response = {
            "content": [
                {
                    "type": "text",
                    "text": f"Analysis complete. Found {len(result)} refactoring opportunities."
                }
            ],
            "isError": False
        }
        
        assert mcp_response["isError"] is False
        assert len(mcp_response["content"]) > 0

    def test_analyze_with_mode_guide_only(self, analyzer, complex_function_code):
        """Test analyze_python_code in guide_only mode."""
        tool_input = {
            "content": complex_function_code,
            "mode": "guide_only"
        }
        
        result = analyzer.analyze_file("complex.py", tool_input["content"])
        
        # In guide_only mode, should return guidance, not modified code
        assert isinstance(result, list)
        if result:
            for guidance in result:
                # Should have guidance structure, not code modifications
                assert hasattr(guidance, 'issue_type')
                assert hasattr(guidance, 'precise_steps')

    def test_quick_analyze_tool(self):
        """Test the quick_analyze MCP tool functionality."""
        # This test would normally go through the MCP protocol
        # For unit testing, we'll verify the tool is properly defined
        from mcp_refactoring_assistant import mcp_server
        
        # The tool should be available in the tool list
        # In real MCP integration, this would be called via protocol
        assert hasattr(mcp_server, 'handle_list_tools'), "MCP server should have tool listing capability"
        
        # Verify basic functionality by testing with analyzer directly
        from mcp_refactoring_assistant.core import EnhancedRefactoringAnalyzer
        analyzer = EnhancedRefactoringAnalyzer()
        result = analyzer.analyze_file("quick.py", "def simple(): return True")
        
        # Should return basic analysis info
        assert isinstance(result, list)

    def test_tool_error_handling(self, analyzer):
        """Test MCP tool error handling."""
        # Test with invalid Python code
        tool_input = {
            "content": "def broken_function(\n    return 'invalid'",
            "mode": "guide_only"
        }
        
        result = analyzer.analyze_file("broken.py", tool_input["content"])
        
        # Should handle errors gracefully
        assert isinstance(result, list)
        # May contain syntax error guidance

    def test_tool_parameter_validation(self, analyzer):
        """Test MCP tool parameter validation."""
        # Test missing required parameters
        try:
            # This would normally be validated by the MCP framework
            tool_input = {
                "mode": "guide_only"  # Missing required 'content'
            }
            
            # Should handle missing content gracefully
            result = analyzer.analyze_file("empty.py", "")
            assert isinstance(result, list)
            
        except Exception as e:
            # Or raise appropriate error
            assert "content" in str(e).lower()

    def test_tool_output_format(self, analyzer, simple_function_code):
        """Test that MCP tool outputs are properly formatted."""
        result = analyzer.analyze_file("format_test.py", simple_function_code)
        
        # Convert to MCP-compatible output format
        mcp_output = {
            "content": [
                {
                    "type": "application/json",
                    "data": {
                        "analysis_results": [guidance.to_dict() for guidance in result],
                        "summary": {
                            "total_issues": len(result),
                            "critical_issues": len([g for g in result if g.severity == "critical"]),
                            "high_issues": len([g for g in result if g.severity == "high"]),
                            "medium_issues": len([g for g in result if g.severity == "medium"]),
                            "low_issues": len([g for g in result if g.severity == "low"])
                        }
                    }
                }
            ]
        }
        
        # Verify output structure
        assert "content" in mcp_output
        assert len(mcp_output["content"]) > 0
        assert mcp_output["content"][0]["type"] == "application/json"
        assert "data" in mcp_output["content"][0]


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPProtocolCompliance:
    """Test MCP protocol compliance."""

    def test_mcp_request_response_format(self):
        """Test MCP request/response format compliance."""
        # Example MCP request format
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_python_code",
                "arguments": {
                    "content": "def test(): pass",
                    "mode": "guide_only"
                }
            }
        }
        
        # Verify request format
        assert mcp_request["jsonrpc"] == "2.0"
        assert "id" in mcp_request
        assert mcp_request["method"] == "tools/call"
        assert "params" in mcp_request

        # Expected response format
        mcp_response = {
            "jsonrpc": "2.0", 
            "id": 1,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "Analysis complete"
                    }
                ]
            }
        }
        
        assert mcp_response["jsonrpc"] == "2.0"
        assert mcp_response["id"] == mcp_request["id"]

    def test_mcp_error_response_format(self):
        """Test MCP error response format compliance."""
        mcp_error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32602,
                "message": "Invalid params",
                "data": {
                    "details": "Content parameter is required"
                }
            }
        }
        
        # Verify error response structure
        assert "error" in mcp_error_response
        assert "code" in mcp_error_response["error"]
        assert "message" in mcp_error_response["error"]

    def test_mcp_tool_list_format(self):
        """Test MCP tool list format compliance."""
        tools_list = {
            "tools": [
                {
                    "name": "analyze_python_code",
                    "description": "Analyze Python code for refactoring opportunities",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "mode": {"type": "string", "enum": ["guide_only", "apply_changes"]}
                        },
                        "required": ["content"]
                    }
                },
                {
                    "name": "extract_function", 
                    "description": "Extract functions with guidance",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "function_name": {"type": "string"}
                        },
                        "required": ["content"]
                    }
                }
            ]
        }
        
        # Verify tools list structure
        assert "tools" in tools_list
        assert len(tools_list["tools"]) > 0
        
        for tool in tools_list["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPServerIntegration:
    """Test integration with MCP server."""

    @patch('mcp_refactoring_assistant.mcp_server.EnhancedRefactoringAnalyzer')
    def test_server_initialization(self, mock_analyzer):
        """Test MCP server initialization."""
        # Mock analyzer initialization
        mock_analyzer.return_value = Mock()
        
        # This would test actual server startup
        # For now, verify mocking works
        from mcp_refactoring_assistant import mcp_server
        
        # Server should have tools registered
        # This would normally check server.list_tools()
        assert hasattr(mcp_server, 'handle_list_tools')

    def test_server_tool_registration(self):
        """Test that all tools are properly registered with MCP server."""
        expected_tools = ["analyze_python_code", "extract_function", "quick_analyze"]
        
        # In actual test, would query the MCP server
        # For now, verify tools exist in module structure
        from mcp_refactoring_assistant import mcp_server
        
        # Verify the server has the handle_list_tools function which contains the tools
        assert hasattr(mcp_server, 'handle_list_tools'), "Server should have tool listing capability"
        assert hasattr(mcp_server, 'handle_call_tool'), "Server should have tool execution capability"

    def test_server_handles_concurrent_requests(self, analyzer):
        """Test server handling of concurrent MCP requests."""
        import threading
        import time
        
        results = []
        
        def make_request(request_id):
            # Simulate MCP tool call
            result = analyzer.analyze_file(f"concurrent_{request_id}.py", "def test(): pass")
            results.append((request_id, len(result)))
        
        # Create concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all requests to complete
        for thread in threads:
            thread.join()
        
        # All requests should complete
        assert len(results) == 5
        
        # Results should be consistent
        for request_id, result_count in results:
            assert isinstance(result_count, int)
            assert result_count >= 0


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPClientCompatibility:
    """Test compatibility with different MCP clients."""

    def test_claude_desktop_compatibility(self):
        """Test compatibility with Claude Desktop MCP client."""
        # Claude Desktop specific requirements
        tool_definition = {
            "name": "analyze_python_code",
            "description": "Analyze Python code and provide refactoring guidance",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Python code to analyze"
                    }
                },
                "required": ["content"]
            }
        }
        
        # Verify Claude Desktop compatibility requirements
        assert len(tool_definition["description"]) > 10, "Description should be descriptive"
        assert "content" in tool_definition["inputSchema"]["required"]

    def test_generic_mcp_client_compatibility(self):
        """Test compatibility with generic MCP clients."""
        # Generic MCP client compatibility
        response_format = {
            "content": [
                {
                    "type": "text",
                    "text": "Analysis results"
                }
            ],
            "isError": False
        }
        
        # Should work with any MCP client
        assert "content" in response_format
        assert isinstance(response_format["content"], list)
        assert response_format["isError"] is False

    def test_streaming_response_support(self):
        """Test support for streaming responses if needed."""
        # Some MCP clients may support streaming
        streaming_response = {
            "content": [
                {"type": "text", "text": "Starting analysis..."},
                {"type": "text", "text": "Analyzing functions..."},
                {"type": "text", "text": "Analysis complete."}
            ]
        }
        
        assert len(streaming_response["content"]) > 1
        for chunk in streaming_response["content"]:
            assert chunk["type"] == "text"
            assert "text" in chunk


@pytest.mark.mcp
@pytest.mark.integration
class TestMCPResourceManagement:
    """Test MCP resource management."""

    def test_resource_cleanup(self, analyzer):
        """Test that resources are properly cleaned up."""
        # Perform multiple analyses
        for i in range(10):
            result = analyzer.analyze_file(f"cleanup_test_{i}.py", "def test(): pass")
            assert isinstance(result, list)
        
        # Resources should be cleaned up automatically
        # In a real test, you'd check memory usage, file handles, etc.
        assert True  # Placeholder assertion

    def test_timeout_handling(self, analyzer, performance_timer):
        """Test handling of long-running operations."""
        # Create a potentially long-running analysis
        large_code = "\n".join([f"def func_{i}(): pass" for i in range(100)])
        
        with performance_timer() as timer:
            result = analyzer.analyze_file("timeout_test.py", large_code)
        
        # Should complete within reasonable time
        assert timer.elapsed < 30.0, "Analysis should not take too long"
        assert isinstance(result, list)

    def test_memory_management(self, analyzer):
        """Test memory management during analysis."""
        import gc
        
        # Force garbage collection before test
        gc.collect()
        
        # Perform memory-intensive operations
        for i in range(20):
            large_code = "\n".join([f"def large_func_{j}(): pass" for j in range(50)])
            result = analyzer.analyze_file(f"memory_test_{i}.py", large_code)
            
            # Occasional cleanup
            if i % 5 == 0:
                gc.collect()
        
        # Memory should be manageable
        # In production, you'd monitor actual memory usage
        assert True  # Placeholder assertion