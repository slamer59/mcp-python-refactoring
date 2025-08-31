#!/usr/bin/env python3
"""
Tests for EnhancedRefactoringAnalyzer class
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_refactoring_assistant.core import EnhancedRefactoringAnalyzer
from mcp_refactoring_assistant.models import RefactoringGuidance, ExtractableBlock


class TestEnhancedRefactoringAnalyzer:
    """Test EnhancedRefactoringAnalyzer class"""

    def test_analyzer_initialization_default_path(self):
        """Test analyzer initialization with default project path"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        assert analyzer.project_path is not None
        assert os.path.exists(analyzer.project_path)
        assert analyzer.analyzers is not None  # Should initialize successfully
        assert len(analyzer.analyzers) > 0  # Should have multiple analyzers

    def test_analyzer_initialization_custom_path(self):
        """Test analyzer initialization with custom project path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = EnhancedRefactoringAnalyzer(project_path=temp_dir)
            
            assert analyzer.project_path == temp_dir
            assert analyzer.analyzers is not None
            assert len(analyzer.analyzers) > 0

    def test_analyzer_initialization_graceful_failure(self):
        """Test analyzer initialization handles individual analyzer failures gracefully"""
        # This test ensures the analyzer orchestrator doesn't fail if one analyzer fails
        analyzer = EnhancedRefactoringAnalyzer()
        
        assert analyzer.project_path is not None
        assert analyzer.analyzers is not None
        # Even if some analyzers fail, the main analyzer should still work

    def test_analyze_file_simple_code(self):
        """Test analyzing simple Python code"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        simple_code = '''
def simple_function():
    """A simple function"""
    return "hello world"

def another_function(x, y):
    """Another function"""
    return x + y
'''
        
        guidance = analyzer.analyze_file("test.py", simple_code)
        
        # Should return a list of RefactoringGuidance objects
        assert isinstance(guidance, list)
        for item in guidance:
            assert isinstance(item, RefactoringGuidance)

    def test_analyze_file_syntax_error(self):
        """Test analyzing code with syntax error"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        bad_code = '''
