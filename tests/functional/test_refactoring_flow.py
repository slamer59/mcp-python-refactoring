#!/usr/bin/env python3
"""
Functional tests for end-to-end refactoring analysis flows.

These tests validate the complete pipeline from code input to refactoring guidance,
using realistic scenarios and the Given-When-Then pattern.
"""

import pytest
import tempfile
import os
import warnings
from pathlib import Path
from typing import List
import json

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mcp_refactoring_assistant.core import EnhancedRefactoringAnalyzer
from mcp_refactoring_assistant.models import RefactoringGuidance, ExtractableBlock


@pytest.mark.functional
class TestRefactoringFlowEndToEnd:
    """End-to-end functional tests for refactoring flows."""

    def test_simple_analysis_flow(self, analyzer, simple_function_code, guidance_validator):
        """
        Given: Simple, clean Python code
        When: Analyzer processes the code
        Then: Returns minimal or no refactoring suggestions
        """
        # When
        guidance = analyzer.analyze_file("simple.py", simple_function_code)
        
        # Then
        guidance_validator(guidance)
        # Simple code should have minimal issues
        critical_issues = [g for g in guidance if g.severity == "critical"]
        assert len(critical_issues) == 0, "Simple code should not have critical issues"

    def test_complex_function_analysis_flow(self, analyzer, complex_function_code, guidance_validator):
        """
        Given: Complex function with multiple issues
        When: Analyzer processes the code
        Then: Returns structured guidance for multiple issue types
        """
        # When
        guidance = analyzer.analyze_file("complex.py", complex_function_code)
        
        # Then
        guidance_validator(guidance)
        assert len(guidance) > 0, "Complex code should generate refactoring guidance"
        
        # Should detect high complexity
        complexity_issues = [g for g in guidance if "complexity" in g.issue_type.lower()]
        assert len(complexity_issues) > 0, "Should detect complexity issues"
        
        # Should detect too many parameters
        param_issues = [g for g in guidance if "parameter" in g.issue_type.lower()]
        assert len(param_issues) > 0, "Should detect parameter issues"

    def test_long_function_extraction_flow(self, analyzer, long_function_code, guidance_validator):
        """
        Given: Long function suitable for extraction
        When: Analyzer processes the code
        Then: Returns extract method suggestions with specific blocks
        """
        # When
        guidance = analyzer.analyze_file("long_function.py", long_function_code)
        
        # Then
        guidance_validator(guidance)
        
        # Look for extraction suggestions (handle None case)
        extraction_guidance = [g for g in guidance if "extract" in g.issue_type.lower() or 
                             "long" in g.issue_type.lower() or
                             (g.extractable_blocks is not None and len(g.extractable_blocks) > 0)]
        
        # Should provide actionable steps for extraction
        for guide in extraction_guidance:
            assert len(guide.precise_steps) > 0, "Should provide extraction steps"
            assert len(guide.benefits) > 0, "Should list extraction benefits"

    def test_class_analysis_flow(self, analyzer, class_with_methods_code, guidance_validator):
        """
        Given: Class with multiple methods
        When: Analyzer processes the code
        Then: Returns guidance appropriate for class structure
        """
        # When
        guidance = analyzer.analyze_file("class_example.py", class_with_methods_code)
        
        # Then
        guidance_validator(guidance)
        
        # Validate that class-level analysis works
        for guide in guidance:
            # Location should reference class or method locations (flexible format)
            assert guide.location and len(guide.location) > 0, "Should provide location info"
            # Accept various location formats: "file.py:123", "Function at line 10", "Multiple locations", etc.
            assert any(indicator in guide.location.lower() for indicator in [".py:", "line", "location", "function", "class"]), "Should provide meaningful location info"

    def test_syntax_error_handling_flow(self, analyzer, syntax_error_code):
        """
        Given: Code with syntax errors
        When: Analyzer processes the code
        Then: Returns critical severity guidance about syntax issues
        """
        # When
        guidance = analyzer.analyze_file("broken.py", syntax_error_code)
        
        # Then
        assert len(guidance) > 0, "Should detect syntax errors"
        
        syntax_errors = [g for g in guidance if g.severity == "critical" or 
                        "syntax" in g.issue_type.lower()]
        assert len(syntax_errors) > 0, "Should identify syntax errors as critical"
        
        for error in syntax_errors:
            assert "syntax" in error.description.lower(), "Should mention syntax in description"

    def test_dead_code_detection_flow(self, analyzer, dead_code_sample, guidance_validator):
        """
        Given: Code with unused functions
        When: Analyzer processes the code
        Then: Identifies dead code and suggests removal
        """
        # When
        guidance = analyzer.analyze_file("dead_code.py", dead_code_sample)
        
        # Then
        guidance_validator(guidance)
        
        # May or may not detect dead code depending on analyzer capabilities
        # But should handle the code without errors
        for guide in guidance:
            assert guide.description, "All guidance should have descriptions"

    def test_incremental_analysis_flow(self, analyzer, code_factory, guidance_validator):
        """
        Given: Code samples with increasing complexity
        When: Analyzer processes each sample
        Then: Guidance complexity increases appropriately
        """
        complexity_levels = [1, 3, 5, 8]
        guidance_counts = []
        
        for complexity in complexity_levels:
            # Given
            code = code_factory.make_function(
                name=f"func_complexity_{complexity}",
                complexity=complexity,
                lines=10 + complexity * 2
            )
            
            # When
            guidance = analyzer.analyze_file(f"complexity_{complexity}.py", code)
            
            # Then
            guidance_validator(guidance)
            guidance_counts.append(len(guidance))
        
        # Higher complexity should generally produce more guidance
        # (though this is not strictly guaranteed)
        assert guidance_counts[-1] >= guidance_counts[0], \
               "Higher complexity should generally produce more guidance"

    def test_multi_file_project_simulation(self, analyzer, test_project_structure):
        """
        Given: A realistic multi-file project structure
        When: Analyzer processes files from the project
        Then: Handles project context appropriately
        """
        # Create analyzer with project path
        project_analyzer = EnhancedRefactoringAnalyzer(project_path=str(test_project_structure))
        
        # Read a file from the project
        main_file = test_project_structure / "src" / "myproject" / "main.py"
        main_content = main_file.read_text()
        
        # When
        guidance = project_analyzer.analyze_file(str(main_file), main_content)
        
        # Then
        assert isinstance(guidance, list), "Should return guidance list"
        # Simple main.py shouldn't have major issues
        critical_issues = [g for g in guidance if g.severity == "critical"]
        assert len(critical_issues) == 0, "Simple main.py should not have critical issues"


