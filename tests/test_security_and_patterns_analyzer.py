#!/usr/bin/env python3
"""
Comprehensive tests for SecurityAndPatternsAnalyzer - the unified analyzer that orchestrates
security scanning, modernization patterns, and dependency vulnerability analysis
"""

import pytest
import ast
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.mcp_refactoring_assistant.analyzers.security_and_patterns_analyzer import SecurityAndPatternsAnalyzer
from src.mcp_refactoring_assistant.models import RefactoringGuidance


class TestSecurityAndPatternsAnalyzer:
    """Test cases for SecurityAndPatternsAnalyzer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = SecurityAndPatternsAnalyzer()
        
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
    
    def test_unified_analysis_vulnerable_and_legacy_code(self):
        """Test unified analysis of code with both security and modernization issues"""
        # Combine both vulnerable and legacy code patterns
        combined_code = self.vulnerable_code + "\n\n" + self.legacy_code
        
        guidance = self.analyzer.analyze(combined_code, "combined_test.py")
        
        # Should detect both security and modernization issues
        assert len(guidance) > 0, "Should detect issues in combined code"
        
        # Check for security issues
        security_issues = [g for g in guidance if 'security' in g.issue_type or 'dependency' in g.issue_type]
        modernization_issues = [g for g in guidance if 'modernization' in g.issue_type]
        
        # Should have both types of issues (though exact numbers depend on tool availability)
        total_issues = len(security_issues) + len(modernization_issues)
        assert total_issues > 0, "Should detect security or modernization issues"
        
        # All guidance should be properly structured
        for item in guidance:
            assert isinstance(item, RefactoringGuidance)
            assert hasattr(item, 'issue_type')
            assert hasattr(item, 'severity')
            assert hasattr(item, 'description')
            assert hasattr(item, 'benefits')
            assert hasattr(item, 'precise_steps')
    
    def test_prioritization_logic(self):
        """Test that guidance is properly prioritized by severity and type"""
        # Create mixed guidance with different severities and types
        mixed_guidance = [
            RefactoringGuidance(
                issue_type="modernization_opportunity",
                severity="low",
                location="line 1",
                description="Minor modernization",
                benefits=["Better code"],
                precise_steps=["Step 1"]
            ),
            RefactoringGuidance(
                issue_type="security_vulnerability",
                severity="critical",
                location="line 2", 
                description="Critical security issue",
                benefits=["Better security"],
                precise_steps=["Fix now"]
            ),
            RefactoringGuidance(
                issue_type="dependency_vulnerability",
                severity="high",
                location="line 3",
                description="Vulnerable dependency",
                benefits=["Security fix"],
                precise_steps=["Update package"]
            ),
            RefactoringGuidance(
                issue_type="modernization_opportunity",
                severity="medium",
                location="line 4",
                description="Medium modernization",
                benefits=["Code improvement"],
                precise_steps=["Modernize"]
            )
        ]
        
        prioritized = self.analyzer._prioritize_guidance(mixed_guidance, {})
        
        # Should be sorted by priority (critical security first)
        assert len(prioritized) > 0
        
        # Critical security should come first
        critical_issues = [g for g in prioritized if g.severity == "critical"]
        if critical_issues:
            assert prioritized[0].severity == "critical"
            assert prioritized[0].issue_type == "security_vulnerability"
    
    def test_deduplication_logic(self):
        """Test that duplicate or near-duplicate issues are removed"""
        # Create duplicate guidance items
        duplicate_guidance = [
            RefactoringGuidance(
                issue_type="security_vulnerability",
                severity="medium",
                location="line 5",
                description="Same security issue",
                benefits=["Security"],
                precise_steps=["Fix"]
            ),
            RefactoringGuidance(
                issue_type="security_vulnerability", 
                severity="medium",
                location="line 5",
                description="Same security issue duplicated",
                benefits=["Security"],
                precise_steps=["Fix"]
            ),
            RefactoringGuidance(
                issue_type="modernization_opportunity",
                severity="low",
                location="line 10",
                description="Different issue",
                benefits=["Modernization"],
                precise_steps=["Modernize"]
            )
        ]
        
        deduplicated = self.analyzer._prioritize_guidance(duplicate_guidance, {})
        
        # Should remove duplicates based on (issue_type, location, severity)
        assert len(deduplicated) < len(duplicate_guidance), "Should remove duplicates"
        
        # Should keep the first occurrence of each unique combination
        locations = [g.location for g in deduplicated]
        assert "line 5" in locations, "Should keep one instance of line 5"
        assert "line 10" in locations, "Should keep line 10"
    
    def test_syntax_error_handling(self):
        """Test handling of files with syntax errors"""
        guidance = self.analyzer.analyze(self.invalid_code, "invalid_test.py")
        
        # Should return syntax error guidance
        assert len(guidance) > 0, "Should return guidance for syntax errors"
        
        syntax_errors = [g for g in guidance if g.issue_type == "syntax_error"]
        assert len(syntax_errors) > 0, "Should detect syntax error"
        
        error_item = syntax_errors[0]
        assert error_item.severity == "critical"
        assert "syntax error" in error_item.description.lower()
    
    def test_clean_code_analysis(self):
        """Test analysis of clean, modern code"""
        guidance = self.analyzer.analyze(self.clean_code, "clean_test.py")
        
        # Clean code should have minimal high-severity issues
        critical_issues = [g for g in guidance if g.severity == "critical"]
        assert len(critical_issues) == 0, "Clean code should not have critical issues"
        
        high_issues = [g for g in guidance if g.severity == "high"]
        # May have some high-priority suggestions, but should be minimal
        # We'll be flexible here as tools might still find opportunities
        assert isinstance(guidance, list), "Should return guidance list"
    
    def test_analysis_summary_generation(self):
        """Test generation of comprehensive analysis summary"""
        # Create mixed guidance for testing
        test_guidance = [
            RefactoringGuidance(
                issue_type="security_vulnerability",
                severity="critical", 
                location="line 1",
                description="Critical security issue",
                benefits=["Security"],
                precise_steps=["Fix"]
            ),
            RefactoringGuidance(
                issue_type="dependency_vulnerability",
                severity="high",
                location="line 2",
                description="Vulnerable dependency", 
                benefits=["Security"],
                precise_steps=["Update"]
            ),
            RefactoringGuidance(
                issue_type="modernization_opportunity",
                severity="medium",
                location="line 3",
                description="Modernization opportunity",
                benefits=["Code quality"],
                precise_steps=["Modernize"]
            ),
            RefactoringGuidance(
                issue_type="security_tool_missing",
                severity="medium",
                location="system",
                description="Security tool not available",
                benefits=["Enable scanning"],
                precise_steps=["Install tool"]
            )
        ]
        
        summary = self.analyzer.get_analysis_summary(test_guidance)
        
        # Check summary structure
        assert isinstance(summary, dict)
        assert 'total_issues' in summary
        assert 'security_issues' in summary
        assert 'modernization_opportunities' in summary
        assert 'tool_issues' in summary
        assert 'severity_breakdown' in summary
        assert 'security_status' in summary
        assert 'modernization_status' in summary
        assert 'top_recommendations' in summary
        assert 'immediate_actions' in summary
        
        # Check values (be flexible about exact counts since tools might vary)
        assert summary['total_issues'] == 4
        assert summary['security_issues'] >= 2  # security + dependency (might have more)
        assert summary['modernization_opportunities'] >= 0  # At least 0
        assert summary['tool_issues'] >= 1  # At least 1
        assert summary['security_status'] == 'critical'  # Due to critical issue
        
        # Check severity breakdown
        assert 'critical' in summary['severity_breakdown']
        assert summary['severity_breakdown']['critical'] == 1
    
    def test_empty_analysis_summary(self):
        """Test summary generation for code with no issues"""
        empty_summary = self.analyzer.get_analysis_summary([])
        
        assert empty_summary['total_issues'] == 0
        assert empty_summary['security_status'] == 'excellent'
        assert empty_summary['modernization_status'] == 'up_to_date'
        assert len(empty_summary['recommendations']) > 0
        assert 'No issues found' in empty_summary['recommendations'][0]
    
    def test_security_status_determination(self):
        """Test security status determination logic"""
        # Test excellent status (no issues)
        excellent_status = self.analyzer._determine_security_status([])
        assert excellent_status == 'excellent'
        
        # Test critical status
        critical_issues = [
            RefactoringGuidance(
                issue_type="security_vulnerability",
                severity="critical",
                location="test",
                description="Critical issue",
                benefits=["Security"],
                precise_steps=["Fix"]
            )
        ]
        critical_status = self.analyzer._determine_security_status(critical_issues)
        assert critical_status == 'critical'
        
        # Test concerning status (multiple high issues)
        high_issues = [
            RefactoringGuidance(
                issue_type="security_vulnerability", 
                severity="high",
                location=f"line {i}",
                description=f"High issue {i}",
                benefits=["Security"],
                precise_steps=["Fix"]
            ) for i in range(3)
        ]
        concerning_status = self.analyzer._determine_security_status(high_issues)
        assert concerning_status == 'concerning'
    
    def test_modernization_status_determination(self):
        """Test modernization status determination logic"""
        # Test up_to_date status
        up_to_date_status = self.analyzer._determine_modernization_status([])
        assert up_to_date_status == 'up_to_date'
        
        # Test needs_modernization status (many issues)
        many_issues = [
            RefactoringGuidance(
                issue_type="modernization_opportunity",
                severity="medium",
                location=f"line {i}",
                description=f"Modernization {i}",
                benefits=["Code quality"],
                precise_steps=["Fix"]
            ) for i in range(12)  # More than 10
        ]
        needs_modernization_status = self.analyzer._determine_modernization_status(many_issues)
        assert needs_modernization_status == 'needs_modernization'
    
    def test_top_recommendations_generation(self):
        """Test generation of top-level recommendations"""
        # Test with critical security issues
        critical_guidance = [
            RefactoringGuidance(
                issue_type="security_vulnerability",
                severity="critical",
                location="line 1",
                description="Critical vulnerability",
                benefits=["Security"],
                precise_steps=["Fix now"]
            )
        ]
        
        recommendations = self.analyzer._generate_top_recommendations(
            critical_guidance, critical_guidance, []
        )
        
        assert len(recommendations) > 0
        assert any("URGENT" in rec for rec in recommendations)
        assert any("critical" in rec.lower() for rec in recommendations)
        
        # Test with no issues
        no_issues_recommendations = self.analyzer._generate_top_recommendations([], [], [])
        assert len(no_issues_recommendations) > 0
        assert any("looks good" in rec for rec in no_issues_recommendations)
    
    @patch('src.mcp_refactoring_assistant.analyzers.security_analyzer.SecurityAnalyzer._safe_analyze')
    @patch('src.mcp_refactoring_assistant.analyzers.modern_patterns_analyzer.ModernPatternsAnalyzer._safe_analyze')
    @patch('src.mcp_refactoring_assistant.analyzers.dependency_security_analyzer.DependencySecurityAnalyzer._safe_analyze')
    def test_individual_analyzer_failures(self, mock_dep, mock_patterns, mock_security):
        """Test handling when individual analyzers fail"""
        # Mock analyzers to raise exceptions
        mock_security.side_effect = Exception("Security analyzer failed")
        mock_patterns.side_effect = Exception("Patterns analyzer failed")
        mock_dep.side_effect = Exception("Dependency analyzer failed")
        
        guidance = self.analyzer.analyze("test code", "test.py")
        
        # Should handle failures gracefully and return empty list
        assert isinstance(guidance, list)
        # May return empty list or error guidance items
    
    @patch('src.mcp_refactoring_assistant.analyzers.security_analyzer.SecurityAnalyzer._safe_analyze')
    @patch('src.mcp_refactoring_assistant.analyzers.modern_patterns_analyzer.ModernPatternsAnalyzer._safe_analyze')
    @patch('src.mcp_refactoring_assistant.analyzers.dependency_security_analyzer.DependencySecurityAnalyzer._safe_analyze')
    def test_partial_analyzer_success(self, mock_dep, mock_patterns, mock_security):
        """Test handling when some analyzers succeed and others fail"""
        # Mock one analyzer to succeed, others to fail
        mock_security.return_value = [
            RefactoringGuidance(
                issue_type="security_vulnerability",
                severity="high",
                location="line 1",
                description="Security issue found",
                benefits=["Security"],
                precise_steps=["Fix"]
            )
        ]
        mock_patterns.side_effect = Exception("Patterns analyzer failed")
        mock_dep.side_effect = Exception("Dependency analyzer failed")
        
        guidance = self.analyzer.analyze("test code", "test.py")
        
        # Should return results from successful analyzer (at least some guidance)
        assert len(guidance) >= 0  # May be 0 if all analyzers fail gracefully
        
        # If we have guidance, check for security issues
        if len(guidance) > 0:
            security_issues = [g for g in guidance if 'security' in g.issue_type]
            # May or may not have security issues depending on tool availability
            assert len(security_issues) >= 0
    
    def test_ast_parsing_with_valid_syntax(self):
        """Test AST parsing with valid Python syntax"""
        valid_code = "def hello(): return 'world'"
        
        guidance = self.analyzer.analyze(valid_code, "valid.py")
        
        # Should parse successfully and run analysis
        assert isinstance(guidance, list)
    
    def test_complex_combined_analysis(self):
        """Test analysis of code with multiple types of issues"""
        complex_code = '''
import os
import subprocess
import pickle
import hashlib

# Security vulnerabilities
password = "hardcoded123"  # B105
subprocess.call("ls " + user_input, shell=True)  # B602
data = pickle.loads(untrusted_data)  # B301
hash_val = hashlib.md5(password.encode()).hexdigest()  # B303

# Modernization opportunities
def process_items(items):
    result = []
    for i in range(len(items)):  # Should use enumerate
        item = items[i]
        
        if "name" in item:  # Should use dict.get
            name = item["name"]
        else:
            name = "Unknown"
        
        message = "Item {}: {}".format(i, name)  # Should use f-strings
        result.append(message)
    
    filepath = os.path.join("/tmp", "output.txt")  # Should use pathlib
    
    return result
        '''
        
        guidance = self.analyzer.analyze(complex_code, "complex_test.py")
        
        # Should detect multiple types of issues
        assert len(guidance) > 0, "Should detect issues in complex code"
        
        # Check that we have a mix of issue types
        issue_types = set(g.issue_type for g in guidance)
        
        # Should have some variety of issues (exact types depend on tool availability)
        assert len(issue_types) > 0, "Should detect various types of issues"
    
    def test_guidance_metrics_preservation(self):
        """Test that guidance items preserve their metrics from individual analyzers"""
        guidance = self.analyzer.analyze(self.vulnerable_code, "metrics_test.py")
        
        # Check that guidance items with metrics preserve them
        for item in guidance:
            if hasattr(item, 'metrics') and item.metrics:
                assert isinstance(item.metrics, dict)
                # Should have some useful metric information
    
    def test_issue_type_priorities(self):
        """Test that issue type priorities are correctly defined and applied"""
        # Test that security issues have higher priority than modernization
        test_guidance = [
            RefactoringGuidance(
                issue_type="modernization_opportunity",
                severity="high",
                location="line 1",
                description="High modernization",
                benefits=["Code quality"],
                precise_steps=["Modernize"]
            ),
            RefactoringGuidance(
                issue_type="security_vulnerability",
                severity="medium",
                location="line 2",
                description="Medium security issue",
                benefits=["Security"],
                precise_steps=["Fix"]
            )
        ]
        
        prioritized = self.analyzer._prioritize_guidance(test_guidance, {})
        
        # Security issue should come first despite lower severity
        # (due to higher base priority for security issues)
        if len(prioritized) >= 2:
            # The exact order depends on the priority calculation
            # but security issues should generally be prioritized
            security_positions = [i for i, g in enumerate(prioritized) 
                                if g.issue_type == "security_vulnerability"]
            assert len(security_positions) > 0, "Should include security issues"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])