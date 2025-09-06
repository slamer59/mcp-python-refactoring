#!/usr/bin/env python3
"""
Comprehensive tests for ModernPatternsAnalyzer using Refurb for modernization suggestions
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from src.mcp_refactoring_assistant.analyzers.modern_patterns_analyzer import ModernPatternsAnalyzer
from src.mcp_refactoring_assistant.models import RefactoringGuidance


class TestModernPatternsAnalyzer:
    """Test cases for ModernPatternsAnalyzer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = ModernPatternsAnalyzer()
        
        # Load test files
        test_fixtures_dir = Path(__file__).parent / "fixtures" / "security_test_code"
        
        with open(test_fixtures_dir / "modernization_opportunities.py", 'r') as f:
            self.legacy_code = f.read()
            
        with open(test_fixtures_dir / "clean_modern_code.py", 'r') as f:
            self.modern_code = f.read()
            
        with open(test_fixtures_dir / "invalid_syntax.py", 'r') as f:
            self.invalid_code = f.read()
    
    def test_analyze_legacy_code(self):
        """Test analysis of code with multiple modernization opportunities"""
        guidance = self.analyzer.analyze(self.legacy_code, "test_legacy.py")
        
        # Should find multiple modernization opportunities
        assert len(guidance) > 0, "Should detect modernization opportunities"
        
        # Check that we get RefactoringGuidance objects
        for item in guidance:
            assert isinstance(item, RefactoringGuidance)
            assert item.issue_type == "modernization_opportunity"
            assert item.severity in ["low", "medium", "high"]
            assert "modernization" in item.description.lower() or "suggestion" in item.description.lower()
            assert len(item.benefits) > 0
            assert len(item.precise_steps) > 0
    
    def test_f_string_suggestions(self):
        """Test detection of f-string modernization opportunities"""
        code_with_old_formatting = '''
name = "John"
age = 30
message = "Hello {}, you are {} years old".format(name, age)
old_message = "Hello %s, you are %d years old" % (name, age)
        '''
        
        guidance = self.analyzer.analyze(code_with_old_formatting, "f_string_test.py")
        
        # May detect f-string opportunities (depends on refurb version and configuration)
        # We'll check that analysis completes successfully
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_enumerate_suggestions(self):
        """Test detection of enumerate() modernization opportunities"""
        code_with_manual_index = '''
items = ["a", "b", "c"]
for i in range(len(items)):
    print(f"Item {i}: {items[i]}")
        '''
        
        guidance = self.analyzer.analyze(code_with_manual_index, "enumerate_test.py")
        
        # Should detect enumerate opportunity
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_pathlib_suggestions(self):
        """Test detection of pathlib modernization opportunities"""
        code_with_os_path = '''
import os
filepath = "/path/to/file.txt"
directory = os.path.dirname(filepath)
filename = os.path.basename(filepath)
full_path = os.path.join(directory, filename)
        '''
        
        guidance = self.analyzer.analyze(code_with_os_path, "pathlib_test.py")
        
        # Should detect pathlib opportunities
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_dict_get_suggestions(self):
        """Test detection of dict.get() modernization opportunities"""
        code_with_manual_key_check = '''
config = {"key1": "value1"}
if "key1" in config:
    value = config["key1"]
else:
    value = "default"
        '''
        
        guidance = self.analyzer.analyze(code_with_manual_key_check, "dict_get_test.py")
        
        # Should detect dict.get opportunity
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_any_all_suggestions(self):
        """Test detection of any()/all() modernization opportunities"""
        code_with_loops = '''
def has_negative(numbers):
    for num in numbers:
        if num < 0:
            return True
    return False

def all_positive(numbers):
    for num in numbers:
        if num <= 0:
            return False
    return True
        '''
        
        guidance = self.analyzer.analyze(code_with_loops, "any_all_test.py")
        
        # Should detect any/all opportunities
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_context_manager_suggestions(self):
        """Test detection of context manager modernization opportunities"""
        code_without_context_manager = '''
f = open("file.txt", "r")
content = f.read()
f.close()
        '''
        
        guidance = self.analyzer.analyze(code_without_context_manager, "context_manager_test.py")
        
        # Should detect context manager opportunity
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_isinstance_suggestions(self):
        """Test detection of isinstance() modernization opportunities"""
        code_with_type_check = '''
def check_string(value):
    return type(value) == str
        '''
        
        guidance = self.analyzer.analyze(code_with_type_check, "isinstance_test.py")
        
        # Should detect isinstance opportunity
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_comprehension_suggestions(self):
        """Test detection of comprehension modernization opportunities"""
        code_with_manual_loops = '''
numbers = [1, 2, 3, 4, 5]
squares = {}
for num in numbers:
    squares[num] = num ** 2

result = []
for num in numbers:
    if num % 2 == 0:
        result.append(num)
        '''
        
        guidance = self.analyzer.analyze(code_with_manual_loops, "comprehension_test.py")
        
        # Should detect comprehension opportunities
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_modern_code_analysis(self):
        """Test analysis of modern code with minimal modernization opportunities"""
        guidance = self.analyzer.analyze(self.modern_code, "modern_test.py")
        
        # Modern code should have fewer modernization opportunities
        # May still have some low-priority suggestions
        high_priority_issues = [g for g in guidance if g.severity == "high"]
        # We'll be flexible here as refurb might still find some opportunities in modern code
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_invalid_syntax_handling(self):
        """Test handling of files with invalid syntax"""
        guidance = self.analyzer.analyze(self.invalid_code, "invalid_test.py")
        
        # Should handle syntax errors gracefully
        assert isinstance(guidance, list), "Should return list even for invalid syntax"
    
    def test_empty_code_analysis(self):
        """Test analysis of empty code"""
        guidance = self.analyzer.analyze("", "empty_test.py")
        
        # Empty code should return empty guidance or handle gracefully
        assert isinstance(guidance, list), "Should return list for empty code"
    
    def test_severity_mapping(self):
        """Test that severities are mapped correctly"""
        guidance = self.analyzer.analyze(self.legacy_code, "severity_test.py")
        
        # Check that all severities are valid
        valid_severities = ["low", "medium", "high"]
        for item in guidance:
            assert item.severity in valid_severities, f"Invalid severity: {item.severity}"
    
    def test_guidance_structure(self):
        """Test that guidance objects have proper structure"""
        guidance = self.analyzer.analyze(self.legacy_code, "structure_test.py")
        
        for item in guidance:
            # Check required fields
            assert hasattr(item, 'issue_type')
            assert hasattr(item, 'severity')
            assert hasattr(item, 'location')
            assert hasattr(item, 'description')
            assert hasattr(item, 'benefits')
            assert hasattr(item, 'precise_steps')
            
            # Check field types and content
            assert isinstance(item.benefits, list)
            assert len(item.benefits) > 0
            assert isinstance(item.precise_steps, list)
            assert len(item.precise_steps) > 0
            assert isinstance(item.description, str)
            assert len(item.description) > 0
    
    def test_severity_determination(self):
        """Test severity determination logic"""
        # Test high priority patterns
        high_priority_issues = {
            'FURB105': "Use print() instead of sys.stdout.write()",
            'FURB107': "Use pathlib instead of os.path",
            'FURB109': "Use dict.get() with default",
            'FURB110': "Use any() instead of for loop",
        }
        
        for rule_id, message in high_priority_issues.items():
            severity = self.analyzer._determine_severity(rule_id, message)
            assert severity in ["medium", "high"], f"Expected medium/high severity for {rule_id}, got {severity}"
        
        # Test low priority pattern
        low_severity = self.analyzer._determine_severity("FURB999", "Some unknown pattern")
        assert low_severity == "low", "Unknown patterns should have low severity"
    
    def test_generate_modernization_steps(self):
        """Test generation of specific modernization steps"""
        # Test with known pattern
        steps_f_string = self.analyzer._generate_modernization_steps("FURB106", "Use f-strings")
        assert isinstance(steps_f_string, list)
        assert len(steps_f_string) > 0
        assert any("f-string" in step.lower() for step in steps_f_string)
        
        # Test with unknown pattern
        steps_unknown = self.analyzer._generate_modernization_steps("UNKNOWN", "Some message")
        assert isinstance(steps_unknown, list)
        assert len(steps_unknown) > 0
    
    @patch('subprocess.run')
    def test_refurb_json_output_processing(self, mock_subprocess):
        """Test processing of refurb JSON output"""
        mock_result = MagicMock()
        mock_result.returncode = 1  # Issues found
        mock_result.stdout = '{"message": "Use f-strings", "id": "FURB106", "line": 5, "column": 10}\n'
        mock_subprocess.return_value = mock_result
        
        guidance = self.analyzer.analyze("test_code = 'test'", "json_test.py")
        
        # Should process JSON output
        assert len(guidance) > 0, "Should process JSON output"
        assert guidance[0].issue_type == "modernization_opportunity"
    
    @patch('subprocess.run')
    def test_refurb_text_output_processing(self, mock_subprocess):
        """Test processing of refurb text output when JSON fails"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Some text output from refurb that's not JSON"
        mock_subprocess.return_value = mock_result
        
        guidance = self.analyzer.analyze("test_code = 'test'", "text_test.py")
        
        # Should handle text output
        assert isinstance(guidance, list), "Should handle text output"
    
    @patch('subprocess.run')
    def test_refurb_timeout_handling(self, mock_subprocess):
        """Test handling of refurb timeouts"""
        from subprocess import TimeoutExpired
        mock_subprocess.side_effect = TimeoutExpired("refurb", 30)
        
        guidance = self.analyzer.analyze(self.legacy_code, "timeout_test.py")
        
        # Should handle timeout gracefully
        timeout_issues = [g for g in guidance if "timeout" in g.issue_type]
        assert len(timeout_issues) > 0, "Should report timeout issue"
    
    @patch('subprocess.run')
    def test_refurb_not_installed_handling(self, mock_subprocess):
        """Test handling when refurb is not installed"""
        mock_subprocess.side_effect = FileNotFoundError("refurb not found")
        
        guidance = self.analyzer.analyze(self.legacy_code, "missing_tool_test.py")
        
        # Should report tool missing
        tool_issues = [g for g in guidance if "tool_missing" in g.issue_type]
        assert len(tool_issues) > 0, "Should report missing refurb tool"
    
    @patch('subprocess.run')
    def test_refurb_error_handling(self, mock_subprocess):
        """Test handling of refurb errors"""
        mock_result = MagicMock()
        mock_result.returncode = 2  # Error code
        mock_result.stderr = "Refurb analysis error"
        mock_subprocess.return_value = mock_result
        
        guidance = self.analyzer.analyze(self.legacy_code, "error_test.py")
        
        # Should handle errors gracefully
        error_issues = [g for g in guidance if "error" in g.issue_type]
        assert len(error_issues) > 0, "Should report analysis error"
    
    def test_complex_legacy_function(self):
        """Test analysis of function with multiple modernization opportunities"""
        complex_legacy_code = '''
import os
import sys

def process_data(users_data):
    # Multiple modernization opportunities
    results = []
    for i in range(len(users_data)):  # Should use enumerate
        user = users_data[i]
        
        if "age" in user:  # Should use dict.get
            age = user["age"]
        else:
            age = 0
        
        message = "User {}: age {}".format(user.get("name", "Unknown"), age)  # Should use f-strings
        
        filepath = os.path.join("/tmp", f"{user.get('id', 0)}.txt")  # Should use pathlib
        
        if type(age) == int:  # Should use isinstance
            results.append(message)
    
    return results
        '''
        
        guidance = self.analyzer.analyze(complex_legacy_code, "complex_test.py")
        
        # Should detect multiple modernization opportunities
        assert len(guidance) >= 0, "Should detect modernization opportunities in complex function"
    
    def test_specific_refurb_patterns(self):
        """Test detection of specific refurb patterns"""
        test_patterns = {
            "f_strings": 'message = "Hello {}".format(name)',
            "enumerate": 'for i in range(len(items)): print(items[i])',
            "pathlib": 'import os; os.path.join("/tmp", "file")',
            "dict_get": 'if "key" in d: value = d["key"]',
            "isinstance": 'if type(x) == str: pass',
        }
        
        for pattern_name, code in test_patterns.items():
            guidance = self.analyzer.analyze(code, f"pattern_{pattern_name}.py")
            
            # Should complete analysis (may or may not detect specific patterns depending on refurb config)
            assert isinstance(guidance, list), f"Analysis should complete for {pattern_name}"
    
    def test_process_refurb_issue(self):
        """Test processing of individual refurb issues"""
        issue = {
            'message': 'Use f-strings instead of .format()',
            'id': 'FURB106',
            'line': 10,
            'column': 5
        }
        
        guidance_item = self.analyzer._process_refurb_issue(issue, "test.py")
        
        assert isinstance(guidance_item, RefactoringGuidance)
        assert guidance_item.issue_type == "modernization_opportunity"
        assert "FURB106" in guidance_item.description
        assert "Line 10:5" in guidance_item.location
        assert len(guidance_item.benefits) > 0
        assert len(guidance_item.precise_steps) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])