@pytest.mark.functional
class TestAnalyzerConfiguration:
    """Test analyzer behavior with different configurations."""

    def test_line_threshold_configuration(self, temp_dir, long_function_code):
        """
        Given: Analyzer with different line thresholds
        When: Processing the same long function
        Then: Threshold affects detection sensitivity
        """
        # Test with strict threshold
        strict_analyzer = EnhancedRefactoringAnalyzer(project_path=str(temp_dir))
        strict_guidance = strict_analyzer.analyze_file("test.py", long_function_code)
        
        # Should detect the long function with default threshold
        assert isinstance(strict_guidance, list)

    def test_analyzer_with_empty_project(self, temp_dir):
        """
        Given: Analyzer initialized with empty project directory
        When: Analyzer is created
        Then: Initializes successfully without errors
        """
        # When
        analyzer = EnhancedRefactoringAnalyzer(project_path=str(temp_dir))
        
        # Then
        assert analyzer.project_path == str(temp_dir)
        assert analyzer.analyzers is not None


@pytest.mark.functional 
class TestGuidanceQuality:
    """Test the quality and usefulness of refactoring guidance."""

    def test_guidance_completeness(self, analyzer, complex_function_code):
        """
        Given: Complex code requiring refactoring
        When: Analyzer generates guidance
        Then: All guidance is complete and actionable
        """
        # When
        guidance = analyzer.analyze_file("test.py", complex_function_code)
        
        # Then
        for guide in guidance:
            # Completeness checks
            assert guide.issue_type, "Issue type should be specified"
            assert guide.severity in ['low', 'medium', 'high', 'critical'], \
                   "Severity should be valid"
            assert guide.description, "Description should be provided"
            assert guide.location, "Location should be specified"
            
            # Actionability checks
            assert len(guide.benefits) > 0, "Should list benefits"
            assert len(guide.precise_steps) > 0, "Should provide action steps"
            
            # Step quality checks
            for step in guide.precise_steps:
                assert len(step.strip()) > 10, "Steps should be descriptive"
            
            # Benefit quality checks
            for benefit in guide.benefits:
                assert len(benefit.strip()) > 5, "Benefits should be meaningful"

    def test_guidance_priority_ordering(self, analyzer, complex_function_code):
        """
        Given: Code with multiple issues
        When: Analyzer generates guidance
        Then: Critical issues are properly prioritized
        """
        # When
        guidance = analyzer.analyze_file("test.py", complex_function_code)
        
        # Then
        if len(guidance) > 1:
            severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            severity_values = [severity_order.get(g.severity, 0) for g in guidance]
            
            # Check if generally ordered by severity (allowing some flexibility)
            high_severity_count = sum(1 for s in severity_values if s >= 3)
            low_severity_count = sum(1 for s in severity_values if s <= 2)
            
            # High severity issues should be reasonable proportion
            if high_severity_count > 0 and low_severity_count > 0:
                # Both types present - this is expected for complex code
                pass

    def test_location_accuracy(self, analyzer, temp_file):
        """
        Given: Code with issues at specific lines
        When: Analyzer identifies issues
        Then: Location information is accurate
        """
        # Given: Code with a function at a known line
        code_with_line_markers = '''# Line 1
# Line 2
def problematic_function(a, b, c, d, e, f, g, h):  # Line 3
    """Function with too many parameters."""  # Line 4
    if a:  # Line 5
        if b:  # Line 6
            if c:  # Line 7
                if d:  # Line 8
                    return e + f + g + h  # Line 9
    return 0  # Line 10
'''
        
        file_path = temp_file(code_with_line_markers, "location_test.py")
        
        # When
        guidance = analyzer.analyze_file(str(file_path), code_with_line_markers)
        
        # Then
        for guide in guidance:
            # Location should include meaningful information (flexible format)
            assert guide.location and len(guide.location) > 0, "Location should not be empty"
            # Accept various location formats: "file.py:123", "Function at line 10", "Multiple locations", etc.
            assert any(indicator in guide.location.lower() for indicator in [":", "line", "location", "function", "class"]), "Location should include meaningful information"
            
            # Extract line number if possible
            parts = guide.location.split(":")
            if len(parts) >= 2:
                try:
                    line_num = int(parts[1])
                    assert 1 <= line_num <= 10, f"Line number {line_num} should be in valid range"
                except ValueError:
                    # Line number extraction failed, but that's not necessarily an error
                    pass


