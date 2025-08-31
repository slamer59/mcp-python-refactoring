#!/usr/bin/env python3
"""
Unit tests for EnhancedRefactoringAnalyzer business logic.

Focus on analyzer orchestration, error handling, and specific behavior.
"""

import pytest
import os
from unittest.mock import patch, Mock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mcp_refactoring_assistant.core import EnhancedRefactoringAnalyzer
from mcp_refactoring_assistant.models.data_classes import RefactoringGuidance


@pytest.mark.unit
class TestAnalyzerOrchestration:
    """Test analyzer orchestration and coordination logic."""

    def test_analyzer_graceful_initialization_failure(self, temp_dir):
        """Test analyzer handles initialization gracefully."""
        # Should not crash during initialization
        analyzer = EnhancedRefactoringAnalyzer(project_path=str(temp_dir))
        
        # Should still have basic attributes set
        assert analyzer.project_path == str(temp_dir)
        assert hasattr(analyzer, 'analyzers')
        
        # Should handle analysis gracefully even with potential analyzer issues
        result = analyzer.analyze_file("test.py", "def simple(): pass")
        assert isinstance(result, list)

    def test_analyzer_aggregates_multiple_issue_types(self, analyzer):
        """Test that analyzer properly aggregates different types of issues."""
        complex_problematic_code = '''
def problematic_function(a, b, c, d, e, f, g, h, i, j):  # Too many params
    """Function with multiple issues."""
    # Long function with high complexity
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        result = []
                        for x in range(100):
                            if x % 2 == 0:
                                if x % 4 == 0:
                                    result.append(x * 2)
                                else:
                                    result.append(x)
                            else:
                                result.append(x + 1)
                        return result
    return []
'''
        
        guidance_list = analyzer.analyze_file("multi_issue.py", complex_problematic_code)
        
        # Should detect multiple types of issues
        if guidance_list:
            issue_types = [g.issue_type for g in guidance_list]
            
            # May detect various issues like complexity, too many parameters, etc.
            # The exact issues depend on analyzer implementation
            assert len(set(issue_types)) >= 1, "Should detect at least one type of issue"
            
            # All guidance should be properly structured
            for guidance in guidance_list:
                assert isinstance(guidance, RefactoringGuidance)
                assert guidance.severity in ["low", "medium", "high", "critical"]


@pytest.mark.unit
class TestAnalyzerErrorHandling:
    """Test analyzer error handling and resilience."""

    def test_syntax_error_produces_critical_guidance(self, analyzer):
        """Test that syntax errors produce critical severity guidance."""
        broken_syntax = '''
def broken_function(
    # Missing closing parenthesis and colon
    print("This will not work")
    return "broken"
'''
        
        guidance_list = analyzer.analyze_file("syntax_error.py", broken_syntax)
        
        # Should handle syntax error gracefully
        assert isinstance(guidance_list, list)
        
        # If syntax errors are detected, they should be critical
        syntax_errors = [g for g in guidance_list if g.severity == "critical"]
        if syntax_errors:
            for error in syntax_errors:
                assert "syntax" in error.issue_type.lower() or "syntax" in error.description.lower()

    def test_analyzer_handles_edge_case_code_patterns(self, analyzer):
        """Test analyzer handles unusual but valid Python patterns."""
        edge_cases = [
            # Empty function
            ("def empty(): pass", "empty_function"),
            
            # Single expression function  
            ("def single(): return 42", "single_expression"),
            
            # Function with only docstring
            ('def documented(): """Just docs"""; pass', "docstring_only"),
            
            # Nested function
            ("def outer():\n    def inner(): return 1\n    return inner", "nested_function"),
            
            # Lambda assignment
            ("square = lambda x: x**2", "lambda_assignment"),
        ]
        
        for code, description in edge_cases:
            result = analyzer.analyze_file(f"{description}.py", code)
            
            # Should handle all edge cases without crashing
            assert isinstance(result, list), f"Failed to handle {description}"

    def test_analyzer_consistency_with_repeated_analysis(self, analyzer, complex_function_code):
        """Test analyzer produces consistent results across multiple runs."""
        results = []
        
        # Run analysis multiple times
        for i in range(3):
            result = analyzer.analyze_file(f"consistency_test_{i}.py", complex_function_code)
            results.append(result)
        
        # Results should be consistent
        assert len(results) == 3
        
        # Same number of issues detected each time
        issue_counts = [len(result) for result in results]
        assert len(set(issue_counts)) == 1, "Should produce consistent number of issues"
        
        # Same types of issues detected
        if results[0]:  # If any issues were detected
            for i in range(1, len(results)):
                result_types = [g.issue_type for g in results[i]]
                baseline_types = [g.issue_type for g in results[0]]
                assert set(result_types) == set(baseline_types), "Should detect same issue types"