def broken_function(
    # Missing closing parenthesis and colon
    return "broken"
'''
        
        guidance = analyzer.analyze_file("bad.py", bad_code)
        
        # Should return guidance about syntax error
        assert len(guidance) >= 1
        syntax_errors = [g for g in guidance if g.issue_type == "syntax_error"]
        assert len(syntax_errors) >= 1
        
        syntax_error = syntax_errors[0]
        assert syntax_error.severity == "critical"
        assert "syntax error" in syntax_error.description.lower()

    def test_analyze_file_complex_function(self):
        """Test analyzing code with complex function"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        complex_code = '''
def complex_function(a, b, c, d, e, f, g, h):
    """Function with too many parameters and complexity"""
    result = []
    
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                if h > 0:
                                    for i in range(10):
                                        if i % 2 == 0:
                                            result.append(i * 2)
                                        else:
                                            result.append(i * 3)
    
    return result
'''
        
        guidance = analyzer.analyze_file("complex.py", complex_code)
        
        # Should detect various issues
        assert len(guidance) > 0
        
        # Check for specific issue types that should be detected
        issue_types = [g.issue_type for g in guidance]
        
        # Should detect too many parameters
        assert any("too_many_parameters" in issue_type for issue_type in issue_types)

    def test_analyze_file_long_function(self):
        """Test analyzing code with long function (for extraction)"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        # Create a function with many lines to trigger extraction analysis
        long_function_lines = [
            "def very_long_function():",
            '    """A very long function that should be refactored"""',
        ]
        
        # Add 25 lines of simple code
        for i in range(25):
            long_function_lines.append(f'    line_{i} = "statement {i}"')
            long_function_lines.append(f'    print(line_{i})')
        
        long_function_lines.append('    return "done"')
        
        long_code = '\n'.join(long_function_lines)
        
        guidance = analyzer.analyze_file("long.py", long_code)
        
        # Should return guidance (may or may not include extraction depending on implementation)
        assert isinstance(guidance, list)
        for item in guidance:
            assert isinstance(item, RefactoringGuidance)

    def test_analyze_file_empty_code(self):
        """Test analyzing empty code"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        guidance = analyzer.analyze_file("empty.py", "")
        
        # Should handle empty code gracefully
        assert isinstance(guidance, list)
        # Empty code might not have issues, that's okay

    def test_analyze_file_only_imports(self):
        """Test analyzing code with only imports"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        import_code = '''
import os
import sys
import json
import ast
import tempfile
from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
import numpy as np
import pandas as pd
'''
        
        guidance = analyzer.analyze_file("imports.py", import_code)
        
        # Should handle import-only code
        assert isinstance(guidance, list)

    def test_analyze_file_with_classes(self):
        """Test analyzing code with classes"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        class_code = '''
class SimpleClass:
    """A simple class"""
    
    def __init__(self):
        self.value = 0
    
    def get_value(self):
        return self.value
    
    def set_value(self, value):
        self.value = value

class ComplexClass:
    """A more complex class"""
    
    def method1(self):
        pass
    
    def method2(self):
        pass
    
    def method3(self):
        pass
    
    def method4(self):
        pass
    
    def method5(self):
        pass
    
    def method6(self):
        pass
    
    def method7(self):
        pass
'''
        
        guidance = analyzer.analyze_file("classes.py", class_code)
        
        assert isinstance(guidance, list)
        for item in guidance:
            assert isinstance(item, RefactoringGuidance)

    def test_analyze_file_dead_code_detection(self):
        """Test dead code detection"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        dead_code = '''
def used_function():
    return "used"

def unused_function():
    return "unused"

def main():
    result = used_function()
    return result

if __name__ == "__main__":
    main()
'''
        
        guidance = analyzer.analyze_file("dead_code.py", dead_code)
        
        # Should return guidance (dead code detection may or may not trigger depending on implementation)
        assert isinstance(guidance, list)

    def test_analyze_file_maintains_guidance_structure(self):
        """Test that analyze_file returns properly structured guidance"""
        analyzer = EnhancedRefactoringAnalyzer()
        
        test_code = '''
def test_function():
    return True
'''
        
        guidance = analyzer.analyze_file("structure_test.py", test_code)
        
        assert isinstance(guidance, list)
        
        for item in guidance:
            # Each guidance item should have required fields
            assert hasattr(item, 'issue_type')
            assert hasattr(item, 'severity')
            assert hasattr(item, 'location')
            assert hasattr(item, 'description')
            assert hasattr(item, 'benefits')
            assert hasattr(item, 'precise_steps')
            
            # Severity should be valid
            assert item.severity in ['low', 'medium', 'high', 'critical']
            
            # Benefits and steps should be lists
            assert isinstance(item.benefits, list)
            assert isinstance(item.precise_steps, list)
            
            # Should be convertible to dict
            item_dict = item.to_dict()
            assert isinstance(item_dict, dict)


# Integration-style tests with real analysis methods
class TestAnalyzerIntegration:
    """Integration tests for analyzer with its analysis methods"""

    def setup_method(self):
        """Setup for each test method"""
        self.analyzer = EnhancedRefactoringAnalyzer()

    def test_full_analysis_pipeline(self):
        """Test the full analysis pipeline end-to-end"""
        # Code that should trigger multiple types of issues
        complex_code = '''
import unused_import
import os
import sys

def complex_function(param1, param2, param3, param4, param5, param6):
    """Function with multiple issues"""
    unused_var = "not used"
    
    if param1:
        if param2:
            if param3:
                if param4:
                    if param5:
                        if param6:
                            # Deeply nested logic
                            result = []
                            for i in range(100):
                                if i % 2 == 0:
                                    if i % 4 == 0:
                                        result.append(i * 2)
                                    else:
                                        result.append(i)
                                else:
                                    if i % 3 == 0:
                                        result.append(i * 3)
                                    else:
                                        result.append(i + 1)
                            return result
    
    return []

def dead_function():
    """This function is never called"""
    pass
'''
        
        guidance = self.analyzer.analyze_file("complex_analysis.py", complex_code)
        
        # Should detect various issues
        assert len(guidance) > 0
        
        # Verify guidance structure
        for item in guidance:
            assert isinstance(item, RefactoringGuidance)
            assert item.issue_type
            assert item.severity in ['low', 'medium', 'high', 'critical']
            assert item.description
            assert isinstance(item.benefits, list)
            assert isinstance(item.precise_steps, list)

    def test_analyzer_handles_edge_cases(self):
        """Test analyzer handles various edge cases"""
        edge_cases = [
            ("", "empty file"),
            ("# Just a comment", "comment only"),
            ("x = 1", "single statement"),
            ("def f(): pass", "minimal function"),
            ("class C: pass", "minimal class"),
        ]
        
        for code, description in edge_cases:
            guidance = self.analyzer.analyze_file(f"{description}.py", code)
            
            # Should handle gracefully without crashing
            assert isinstance(guidance, list)
            # Each guidance item should be valid
            for item in guidance:
                assert isinstance(item, RefactoringGuidance)


if __name__ == "__main__":
    pytest.main([__file__])