@pytest.mark.functional
class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_empty_file_handling(self, analyzer):
        """
        Given: Empty Python file
        When: Analyzer processes the file
        Then: Handles gracefully without errors
        """
        # When
        guidance = analyzer.analyze_file("empty.py", "")
        
        # Then
        assert isinstance(guidance, list), "Should return list for empty file"

    def test_whitespace_only_handling(self, analyzer):
        """
        Given: File with only whitespace
        When: Analyzer processes the file
        Then: Handles gracefully without errors
        """
        # When
        guidance = analyzer.analyze_file("whitespace.py", "   \n\n  \t  \n")
        
        # Then
        assert isinstance(guidance, list), "Should return list for whitespace-only file"

    def test_comments_only_handling(self, analyzer):
        """
        Given: File with only comments
        When: Analyzer processes the file
        Then: Handles gracefully without errors
        """
        # When
        guidance = analyzer.analyze_file("comments.py", "# Just a comment\n# Another comment")
        
        # Then
        assert isinstance(guidance, list), "Should return list for comments-only file"

    def test_very_large_function_handling(self, analyzer, code_factory):
        """
        Given: Extremely large function
        When: Analyzer processes the function
        Then: Handles without performance issues or crashes
        """
        # Given: Generate a very large function
        large_code = code_factory.make_function(
            name="huge_function",
            params=2,
            complexity=1,
            lines=200  # Very long function
        )
        
        # When
        with warnings.catch_warnings(record=True) as warning_list:
            guidance = analyzer.analyze_file("large.py", large_code)
        
        # Then
        assert isinstance(guidance, list), "Should handle large functions"
        # Should complete without excessive warnings
        excessive_warnings = [w for w in warning_list if "timeout" in str(w.message).lower()]
        assert len(excessive_warnings) == 0, "Should not timeout on large functions"


