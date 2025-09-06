#!/usr/bin/env python3
"""
Comprehensive tests for DependencySecurityAnalyzer using pip-audit for vulnerability scanning
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

from src.mcp_refactoring_assistant.analyzers.dependency_security_analyzer import DependencySecurityAnalyzer
from src.mcp_refactoring_assistant.models import RefactoringGuidance


class TestDependencySecurityAnalyzer:
    """Test cases for DependencySecurityAnalyzer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = DependencySecurityAnalyzer()
        
        # Load test files
        test_fixtures_dir = Path(__file__).parent / "fixtures" / "security_test_code"
        
        with open(test_fixtures_dir / "requirements_vulnerable.txt", 'r') as f:
            self.vulnerable_requirements = f.read()
    
    def test_find_project_root(self):
        """Test finding project root directory"""
        # Create temporary structure
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a nested structure with pyproject.toml
            nested_dir = temp_path / "src" / "mypackage"
            nested_dir.mkdir(parents=True)
            
            # Create project indicator
            (temp_path / "pyproject.toml").touch()
            
            # Test finding root from nested directory
            root = self.analyzer._find_project_root(str(nested_dir))
            
            assert root == temp_path, "Should find project root with pyproject.toml"
    
    def test_find_requirements_files(self):
        """Test finding requirements files in project"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create various requirements files
            (temp_path / "requirements.txt").touch()
            (temp_path / "requirements-dev.txt").touch()
            (temp_path / "pyproject.toml").touch()
            
            # Create requirements subdirectory
            req_dir = temp_path / "requirements"
            req_dir.mkdir()
            (req_dir / "base.txt").touch()
            (req_dir / "test.txt").touch()
            
            files = self.analyzer._find_requirements_files(temp_path)
            
            # Should find multiple requirements files
            assert len(files) > 0, "Should find requirements files"
            
            # Check that it finds the main requirements files
            file_names = [f.name for f in files]
            assert "requirements.txt" in file_names
            assert "pyproject.toml" in file_names
    
    @patch('subprocess.run')
    def test_analyze_requirements_file_with_vulnerabilities(self, mock_subprocess):
        """Test analysis of requirements file with vulnerabilities"""
        # Mock pip-audit output with vulnerabilities
        mock_result = MagicMock()
        mock_result.returncode = 1  # Vulnerabilities found
        mock_result.stdout = json.dumps({
            "vulnerabilities": [
                {
                    "package": "requests",
                    "installed_version": "2.25.1",
                    "id": "PYSEC-2023-99999",
                    "description": "Test vulnerability in requests",
                    "fix_versions": ["2.31.0"],
                    "severity": "HIGH"
                }
            ]
        })
        mock_subprocess.return_value = mock_result
        
        # Create temporary requirements file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests==2.25.1\n")
            requirements_path = Path(f.name)
        
        try:
            guidance = self.analyzer._analyze_requirements_file(requirements_path)
            
            # Should detect vulnerability
            assert len(guidance) > 0, "Should detect vulnerabilities"
            
            vuln_issues = [g for g in guidance if g.issue_type == "dependency_vulnerability"]
            assert len(vuln_issues) > 0, "Should find dependency vulnerabilities"
            
            # Check vulnerability details
            vuln = vuln_issues[0]
            assert "requests" in vuln.location
            assert "PYSEC-2023-99999" in vuln.description
            assert vuln.severity in ["low", "medium", "high", "critical"]
            
        finally:
            requirements_path.unlink()
    
    @patch('subprocess.run')
    def test_analyze_requirements_file_no_vulnerabilities(self, mock_subprocess):
        """Test analysis of requirements file with no vulnerabilities"""
        # Mock pip-audit output with no vulnerabilities
        mock_result = MagicMock()
        mock_result.returncode = 0  # No vulnerabilities
        mock_result.stdout = json.dumps({"vulnerabilities": []})
        mock_subprocess.return_value = mock_result
        
        # Create temporary requirements file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests==2.31.0\n")  # Safe version
            requirements_path = Path(f.name)
        
        try:
            guidance = self.analyzer._analyze_requirements_file(requirements_path)
            
            # Should have no or minimal issues
            vuln_issues = [g for g in guidance if g.issue_type == "dependency_vulnerability"]
            assert len(vuln_issues) == 0, "Should find no vulnerabilities in safe requirements"
            
        finally:
            requirements_path.unlink()
    
    @patch('subprocess.run')
    def test_analyze_current_environment(self, mock_subprocess):
        """Test analysis of current Python environment"""
        # Mock pip-audit output for current environment
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps([
            {
                "package": "pillow",
                "installed_version": "8.0.0",
                "id": "PYSEC-2023-88888", 
                "description": "Test vulnerability in Pillow",
                "fix_versions": ["9.0.0"]
            }
        ])
        mock_subprocess.return_value = mock_result
        
        guidance = self.analyzer._analyze_current_environment()
        
        # Should detect vulnerabilities in current environment
        assert len(guidance) > 0, "Should detect vulnerabilities in environment"
        
        vuln_issues = [g for g in guidance if g.issue_type == "dependency_vulnerability"]
        assert len(vuln_issues) > 0, "Should find dependency vulnerabilities"
    
    def test_determine_vulnerability_severity(self):
        """Test vulnerability severity determination"""
        # Test explicit severity mapping
        vuln_high = {"severity": "HIGH", "description": "Test vulnerability"}
        assert self.analyzer._determine_vulnerability_severity(vuln_high) == "high"
        
        vuln_critical = {"severity": "CRITICAL", "description": "Critical issue"}
        assert self.analyzer._determine_vulnerability_severity(vuln_critical) == "critical"
        
        # Test description-based severity
        vuln_rce = {"description": "Remote code execution vulnerability"}
        assert self.analyzer._determine_vulnerability_severity(vuln_rce) in ["critical", "high"]
        
        vuln_sql = {"description": "SQL injection vulnerability"}
        assert self.analyzer._determine_vulnerability_severity(vuln_sql) == "high"
        
        vuln_dos = {"description": "Denial of service vulnerability"}
        assert self.analyzer._determine_vulnerability_severity(vuln_dos) == "medium"
        
        # Test unknown severity
        vuln_unknown = {"description": "Some unknown vulnerability"}
        assert self.analyzer._determine_vulnerability_severity(vuln_unknown) == "medium"
    
    def test_generate_vulnerability_fix_steps(self):
        """Test generation of vulnerability fix steps"""
        # Test with fix versions available
        vuln_with_fix = {
            "package": "requests",
            "fix_versions": ["2.31.0"]
        }
        steps = self.analyzer._generate_vulnerability_fix_steps(vuln_with_fix)
        
        assert isinstance(steps, list)
        assert len(steps) > 0
        assert any("requests" in step for step in steps)
        assert any("2.31.0" in step for step in steps)
        
        # Test with multiple fix versions
        vuln_multi_fix = {
            "package": "pillow",
            "fix_versions": ["8.3.0", "9.0.0"]
        }
        steps = self.analyzer._generate_vulnerability_fix_steps(vuln_multi_fix)
        
        assert len(steps) > 0
        assert any("8.3.0" in step or "9.0.0" in step for step in steps)
        
        # Test with no fix versions
        vuln_no_fix = {
            "package": "vulnerable-package",
            "fix_versions": []
        }
        steps = self.analyzer._generate_vulnerability_fix_steps(vuln_no_fix)
        
        assert len(steps) > 0
        assert any("alternative" in step.lower() for step in steps)
    
    def test_process_audit_results_list_format(self):
        """Test processing audit results in list format"""
        audit_data = [
            {
                "package": "pyyaml",
                "installed_version": "5.1",
                "id": "PYSEC-2023-77777",
                "description": "Test YAML vulnerability"
            }
        ]
        
        guidance = self.analyzer._process_audit_results(audit_data, "test source")
        
        assert len(guidance) > 0
        assert guidance[0].issue_type == "dependency_vulnerability"
        assert "pyyaml" in guidance[0].location.lower()
    
    def test_process_audit_results_dict_format(self):
        """Test processing audit results in dict format"""
        audit_data = {
            "vulnerabilities": [
                {
                    "package": "django",
                    "installed_version": "3.0.0",
                    "id": "PYSEC-2023-66666",
                    "description": "Test Django vulnerability",
                    "fix_versions": ["3.2.0"]
                }
            ]
        }
        
        guidance = self.analyzer._process_audit_results(audit_data, "requirements.txt")
        
        assert len(guidance) > 0
        assert guidance[0].issue_type == "dependency_vulnerability"
        assert "django" in guidance[0].location.lower()
    
    @patch('subprocess.run')
    def test_pip_audit_timeout_handling(self, mock_subprocess):
        """Test handling of pip-audit timeouts"""
        from subprocess import TimeoutExpired
        mock_subprocess.side_effect = TimeoutExpired("pip-audit", 60)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests==2.25.1\n")
            requirements_path = Path(f.name)
        
        try:
            guidance = self.analyzer._analyze_requirements_file(requirements_path)
            
            # Should handle timeout gracefully
            timeout_issues = [g for g in guidance if "timeout" in g.issue_type]
            assert len(timeout_issues) > 0, "Should report timeout issue"
            
        finally:
            requirements_path.unlink()
    
    @patch('subprocess.run')
    def test_pip_audit_not_installed_handling(self, mock_subprocess):
        """Test handling when pip-audit is not installed"""
        mock_subprocess.side_effect = FileNotFoundError("pip-audit not found")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("requests==2.25.1\n")
            requirements_path = Path(f.name)
        
        try:
            guidance = self.analyzer._analyze_requirements_file(requirements_path)
            
            # Should report tool missing
            tool_issues = [g for g in guidance if "tool_missing" in g.issue_type]
            assert len(tool_issues) > 0, "Should report missing pip-audit tool"
            
        finally:
            requirements_path.unlink()
    
    @patch('subprocess.run')
    def test_pip_audit_error_handling(self, mock_subprocess):
        """Test handling of pip-audit errors"""
        mock_result = MagicMock()
        mock_result.returncode = 2  # Error
        mock_result.stderr = "pip-audit error"
        mock_subprocess.return_value = mock_result
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("invalid-package==1.0.0\n")
            requirements_path = Path(f.name)
        
        try:
            guidance = self.analyzer._analyze_requirements_file(requirements_path)
            
            # Should handle errors gracefully
            error_issues = [g for g in guidance if "error" in g.issue_type]
            assert len(error_issues) > 0, "Should report analysis error"
            
        finally:
            requirements_path.unlink()
    
    def test_analyze_with_no_requirements_files(self):
        """Test analysis when no requirements files are found"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a Python file but no requirements
            test_file = temp_path / "test.py"
            test_file.write_text("import requests\nprint('hello')")
            
            guidance = self.analyzer.analyze("import requests", str(test_file))
            
            # Should attempt to analyze current environment
            assert isinstance(guidance, list), "Should return guidance list"
    
    def test_analyze_with_multiple_requirements_files(self):
        """Test analysis with multiple requirements files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple requirements files
            (temp_path / "requirements.txt").write_text("requests==2.25.1\n")
            (temp_path / "requirements-dev.txt").write_text("pytest==6.0.0\n")
            
            test_file = temp_path / "test.py"
            test_file.write_text("import requests")
            
            with patch('subprocess.run') as mock_subprocess:
                # Mock successful analysis
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({"vulnerabilities": []})
                mock_subprocess.return_value = mock_result
                
                guidance = self.analyzer.analyze("import requests", str(test_file))
                
                # Should analyze multiple files
                assert isinstance(guidance, list)
    
    def test_create_generic_guidance(self):
        """Test creation of generic guidance for non-structured output"""
        guidance = self.analyzer._create_generic_guidance(
            "dependency_scan_output",
            "Scan completed",
            "Some output text"
        )
        
        assert isinstance(guidance, RefactoringGuidance)
        assert guidance.issue_type == "dependency_scan_output"
        assert guidance.severity == "medium"
        assert "Scan completed" in guidance.description
        assert len(guidance.benefits) > 0
        assert len(guidance.precise_steps) > 0
    
    def test_analyze_pyproject_toml(self):
        """Test analysis of pyproject.toml files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create pyproject.toml
            pyproject_content = '''
[build-system]
requires = ["setuptools", "wheel"]

[project]
dependencies = [
    "requests>=2.25.0",
    "pyyaml>=5.1"
]
            '''
            (temp_path / "pyproject.toml").write_text(pyproject_content)
            
            test_file = temp_path / "test.py"
            test_file.write_text("import requests")
            
            with patch('subprocess.run') as mock_subprocess:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = json.dumps({"vulnerabilities": []})
                mock_subprocess.return_value = mock_result
                
                guidance = self.analyzer.analyze("import requests", str(test_file))
                
                # Should handle pyproject.toml
                assert isinstance(guidance, list)
    
    def test_guidance_structure(self):
        """Test that guidance objects have proper structure"""
        # Create test vulnerability data
        test_vuln = {
            "package": "test-package",
            "installed_version": "1.0.0",
            "id": "TEST-2023-001",
            "description": "Test vulnerability",
            "fix_versions": ["1.1.0"]
        }
        
        guidance = self.analyzer._process_audit_results([test_vuln], "test.txt")
        
        assert len(guidance) > 0
        item = guidance[0]
        
        # Check required fields
        assert hasattr(item, 'issue_type')
        assert hasattr(item, 'severity')
        assert hasattr(item, 'location')
        assert hasattr(item, 'description')
        assert hasattr(item, 'benefits')
        assert hasattr(item, 'precise_steps')
        assert hasattr(item, 'metrics')
        
        # Check field types and content
        assert isinstance(item.benefits, list)
        assert len(item.benefits) > 0
        assert isinstance(item.precise_steps, list)
        assert len(item.precise_steps) > 0
        assert isinstance(item.description, str)
        assert len(item.description) > 0
        assert isinstance(item.metrics, dict)
        
        # Check specific metrics
        assert 'package_name' in item.metrics
        assert 'vulnerability_id' in item.metrics
        assert 'fix_versions' in item.metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])