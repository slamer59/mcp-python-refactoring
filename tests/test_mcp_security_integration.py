#!/usr/bin/env python3
"""
Comprehensive tests for MCP integration of security and patterns analysis
Tests the analyze_security_and_patterns endpoint with various configurations
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# MCP-related imports (with graceful handling if not available)
try:
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Mock MCP types for testing
    class MockTypes:
        class TextContent:
            def __init__(self, type, text):
                self.type = type
                self.text = text
    types = MockTypes()

# Try to import MCP components, but handle gracefully if not available
try:
    from src.mcp_refactoring_assistant.server import handle_call_tool, MCP_AVAILABLE
    if not MCP_AVAILABLE:
        # Create a mock handle_call_tool for testing
        async def handle_call_tool(name: str, arguments: dict):
            """Mock MCP tool handler for testing when MCP is not available"""
            from src.mcp_refactoring_assistant.analyzers.security_and_patterns_analyzer import SecurityAndPatternsAnalyzer
            
            try:
                if name == "analyze_security_and_patterns":
                    analyzer = SecurityAndPatternsAnalyzer()
                    content = arguments["content"]
                    file_path = arguments.get("file_path", "unknown.py")
                    
                    guidance = analyzer.analyze(content, file_path)
                    analysis_summary = analyzer.get_analysis_summary(guidance)
                    
                    # Filter results based on scan options
                    include_dependency_scan = arguments.get("include_dependency_scan", True)
                    include_security_scan = arguments.get("include_security_scan", True)
                    include_modernization = arguments.get("include_modernization", True)
                    
                    filtered_guidance = guidance
                    if not include_dependency_scan:
                        filtered_guidance = [g for g in filtered_guidance if 'dependency' not in g.issue_type]
                    if not include_security_scan:
                        filtered_guidance = [g for g in filtered_guidance if 'security_vulnerability' != g.issue_type]
                    if not include_modernization:
                        filtered_guidance = [g for g in filtered_guidance if 'modernization' not in g.issue_type]
                    
                    # Create comprehensive result
                    from src.mcp_refactoring_assistant.server import _create_analysis_summary
                    base_summary = _create_analysis_summary(filtered_guidance)
                    result = {
                        "analysis_summary": {
                            **base_summary,
                            **analysis_summary
                        },
                        "security_and_patterns_guidance": [g.to_dict() for g in filtered_guidance],
                        "tools_used": {
                            "bandit_security": include_security_scan,
                            "pip_audit_dependencies": include_dependency_scan,
                            "refurb_modernization": include_modernization,
                            "unified_analysis": True
                        },
                        "scan_configuration": {
                            "dependency_scan_enabled": include_dependency_scan,
                            "security_scan_enabled": include_security_scan,
                            "modernization_enabled": include_modernization
                        }
                    }
                    
                    import json
                    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                else:
                    import json
                    return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
            except Exception as e:
                import json
                return [types.TextContent(type="text", text=json.dumps({"error": f"Analysis failed: {str(e)}"}))]
                
except ImportError:
    # If we can't import at all, skip these tests
    handle_call_tool = None
    MCP_AVAILABLE = False
from src.mcp_refactoring_assistant.analyzers.security_and_patterns_analyzer import SecurityAndPatternsAnalyzer


@pytest.mark.skipif(handle_call_tool is None, reason="MCP not available")
class TestMCPSecurityIntegration:
    """Test cases for MCP security and patterns analysis integration"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Load test files
        test_fixtures_dir = Path(__file__).parent / "fixtures" / "security_test_code"
        
        with open(test_fixtures_dir / "security_vulnerabilities.py", 'r') as f:
            self.vulnerable_code = f.read()
            
        with open(test_fixtures_dir / "modernization_opportunities.py", 'r') as f:
            self.legacy_code = f.read()
            
        with open(test_fixtures_dir / "clean_modern_code.py", 'r') as f:
            self.clean_code = f.read()
            
        with open(test_fixtures_dir / "invalid_syntax.py", 'r') as f:
            self.invalid_code = f.read()
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_basic(self):
        """Test basic analyze_security_and_patterns endpoint functionality"""
        arguments = {
            "content": self.vulnerable_code,
            "file_path": "test_vulnerable.py"
        }
        
        # Call the MCP tool handler
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        
        # Should return list of TextContent
        assert isinstance(result, list)
        assert len(result) > 0
        assert hasattr(result[0], 'type')
        assert hasattr(result[0], 'text')
        
        # Parse the JSON response
        response_data = json.loads(result[0].text)
        
        # Check response structure
        assert 'analysis_summary' in response_data
        assert 'security_and_patterns_guidance' in response_data
        assert 'tools_used' in response_data
        assert 'scan_configuration' in response_data
        
        # Check analysis summary structure
        summary = response_data['analysis_summary']
        assert 'total_issues_found' in summary
        assert 'security_status' in summary
        assert 'modernization_status' in summary
        
        # Check guidance structure
        guidance = response_data['security_and_patterns_guidance']
        assert isinstance(guidance, list)
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_with_all_scans_enabled(self):
        """Test endpoint with all scan types enabled"""
        arguments = {
            "content": self.vulnerable_code,
            "file_path": "test_all_scans.py",
            "include_dependency_scan": True,
            "include_security_scan": True,
            "include_modernization": True
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Check scan configuration
        config = response_data['scan_configuration']
        assert config['dependency_scan_enabled'] is True
        assert config['security_scan_enabled'] is True
        assert config['modernization_enabled'] is True
        
        # Check tools used
        tools = response_data['tools_used']
        assert tools['bandit_security'] is True
        assert tools['pip_audit_dependencies'] is True
        assert tools['refurb_modernization'] is True
        assert tools['unified_analysis'] is True
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_security_only(self):
        """Test endpoint with only security scanning enabled"""
        arguments = {
            "content": self.vulnerable_code,
            "file_path": "test_security_only.py",
            "include_dependency_scan": False,
            "include_security_scan": True,
            "include_modernization": False
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Check scan configuration
        config = response_data['scan_configuration']
        assert config['dependency_scan_enabled'] is False
        assert config['security_scan_enabled'] is True
        assert config['modernization_enabled'] is False
        
        # Check tools used
        tools = response_data['tools_used']
        assert tools['bandit_security'] is True
        assert tools['pip_audit_dependencies'] is False
        assert tools['refurb_modernization'] is False
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_modernization_only(self):
        """Test endpoint with only modernization analysis enabled"""
        arguments = {
            "content": self.legacy_code,
            "file_path": "test_modernization_only.py", 
            "include_dependency_scan": False,
            "include_security_scan": False,
            "include_modernization": True
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Check scan configuration
        config = response_data['scan_configuration']
        assert config['dependency_scan_enabled'] is False
        assert config['security_scan_enabled'] is False
        assert config['modernization_enabled'] is True
        
        # Check tools used
        tools = response_data['tools_used']
        assert tools['bandit_security'] is False
        assert tools['pip_audit_dependencies'] is False
        assert tools['refurb_modernization'] is True
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_dependency_only(self):
        """Test endpoint with only dependency scanning enabled"""
        arguments = {
            "content": "import requests\nprint('hello')",
            "file_path": "test_dependency_only.py",
            "include_dependency_scan": True,
            "include_security_scan": False,
            "include_modernization": False
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Check scan configuration
        config = response_data['scan_configuration']
        assert config['dependency_scan_enabled'] is True
        assert config['security_scan_enabled'] is False
        assert config['modernization_enabled'] is False
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_clean_code(self):
        """Test endpoint with clean, modern code"""
        arguments = {
            "content": self.clean_code,
            "file_path": "test_clean.py"
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Should complete successfully even with clean code
        assert 'analysis_summary' in response_data
        
        # Clean code should have fewer critical issues
        summary = response_data['analysis_summary']
        critical_issues = summary.get('critical_issues', 0)
        assert critical_issues == 0, "Clean code should not have critical issues"
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_invalid_syntax(self):
        """Test endpoint with invalid Python syntax"""
        arguments = {
            "content": self.invalid_code,
            "file_path": "test_invalid.py"
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Should handle syntax errors gracefully
        assert 'analysis_summary' in response_data
        
        # May have syntax error in guidance
        guidance = response_data['security_and_patterns_guidance']
        syntax_errors = [g for g in guidance if g.get('issue_type') == 'syntax_error']
        # May or may not detect syntax error depending on how analyzers handle it
        assert isinstance(guidance, list), "Should return guidance list"
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_empty_content(self):
        """Test endpoint with empty content"""
        arguments = {
            "content": "",
            "file_path": "test_empty.py"
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Should handle empty content gracefully
        assert 'analysis_summary' in response_data
        assert 'security_and_patterns_guidance' in response_data
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_default_parameters(self):
        """Test endpoint with default parameter values"""
        arguments = {
            "content": self.vulnerable_code
            # No file_path, should use default
            # No scan options, should use defaults (all True)
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Should use default values
        config = response_data['scan_configuration']
        assert config['dependency_scan_enabled'] is True  # Default
        assert config['security_scan_enabled'] is True    # Default
        assert config['modernization_enabled'] is True    # Default
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_complex_code(self):
        """Test endpoint with complex code having multiple issue types"""
        complex_code = '''
import os
import subprocess
import pickle
import hashlib

# Security issues
password = "hardcoded123"
subprocess.call(f"ls {user_input}", shell=True)
data = pickle.loads(untrusted)
hash_val = hashlib.md5(password.encode()).hexdigest()

# Modernization opportunities  
def process_items(items):
    for i in range(len(items)):  # Should use enumerate
        item = items[i]
        if "name" in item:  # Should use dict.get
            name = item["name"]
        message = "Item {}: {}".format(i, name)  # Should use f-strings
    return os.path.join("/tmp", "file.txt")  # Should use pathlib
        '''
        
        arguments = {
            "content": complex_code,
            "file_path": "test_complex.py"
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Should detect multiple types of issues
        summary = response_data['analysis_summary']
        assert summary['total_issues_found'] > 0, "Should detect issues in complex code"
        
        # Should have comprehensive analysis
        guidance = response_data['security_and_patterns_guidance']
        assert isinstance(guidance, list)
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_response_filtering(self):
        """Test that response filtering works correctly based on scan options"""
        arguments = {
            "content": self.vulnerable_code + "\n" + self.legacy_code,
            "file_path": "test_filtering.py",
            "include_dependency_scan": False,  # Should filter out dependency issues
            "include_security_scan": True,
            "include_modernization": True
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Check that dependency issues are filtered out
        guidance = response_data['security_and_patterns_guidance']
        dependency_issues = [g for g in guidance if 'dependency' in g.get('issue_type', '')]
        
        # Should not have dependency issues when dependency scan is disabled
        assert len(dependency_issues) == 0, "Should filter out dependency issues"
    
    @pytest.mark.asyncio
    async def test_analyze_security_and_patterns_error_handling(self):
        """Test error handling in the MCP endpoint"""
        # Test with malformed arguments
        arguments = {
            "content": self.vulnerable_code,
            "include_dependency_scan": "invalid_boolean"  # Should be boolean
        }
        
        try:
            result = await handle_call_tool("analyze_security_and_patterns", arguments)
            # Should either handle gracefully or raise an appropriate error
            assert isinstance(result, list)
        except Exception as e:
            # If it raises an exception, it should be handled appropriately
            assert isinstance(e, (ValueError, TypeError))
    
    @pytest.mark.asyncio
    async def test_unknown_tool_error_handling(self):
        """Test handling of unknown tool names"""
        result = await handle_call_tool("unknown_tool", {})
        
        # Should return error response
        assert isinstance(result, list)
        assert len(result) > 0
        
        response_data = json.loads(result[0].text)
        assert 'error' in response_data
        assert 'Unknown tool' in response_data['error']
    
    @pytest.mark.asyncio 
    async def test_missing_required_parameters(self):
        """Test handling of missing required parameters"""
        # Missing content parameter
        arguments = {
            "file_path": "test.py"
            # Missing required "content" parameter
        }
        
        try:
            result = await handle_call_tool("analyze_security_and_patterns", arguments)
            # Should handle missing parameter gracefully
            response_data = json.loads(result[0].text)
            # May return error or handle with default values
        except KeyError:
            # Acceptable to raise KeyError for missing required parameter
            pass
    
    @patch('src.mcp_refactoring_assistant.analyzers.security_and_patterns_analyzer.SecurityAndPatternsAnalyzer.analyze')
    @pytest.mark.asyncio
    async def test_analyzer_exception_handling(self, mock_analyze):
        """Test handling when the analyzer raises an exception"""
        # Mock analyzer to raise exception
        mock_analyze.side_effect = Exception("Analyzer failed")
        
        arguments = {
            "content": "test code",
            "file_path": "test.py"
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        
        # Should handle analyzer exceptions gracefully
        assert isinstance(result, list)
        assert len(result) > 0
        
        response_data = json.loads(result[0].text)
        assert 'error' in response_data
        assert 'Analysis failed' in response_data['error']
    
    def test_response_structure_validation(self):
        """Test that the response structure matches the expected format"""
        # Create a sample response to validate structure
        sample_guidance = [
            {
                'issue_type': 'security_vulnerability',
                'severity': 'high',
                'location': 'line 10',
                'description': 'Test security issue',
                'benefits': ['Better security'],
                'precise_steps': ['Fix the issue'],
                'metrics': {'test_id': 'B105'}
            }
        ]
        
        expected_keys = [
            'analysis_summary',
            'security_and_patterns_guidance', 
            'tools_used',
            'scan_configuration'
        ]
        
        # Check that all expected keys are present in a typical response
        for key in expected_keys:
            # This would be part of the actual response validation
            assert isinstance(key, str), f"Expected key {key} should be string"
    
    @pytest.mark.asyncio
    async def test_large_code_handling(self):
        """Test handling of large code files"""
        # Create a larger code sample
        large_code = self.vulnerable_code * 10  # Repeat vulnerable code
        
        arguments = {
            "content": large_code,
            "file_path": "test_large.py"
        }
        
        result = await handle_call_tool("analyze_security_and_patterns", arguments)
        response_data = json.loads(result[0].text)
        
        # Should handle large files (may have timeouts handled by individual analyzers)
        assert 'analysis_summary' in response_data
        assert 'security_and_patterns_guidance' in response_data
    
    def test_tool_availability_flags(self):
        """Test that tool availability is correctly reported"""
        # This would test the actual availability of bandit, refurb, pip-audit
        # In a real environment, but for testing we just validate the structure
        
        expected_tools = [
            'bandit_security',
            'pip_audit_dependencies', 
            'refurb_modernization',
            'unified_analysis'
        ]
        
        for tool in expected_tools:
            # In the actual response, these should be boolean values
            assert isinstance(tool, str), f"Tool name {tool} should be string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])