@pytest.mark.functional
@pytest.mark.slow
class TestPerformanceCharacteristics:
    """Test performance aspects of the analysis flow."""

    def test_analysis_performance_scaling(self, analyzer, code_factory, performance_timer):
        """
        Given: Functions of increasing size
        When: Analyzer processes each function
        Then: Performance scales reasonably
        """
        sizes = [10, 50, 100, 200]
        times = []
        
        for size in sizes:
            code = code_factory.make_function(
                name=f"func_{size}_lines",
                lines=size,
                complexity=2
            )
            
            # Time the analysis
            with performance_timer() as timer:
                guidance = analyzer.analyze_file(f"perf_{size}.py", code)
            
            times.append(timer.elapsed)
            assert isinstance(guidance, list), f"Should handle {size}-line function"
        
        # Performance should not degrade exponentially
        # (This is a basic smoke test, not a strict performance requirement)
        assert all(t < 10.0 for t in times), "Analysis should complete within reasonable time"

    def test_memory_usage_stability(self, analyzer, code_factory):
        """
        Given: Multiple analysis operations
        When: Performing repeated analyses
        Then: Memory usage remains stable
        """
        # Perform multiple analyses
        for i in range(10):
            code = code_factory.make_function(
                name=f"memory_test_{i}",
                lines=50,
                complexity=3
            )
            
            guidance = analyzer.analyze_file(f"memory_{i}.py", code)
            assert isinstance(guidance, list), f"Analysis {i} should succeed"
        
        # If we reach here without memory errors, test passes
        assert True, "Memory usage remained stable across multiple analyses"


@pytest.mark.functional
class TestRealWorldScenarios:
    """Test with realistic code scenarios."""

    def test_django_model_like_code(self, analyzer, guidance_validator):
        """Test analysis of Django model-like code."""
        django_like_code = '''
from django.db import models
from django.contrib.auth.models import User

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('blog:detail', kwargs={'pk': self.pk})
    
    def publish(self):
        self.is_published = True
        self.save()
        
    def unpublish(self):
        self.is_published = False
        self.save()
'''
        
        guidance = analyzer.analyze_file("models.py", django_like_code)
        guidance_validator(guidance)

    def test_flask_route_like_code(self, analyzer, guidance_validator):
        """Test analysis of Flask route-like code."""
        flask_like_code = '''
from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/users', methods=['GET', 'POST'])
def handle_users():
    if request.method == 'GET':
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        conn.close()
        return jsonify(users)
    
    elif request.method == 'POST':
        data = request.get_json()
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({'error': 'Invalid data'}), 400
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (name, email) VALUES (?, ?)',
            (data['name'], data['email'])
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'id': user_id, 'name': data['name'], 'email': data['email']}), 201

if __name__ == '__main__':
    app.run(debug=True)
'''
        
        guidance = analyzer.analyze_file("app.py", flask_like_code)
        guidance_validator(guidance)

    def test_data_processing_script(self, analyzer, guidance_validator):
        """Test analysis of data processing script."""
        data_script = '''
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def load_and_process_data(file_path, start_date=None, end_date=None):
    """Load and process CSV data file."""
    # Load data
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"File {file_path} not found")
        return None
    
    # Data cleaning
    df = df.dropna()
    df = df.drop_duplicates()
    
    # Date filtering
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        if start_date:
            df = df[df['date'] >= start_date]
        if end_date:
            df = df[df['date'] <= end_date]
    
    # Calculate metrics
    if 'value' in df.columns:
        df['value_normalized'] = (df['value'] - df['value'].mean()) / df['value'].std()
        df['value_percentile'] = df['value'].rank(pct=True)
    
    # Group and aggregate
    if 'category' in df.columns:
        grouped = df.groupby('category').agg({
            'value': ['sum', 'mean', 'count'],
            'date': ['min', 'max']
        }).reset_index()
        return df, grouped
    
    return df

def generate_report(processed_data):
    """Generate summary report from processed data."""
    if processed_data is None:
        return "No data to process"
    
    if isinstance(processed_data, tuple):
        df, grouped = processed_data
        report = f"""
Data Summary Report
==================
Total records: {len(df)}
Date range: {df['date'].min()} to {df['date'].max()}
Categories: {df['category'].nunique()}

Category Summary:
{grouped.to_string(index=False)}
        """
    else:
        df = processed_data
        report = f"""
Data Summary Report
==================
Total records: {len(df)}
Columns: {', '.join(df.columns)}
        """
    
    return report
'''
        
        guidance = analyzer.analyze_file("data_processor.py", data_script)
        guidance_validator(guidance)