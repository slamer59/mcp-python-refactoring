#!/usr/bin/env python3
"""
Dependency security analyzer using pip-audit for vulnerability scanning
"""

import ast
import json
import os
import subprocess
from pathlib import Path
from typing import List

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class DependencySecurityAnalyzer(BaseAnalyzer):
    """Analyzer using pip-audit for dependency vulnerability scanning"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use pip-audit for dependency security analysis"""
        guidance_list = []

        try:
            # Look for requirements files or pyproject.toml in the project
            project_root = self._find_project_root(file_path)
            requirements_files = self._find_requirements_files(project_root)
            
            if not requirements_files:
                # Try to extract imports from the code and check current environment
                guidance_list.extend(self._analyze_current_environment())
            else:
                # Analyze each requirements file found
                for req_file in requirements_files:
                    guidance_list.extend(self._analyze_requirements_file(req_file))

        except Exception as e:
            print(f"Warning: Dependency security analysis failed: {e}")

        return guidance_list

    def _find_project_root(self, file_path: str) -> Path:
        """Find the project root directory"""
        current_path = Path(file_path).parent if os.path.isfile(file_path) else Path(file_path)
        
        # Look for common project indicators
        project_indicators = [
            'pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', 
            '.git', 'Pipfile', 'poetry.lock', 'Cargo.toml'
        ]
        
        while current_path != current_path.parent:
            if any((current_path / indicator).exists() for indicator in project_indicators):
                return current_path
            current_path = current_path.parent
        
        # Default to the file's directory
        return Path(file_path).parent if os.path.isfile(file_path) else Path(file_path)

    def _find_requirements_files(self, project_root: Path) -> List[Path]:
        """Find requirements files in the project"""
        requirements_files = []
        
        # Common requirements file patterns
        patterns = [
            'requirements*.txt',
            'pyproject.toml',
            'setup.py',
            'Pipfile',
            'poetry.lock'
        ]
        
        for pattern in patterns:
            requirements_files.extend(project_root.glob(pattern))
        
        # Look in common subdirectories
        for subdir in ['requirements', 'deps', 'dependencies']:
            subdir_path = project_root / subdir
            if subdir_path.exists():
                requirements_files.extend(subdir_path.glob('*.txt'))
        
        return list(set(requirements_files))  # Remove duplicates

    def _analyze_requirements_file(self, requirements_file: Path) -> List[RefactoringGuidance]:
        """Analyze a specific requirements file with pip-audit"""
        guidance_list = []
        
        try:
            # Determine the appropriate pip-audit command based on file type
            if requirements_file.name == 'pyproject.toml':
                cmd = ['pip-audit', '--format', 'json', '--requirement', str(requirements_file)]
            elif requirements_file.name.endswith('.txt'):
                cmd = ['pip-audit', '--format', 'json', '--requirement', str(requirements_file)]
            else:
                # For other file types, try general scanning
                cmd = ['pip-audit', '--format', 'json', '--local']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=requirements_file.parent
            )
            
            if result.returncode == 0:
                if result.stdout:
                    try:
                        audit_data = json.loads(result.stdout)
                        guidance_list.extend(self._process_audit_results(audit_data, requirements_file))
                    except json.JSONDecodeError:
                        # Handle non-JSON output
                        if result.stdout.strip():
                            guidance_list.append(self._create_generic_guidance(
                                "dependency_scan_output",
                                f"Dependency scan completed for {requirements_file.name}",
                                result.stdout
                            ))
            elif result.returncode == 1:
                # Vulnerabilities found
                if result.stdout:
                    try:
                        audit_data = json.loads(result.stdout)
                        guidance_list.extend(self._process_audit_results(audit_data, requirements_file))
                    except json.JSONDecodeError:
                        guidance_list.append(self._create_generic_guidance(
                            "dependency_vulnerabilities_found",
                            f"Vulnerabilities found in {requirements_file.name}",
                            result.stdout
                        ))
            else:
                # Error occurred
                guidance_list.append(
                    RefactoringGuidance(
                        issue_type="dependency_scan_error",
                        severity="medium",
                        location=f"File {requirements_file}",
                        description=f"Dependency security scan failed: {result.stderr}",
                        benefits=["Fix scan issues to enable vulnerability detection"],
                        precise_steps=[
                            "1. Check requirements file format and syntax",
                            "2. Ensure pip-audit has access to required resources",
                            "3. Review pip-audit configuration",
                            "4. Consider manual dependency review"
                        ]
                    )
                )

        except subprocess.TimeoutExpired:
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="dependency_scan_timeout",
                    severity="medium",
                    location=f"File {requirements_file}",
                    description="Dependency security scan timed out",
                    benefits=["Optimize dependency resolution for better scanning"],
                    precise_steps=[
                        "1. Check for circular dependencies",
                        "2. Review large dependency lists",
                        "3. Consider breaking into smaller requirement files",
                        "4. Run scan with increased timeout"
                    ]
                )
            )
        except FileNotFoundError:
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="dependency_tool_missing",
                    severity="high",
                    location="System",
                    description="pip-audit dependency scanner not installed",
                    benefits=["Enable dependency vulnerability detection"],
                    precise_steps=[
                        "1. Install pip-audit: pip install pip-audit",
                        "2. Re-run dependency security scan",
                        "3. Consider integrating pip-audit into CI/CD pipeline",
                        "4. Set up automated dependency vulnerability monitoring"
                    ]
                )
            )
        
        return guidance_list

    def _analyze_current_environment(self) -> List[RefactoringGuidance]:
        """Analyze the current Python environment for vulnerabilities"""
        guidance_list = []
        
        try:
            # Scan current environment
            result = subprocess.run(
                ['pip-audit', '--format', 'json', '--local'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode in [0, 1]:
                if result.stdout:
                    try:
                        audit_data = json.loads(result.stdout)
                        guidance_list.extend(self._process_audit_results(audit_data, "current environment"))
                    except json.JSONDecodeError:
                        if result.stdout.strip():
                            guidance_list.append(self._create_generic_guidance(
                                "environment_scan_output",
                                "Current environment dependency scan completed",
                                result.stdout
                            ))
        
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # These are handled in _analyze_requirements_file, so we can skip here
            pass
        
        return guidance_list

    def _process_audit_results(self, audit_data: dict, source) -> List[RefactoringGuidance]:
        """Process pip-audit JSON results into RefactoringGuidance objects"""
        guidance_list = []
        
        # Handle different pip-audit output formats
        vulnerabilities = []
        if isinstance(audit_data, list):
            vulnerabilities = audit_data
        elif isinstance(audit_data, dict):
            vulnerabilities = audit_data.get('vulnerabilities', [])
        
        for vuln in vulnerabilities:
            package_name = vuln.get('package', 'unknown')
            installed_version = vuln.get('installed_version', 'unknown')
            vulnerability_id = vuln.get('id', 'unknown')
            description = vuln.get('description', 'No description available')
            fix_versions = vuln.get('fix_versions', [])
            
            # Determine severity
            severity = self._determine_vulnerability_severity(vuln)
            
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="dependency_vulnerability",
                    severity=severity,
                    location=f"Package {package_name} ({installed_version}) in {source}",
                    description=f"Security vulnerability {vulnerability_id} in {package_name}: {description}",
                    benefits=[
                        "Improved application security",
                        "Protection against known vulnerabilities",
                        "Better compliance with security standards",
                        "Reduced risk of security exploits"
                    ],
                    precise_steps=self._generate_vulnerability_fix_steps(vuln),
                    metrics={
                        "package_name": package_name,
                        "installed_version": installed_version,
                        "vulnerability_id": vulnerability_id,
                        "fix_versions": fix_versions,
                        "source": str(source)
                    }
                )
            )
        
        return guidance_list

    def _determine_vulnerability_severity(self, vulnerability: dict) -> str:
        """Determine severity based on vulnerability information"""
        
        # Check for explicit severity in the vulnerability data
        if 'severity' in vulnerability:
            severity_map = {
                'CRITICAL': 'critical',
                'HIGH': 'high',
                'MODERATE': 'medium',
                'MEDIUM': 'medium',
                'LOW': 'low'
            }
            return severity_map.get(vulnerability['severity'].upper(), 'medium')
        
        # Check for CVE scores or other indicators
        description = vulnerability.get('description', '').lower()
        
        # High severity indicators
        if any(indicator in description for indicator in [
            'remote code execution', 'rce', 'critical', 'arbitrary code',
            'privilege escalation', 'authentication bypass'
        ]):
            return 'critical'
        
        # Medium-high severity indicators
        if any(indicator in description for indicator in [
            'sql injection', 'xss', 'csrf', 'path traversal', 'high severity'
        ]):
            return 'high'
        
        # Medium severity indicators
        if any(indicator in description for indicator in [
            'denial of service', 'information disclosure', 'medium severity'
        ]):
            return 'medium'
        
        # Default to medium for unknown severities
        return 'medium'

    def _generate_vulnerability_fix_steps(self, vulnerability: dict) -> List[str]:
        """Generate specific steps to fix the vulnerability"""
        package_name = vulnerability.get('package', 'unknown')
        fix_versions = vulnerability.get('fix_versions', [])
        
        steps = [
            f"1. Update {package_name} to a secure version"
        ]
        
        if fix_versions:
            if len(fix_versions) == 1:
                steps.append(f"2. Install fixed version: pip install '{package_name}>={fix_versions[0]}'")
            else:
                steps.append(f"2. Install any of the fixed versions: {', '.join(fix_versions)}")
        else:
            steps.append("2. Check for alternative packages if no fix is available")
        
        steps.extend([
            "3. Update requirements.txt or pyproject.toml with the new version",
            "4. Test the application thoroughly after the update",
            "5. Review release notes for breaking changes",
            "6. Consider setting up automated dependency vulnerability monitoring"
        ])
        
        return steps

    def _create_generic_guidance(self, issue_type: str, title: str, output: str) -> RefactoringGuidance:
        """Create generic guidance for non-structured output"""
        return RefactoringGuidance(
            issue_type=issue_type,
            severity="medium",
            location="Dependencies",
            description=f"{title}: {output[:200]}{'...' if len(output) > 200 else ''}",
            benefits=[
                "Review dependency security status",
                "Ensure dependencies are up to date",
                "Maintain security best practices"
            ],
            precise_steps=[
                "1. Review the pip-audit output carefully",
                "2. Update vulnerable dependencies as needed",
                "3. Set up regular dependency security scanning",
                "4. Consider using dependency pinning for stability"
            ]
        )