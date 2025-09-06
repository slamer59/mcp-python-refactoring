#!/usr/bin/env python3
"""
Security analyzer using Bandit for vulnerability detection
"""

import ast
import json
import subprocess
import tempfile
from typing import List

from ..models import RefactoringGuidance
from .base import BaseAnalyzer


class SecurityAnalyzer(BaseAnalyzer):
    """Analyzer using Bandit for security vulnerability detection"""

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """Use Bandit for security analysis"""
        guidance_list = []

        try:
            # Create temporary file for bandit analysis
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            # Run bandit on the temporary file
            result = subprocess.run(
                ['bandit', '-f', 'json', temp_file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up temporary file
            import os
            os.unlink(temp_file_path)

            if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                if result.stdout:
                    bandit_data = json.loads(result.stdout)
                    
                    # Process bandit results
                    for issue in bandit_data.get('results', []):
                        severity_map = {
                            'LOW': 'low',
                            'MEDIUM': 'medium', 
                            'HIGH': 'high'
                        }
                        
                        confidence_map = {
                            'LOW': 'uncertain',
                            'MEDIUM': 'likely',
                            'HIGH': 'definite'
                        }
                        
                        severity = severity_map.get(issue.get('issue_severity', 'MEDIUM'), 'medium')
                        confidence = confidence_map.get(issue.get('issue_confidence', 'MEDIUM'), 'likely')
                        
                        # Adjust severity based on confidence
                        if confidence == 'uncertain' and severity == 'high':
                            severity = 'medium'
                        
                        guidance_list.append(
                            RefactoringGuidance(
                                issue_type="security_vulnerability",
                                severity=severity,
                                location=f"Line {issue.get('line_number', 'unknown')} in {file_path}",
                                description=f"Security issue ({issue.get('test_id', 'unknown')}): {issue.get('issue_text', 'Unknown security issue')}",
                                benefits=[
                                    "Improved application security",
                                    "Reduced vulnerability risk",
                                    "Better compliance with security standards",
                                    "Protection against common attack vectors"
                                ],
                                precise_steps=self._generate_security_steps(issue),
                                code_snippet=issue.get('code', ''),
                                metrics={
                                    "test_id": issue.get('test_id', ''),
                                    "issue_severity": issue.get('issue_severity', ''),
                                    "issue_confidence": issue.get('issue_confidence', ''),
                                    "line_number": issue.get('line_number', 0),
                                    "filename": issue.get('filename', ''),
                                    "more_info": issue.get('more_info', '')
                                }
                            )
                        )
                        
            elif result.returncode == 2:
                # Bandit error occurred
                guidance_list.append(
                    RefactoringGuidance(
                        issue_type="security_analysis_error",
                        severity="low",
                        location=f"File {file_path}",
                        description=f"Security analysis failed: {result.stderr}",
                        benefits=["Fix syntax or analysis issues to enable security scanning"],
                        precise_steps=[
                            "1. Check file syntax and structure",
                            "2. Ensure file contains valid Python code",
                            "3. Review bandit configuration if needed"
                        ]
                    )
                )

        except subprocess.TimeoutExpired:
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="security_analysis_timeout",
                    severity="low",
                    location=f"File {file_path}",
                    description="Security analysis timed out - file may be too large or complex",
                    benefits=["Optimize file size and complexity for better analysis"],
                    precise_steps=[
                        "1. Consider breaking large files into smaller modules",
                        "2. Reduce complexity where possible",
                        "3. Run security analysis on individual functions"
                    ]
                )
            )
        except FileNotFoundError:
            guidance_list.append(
                RefactoringGuidance(
                    issue_type="security_tool_missing",
                    severity="medium",
                    location="System",
                    description="Bandit security scanner not installed",
                    benefits=["Enable security vulnerability detection"],
                    precise_steps=[
                        "1. Install bandit: pip install bandit",
                        "2. Re-run security analysis",
                        "3. Consider integrating bandit into CI/CD pipeline"
                    ]
                )
            )
        except Exception as e:
            print(f"Warning: Security analysis failed: {e}")

        return guidance_list

    def _generate_security_steps(self, issue: dict) -> List[str]:
        """Generate specific remediation steps based on bandit issue type"""
        test_id = issue.get('test_id', '')
        
        # Common security remediation patterns
        step_patterns = {
            'B101': [  # assert_used
                "1. Replace assert statements with proper exception handling",
                "2. Use explicit if-conditions for validation",
                "3. Consider using logging for debug information",
                "4. Ensure production code doesn't rely on assertions"
            ],
            'B102': [  # exec_used
                "1. Avoid using exec() function - major security risk",
                "2. Use safer alternatives like importlib for dynamic imports",
                "3. If absolutely necessary, sanitize and validate all inputs",
                "4. Consider redesigning to avoid dynamic code execution"
            ],
            'B103': [  # set_bad_file_permissions
                "1. Review file permissions - avoid overly permissive settings",
                "2. Use specific permissions (e.g., 0o644 instead of 0o777)",
                "3. Follow principle of least privilege",
                "4. Consider using constants for common permission patterns"
            ],
            'B104': [  # hardcoded_bind_all_interfaces
                "1. Avoid binding to all interfaces (0.0.0.0) in production",
                "2. Bind to specific interfaces when possible",
                "3. Use configuration for different environments",
                "4. Consider firewall rules and network security"
            ],
            'B105': [  # hardcoded_password_string
                "1. Remove hardcoded passwords immediately",
                "2. Use environment variables for sensitive data",
                "3. Consider using secret management systems",
                "4. Implement proper authentication mechanisms"
            ],
            'B106': [  # hardcoded_password_funcarg
                "1. Remove hardcoded password in function argument",
                "2. Use secure password input methods",
                "3. Implement proper credential management",
                "4. Consider using authentication libraries"
            ],
            'B107': [  # hardcoded_password_default
                "1. Remove hardcoded default password",
                "2. Force users to set strong passwords",
                "3. Implement password complexity requirements",
                "4. Use secure defaults or require configuration"
            ],
            'B108': [  # hardcoded_tmp_directory
                "1. Use tempfile module for temporary file creation",
                "2. Avoid hardcoded /tmp paths",
                "3. Ensure proper cleanup of temporary files",
                "4. Set appropriate permissions on temporary files"
            ],
            'B110': [  # try_except_pass
                "1. Avoid bare except clauses that silently ignore errors",
                "2. Log exceptions appropriately",
                "3. Handle specific exceptions explicitly",
                "4. Ensure proper error recovery or propagation"
            ],
            'B112': [  # try_except_continue
                "1. Review exception handling in loops",
                "2. Log exceptions before continuing",
                "3. Consider if the exception should break the loop",
                "4. Ensure proper error handling strategy"
            ],
            'B201': [  # flask_debug_true
                "1. Set Flask debug=False in production",
                "2. Use environment variables for debug settings",
                "3. Ensure proper logging configuration",
                "4. Review error handling in production mode"
            ],
            'B301': [  # pickle
                "1. Avoid using pickle with untrusted data",
                "2. Use safer serialization formats like JSON",
                "3. If pickle is necessary, validate data sources",
                "4. Consider using cryptographic signatures"
            ],
            'B302': [  # marshal
                "1. Avoid marshal.loads with untrusted data",
                "2. Use safer alternatives for data serialization",
                "3. Validate all input data thoroughly",
                "4. Consider using structured data formats"
            ],
            'B303': [  # md5
                "1. Replace MD5 with stronger hash functions",
                "2. Use SHA-256 or higher for cryptographic purposes",
                "3. Consider using bcrypt or scrypt for passwords",
                "4. Review all cryptographic implementations"
            ],
            'B304': [  # insecure_cipher
                "1. Replace insecure cipher with modern alternatives",
                "2. Use AES with proper modes (GCM, CBC with HMAC)",
                "3. Ensure proper key management",
                "4. Review entire cryptographic implementation"
            ],
            'B305': [  # weak_cipher_mode
                "1. Use secure cipher modes (GCM, CBC with authentication)",
                "2. Avoid ECB mode entirely",
                "3. Implement proper initialization vectors",
                "4. Consider using high-level cryptographic libraries"
            ],
            'B306': [  # mktemp_q
                "1. Replace mktemp() with mkstemp() or NamedTemporaryFile",
                "2. Ensure proper file permissions and cleanup",
                "3. Use context managers for automatic cleanup",
                "4. Consider using tempfile.TemporaryDirectory"
            ],
            'B401': [  # import_telnetlib
                "1. Replace telnetlib with secure alternatives",
                "2. Use SSH for secure remote connections",
                "3. Implement proper authentication and encryption",
                "4. Review all network communication protocols"
            ],
            'B402': [  # import_ftplib
                "1. Replace FTP with secure alternatives (SFTP, FTPS)",
                "2. Use paramiko or similar for secure file transfer",
                "3. Implement proper authentication mechanisms",
                "4. Encrypt all data in transit"
            ],
            'B403': [  # import_pickle
                "1. Avoid pickle for untrusted data deserialization",
                "2. Use safer serialization formats",
                "3. Implement input validation and sanitization",
                "4. Consider using JSON or other safe formats"
            ],
            'B501': [  # request_with_no_cert_validation
                "1. Enable SSL certificate verification",
                "2. Set verify=True in requests calls",
                "3. Use proper certificate validation",
                "4. Implement certificate pinning if needed"
            ],
            'B502': [  # ssl_with_bad_version
                "1. Use modern SSL/TLS versions (TLS 1.2+)",
                "2. Remove support for deprecated protocols",
                "3. Configure proper SSL context",
                "4. Regularly update SSL/TLS configurations"
            ],
            'B503': [  # ssl_with_bad_defaults
                "1. Configure SSL with secure defaults",
                "2. Disable weak ciphers and protocols",
                "3. Enable certificate validation",
                "4. Use ssl.create_default_context()"
            ],
            'B506': [  # yaml_load
                "1. Use yaml.safe_load() instead of yaml.load()",
                "2. Validate YAML structure and content",
                "3. Avoid loading untrusted YAML data",
                "4. Consider using safer configuration formats"
            ],
            'B601': [  # paramiko_calls
                "1. Review Paramiko configuration for security",
                "2. Use proper authentication methods",
                "3. Validate host keys properly",
                "4. Implement connection security best practices"
            ],
            'B602': [  # subprocess_popen_with_shell_equals_true
                "1. Avoid shell=True in subprocess calls",
                "2. Use argument lists instead of shell commands",
                "3. Sanitize and validate all inputs",
                "4. Consider using shlex for command parsing"
            ],
            'B603': [  # subprocess_without_shell_equals_false
                "1. Set shell=False explicitly in subprocess calls",
                "2. Use secure subprocess practices",
                "3. Validate all command arguments",
                "4. Consider input sanitization"
            ],
            'B604': [  # any_other_function_with_shell_equals_true
                "1. Review shell command execution for security risks",
                "2. Avoid shell=True when possible",
                "3. Sanitize all user inputs",
                "4. Use safer alternatives to shell commands"
            ],
            'B605': [  # start_process_with_a_shell
                "1. Avoid starting processes with shell access",
                "2. Use direct process execution",
                "3. Validate and sanitize all inputs",
                "4. Implement proper process security"
            ],
            'B606': [  # start_process_with_no_shell
                "1. Review process execution for security",
                "2. Validate all arguments and inputs",
                "3. Implement proper error handling",
                "4. Consider process isolation"
            ],
            'B607': [  # start_process_with_partial_path
                "1. Use absolute paths for executable files",
                "2. Avoid relying on PATH environment variable",
                "3. Validate executable permissions",
                "4. Implement path validation"
            ],
            'B608': [  # hardcoded_sql_expressions
                "1. Use parameterized queries to prevent SQL injection",
                "2. Validate and sanitize all user inputs",
                "3. Use ORM frameworks with built-in protection",
                "4. Implement input validation and escaping"
            ],
            'B609': [  # linux_commands_wildcard_injection
                "1. Avoid using wildcards with user input",
                "2. Sanitize file paths and patterns",
                "3. Use specific file operations instead of wildcards",
                "4. Implement proper input validation"
            ],
            'B701': [  # jinja2_autoescape_false
                "1. Enable auto-escaping in Jinja2 templates",
                "2. Manually escape user input when necessary",
                "3. Validate all template variables",
                "4. Review template security configurations"
            ],
            'B702': [  # use_of_mako_templates
                "1. Review Mako template security configurations",
                "2. Enable proper escaping mechanisms",
                "3. Validate all template inputs",
                "4. Consider using safer template engines"
            ],
            'B703': [  # django_mark_safe
                "1. Review django.utils.safestring.mark_safe usage",
                "2. Ensure marked content is actually safe",
                "3. Sanitize content before marking as safe",
                "4. Consider alternative approaches"
            ]
        }
        
        # Return specific steps if available, otherwise generic steps
        return step_patterns.get(test_id, [
            "1. Review the security issue identified by bandit",
            "2. Consult security best practices for this pattern",
            "3. Implement appropriate security measures",
            "4. Test the fix thoroughly",
            "5. Consider security code review"
        ])