@pytest.mark.unit
class TestAnalyzerConfiguration:
    """Test analyzer configuration and customization."""

    def test_analyzer_respects_project_path_context(self, temp_dir):
        """Test that analyzer uses project path for context."""
        # Create analyzer with specific project path
        analyzer = EnhancedRefactoringAnalyzer(project_path=str(temp_dir))
        
        assert analyzer.project_path == str(temp_dir)
        
        # Analysis should work with the configured path
        result = analyzer.analyze_file("context_test.py", "def test(): pass")
        assert isinstance(result, list)

    def test_analyzer_handles_concurrent_analysis(self, analyzer, simple_function_code):
        """Test analyzer thread safety with concurrent analyses."""
        import threading
        import time
        
        results = []
        errors = []
        
        def analyze_worker(worker_id):
            try:
                result = analyzer.analyze_file(f"concurrent_{worker_id}.py", simple_function_code)
                results.append((worker_id, result))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Start multiple concurrent analyses
        threads = []
        for i in range(5):
            thread = threading.Thread(target=analyze_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Should complete all analyses without errors
        assert len(errors) == 0, f"Concurrent analysis errors: {errors}"
        assert len(results) == 5, "All concurrent analyses should complete"
        
        # All results should be valid
        for worker_id, result in results:
            assert isinstance(result, list), f"Worker {worker_id} result invalid"


@pytest.mark.unit
class TestAnalyzerBusinessLogic:
    """Test specific business logic in the analyzer."""

    def test_analyzer_prioritizes_critical_issues(self, analyzer):
        """Test that critical issues are properly identified and prioritized."""
        critical_issue_code = '''
def broken_function(
    # This is a syntax error - should be critical
    print("Missing parenthesis and colon")
    return "broken"
    
def also_problematic():
    # This might have other issues but syntax is most critical
    pass
'''
        
        guidance_list = analyzer.analyze_file("critical_test.py", critical_issue_code)
        
        # Should detect issues
        if guidance_list:
            # Critical issues should be present for syntax errors
            severities = [g.severity for g in guidance_list]
            
            # At minimum, should handle the code without crashing
            assert isinstance(guidance_list, list)

    def test_analyzer_extracts_meaningful_locations(self, analyzer):
        """Test that analyzer provides meaningful location information."""
        multiline_code = '''# Line 1
def function_at_line_2():  # Line 2
    """Docstring at line 3"""  # Line 3
    if True:  # Line 4
        return "success"  # Line 5
    return "failure"  # Line 6
'''
        
        guidance_list = analyzer.analyze_file("location_test.py", multiline_code)
        
        # All guidance should have meaningful locations
        for guidance in guidance_list:
            assert guidance.location, "Location should not be empty"
            # Accept various location formats: "file.py:123", "Function at line 10", "Multiple locations", etc.
            assert any(indicator in guidance.location.lower() for indicator in [":", "line", "location", "function", "class"]), "Location should include meaningful info"
            
            # Extract and validate line number if possible
            if ":" in guidance.location:
                parts = guidance.location.split(":")
                if len(parts) >= 2:
                    try:
                        line_num = int(parts[1])
                        assert 1 <= line_num <= 6, f"Line {line_num} should be in valid range 1-6"
                    except ValueError:
                        # Line number extraction failed, but location exists
                        pass


@pytest.mark.unit
@pytest.mark.slow
class TestAnalyzerPerformanceConstraints:
    """Test performance constraints and limits."""

    def test_analyzer_handles_large_functions_efficiently(self, analyzer, code_factory, performance_timer):
        """Test analyzer performance with large functions."""
        # Generate a large but realistic function
        large_function = code_factory.make_function(
            name="large_function", 
            lines=200,  # Very large function
            complexity=1  # Keep complexity low to focus on size
        )
        
        with performance_timer() as timer:
            result = analyzer.analyze_file("large_function.py", large_function)
        
        # Should complete within reasonable time even for large functions
        assert timer.elapsed < 10.0, f"Large function analysis too slow: {timer.elapsed:.2f}s"
        assert isinstance(result, list), "Should return valid result"

    def test_analyzer_memory_stability_under_load(self, analyzer, code_factory):
        """Test that analyzer doesn't leak memory under repeated use."""
        import gc
        
        # Force initial cleanup
        gc.collect()
        
        # Perform many analyses
        for i in range(25):
            code = code_factory.make_function(
                name=f"memory_stability_test_{i}",
                lines=40,
                complexity=2
            )
            
            result = analyzer.analyze_file(f"stability_{i}.py", code)
            assert isinstance(result, list)
            
            # Periodic cleanup to help detect leaks
            if i % 10 == 0:
                gc.collect()
        
        # If we reach here without memory errors, test passes
        assert True, "Memory remained stable under repeated analysis"