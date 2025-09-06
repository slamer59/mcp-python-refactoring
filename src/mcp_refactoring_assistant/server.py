#!/usr/bin/env python3
"""
Enhanced Python Refactoring MCP Tool - Clean Modular Architecture

This MCP tool leverages powerful libraries to provide professional-grade
refactoring analysis and guidance without automatically modifying code.

Now using a modular architecture with separated analyzers and Pydantic models.
"""

import ast
import json
import glob
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

# Import the new modular components
from .core import EnhancedRefactoringAnalyzer
from .core.package_analyzer import PackageAnalyzer
from .analyzers import SecurityAndPatternsAnalyzer


class AdvancedFeatures:
    """Container for advanced features that need further modularization"""
    
    def __init__(self) -> None:
        self.analyzer = EnhancedRefactoringAnalyzer()
    
    def analyze_test_coverage(self, source_path: str, test_path: Optional[str] = None, target_coverage: int = 80) -> Dict[str, Any]:
        """Analyze test coverage and provide improvement suggestions"""
        result = self._initialize_coverage_result()
        
        try:
            import coverage
        except ImportError:
            coverage = None
        
        try:
            # Run coverage analysis if test path provided
            if test_path and os.path.exists(test_path):
                self._run_coverage_analysis(source_path, test_path, result)
            
            # Analyze source files for testing needs
            source_files = self._get_source_files(source_path)
            self._analyze_source_files(source_files, result)
            
            # Generate recommendations
            result["recommendations"] = self._generate_testing_recommendations(
                result["files_needing_tests"], 
                target_coverage
            )
            
        except ImportError:
            result["error"] = "Coverage package not installed. Install with: pip install coverage"
        except Exception as e:
            result["error"] = f"Coverage analysis failed: {str(e)}"
        
        return result
    
    def _initialize_coverage_result(self) -> Dict[str, Any]:
        """Initialize the coverage analysis result dictionary"""
        return {
            "coverage_analysis": {},
            "missing_coverage": [],
            "testing_suggestions": [],
            "files_needing_tests": [],
            "coverage_report": "",
            "recommendations": []
        }
    
    def _run_coverage_analysis(self, source_path: str, test_path: str, result: Dict[str, Any]) -> None:
        """Run pytest with coverage analysis"""
        try:
            # Run pytest with coverage
            cmd = [
                "python", "-m", "pytest", 
                test_path,
                f"--cov={source_path}",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json"
            ]
            subprocess.run(cmd, capture_output=True, text=True, cwd=".")
            
            # Read coverage.json if it exists
            if os.path.exists("coverage.json"):
                with open("coverage.json", "r") as f:
                    coverage_data = json.load(f)
                    result["coverage_analysis"] = coverage_data
                os.remove("coverage.json")
                
        except Exception as e:
            result["error"] = f"Error running tests: {e}"
    
    def _get_source_files(self, source_path: str) -> List[str]:
        """Get list of source files to analyze"""
        if os.path.isfile(source_path):
            return [source_path]
        else:
            return glob.glob(f"{source_path}/**/*.py", recursive=True)
    
    def _analyze_source_files(self, source_files: List[str], result: Dict[str, Any]) -> None:
        """Analyze source files for testing needs"""
        for file_path in source_files:
            if "__pycache__" in file_path or file_path.endswith("__init__.py"):
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Analyze what needs testing
            analysis = self._analyze_testability(content, file_path)
            result["missing_coverage"].extend(analysis["untested_functions"])
            result["testing_suggestions"].extend(analysis["suggestions"])
            
            if analysis["needs_tests"]:
                result["files_needing_tests"].append({
                    "file": file_path,
                    "functions": analysis["functions"],
                    "classes": analysis["classes"],
                    "complexity": analysis["complexity_score"]
                })

    def _analyze_testability(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze code for testability and testing needs"""
        result = {
            "untested_functions": [],
            "suggestions": [],
            "needs_tests": False,
            "functions": [],
            "classes": [],
            "complexity_score": 0
        }
        
        try:
            tree = ast.parse(content)
            
            # Find functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args),
                        "is_private": node.name.startswith("_"),
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(node) is not None
                    }
                    result["functions"].append(func_info)
                    
                    # Suggest tests for public functions
                    if not node.name.startswith("_") and node.name != "__init__":
                        result["untested_functions"].append(f"{file_path}:{node.lineno} - Function '{node.name}'")
                        result["suggestions"].append({
                            "type": "unit_test",
                            "target": f"{node.name}",
                            "location": f"{file_path}:{node.lineno}",
                            "suggestion": f"Create test for function '{node.name}' - {len(node.args.args)} parameters",
                            "priority": "high" if len(node.args.args) > 3 else "medium"
                        })
                
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
                        "is_private": node.name.startswith("_")
                    }
                    result["classes"].append(class_info)
                    
                    if not node.name.startswith("_"):
                        result["suggestions"].append({
                            "type": "class_test",
                            "target": f"{node.name}",
                            "location": f"{file_path}:{node.lineno}",
                            "suggestion": f"Create test class for '{node.name}' with {class_info['methods']} methods",
                            "priority": "high"
                        })
            
            # Calculate complexity score
            result["complexity_score"] = len(result["functions"]) * 0.3 + len(result["classes"]) * 0.7
            result["needs_tests"] = len(result["functions"]) > 0 or len(result["classes"]) > 0
            
        except Exception as e:
            result["suggestions"].append({
                "type": "error",
                "suggestion": f"Could not analyze {file_path}: {e}",
                "priority": "low"
            })
        
        return result
    
    def _generate_testing_recommendations(self, files_needing_tests: List[Dict], target_coverage: int) -> List[str]:
        """Generate specific testing recommendations based on existing setup"""
        recommendations = []
        
        if not files_needing_tests:
            recommendations.append("✅ No additional tests needed - good job!")
            return recommendations
        
        # Detect existing test framework and setup
        test_framework = self._detect_test_framework()
        
        # Generate header recommendations
        recommendations.extend(self._generate_recommendation_header(files_needing_tests, target_coverage, test_framework))
        
        # Generate priority file recommendations
        priority_files = sorted(files_needing_tests, key=lambda x: x["complexity"], reverse=True)[:5]
        recommendations.extend(self._generate_priority_file_recommendations(priority_files))
        
        return recommendations
    
    def _generate_recommendation_header(self, files_needing_tests: List[Dict], target_coverage: int, test_framework: Dict) -> List[str]:
        """Generate header section of recommendations"""
        return [
            f"🎯 TARGET: {target_coverage}% test coverage",
            f"📊 ANALYSIS: {len(files_needing_tests)} files need testing",
            f"🔍 DETECTED: {test_framework['framework']} framework",
            "",
            "📋 TESTING STRATEGY:"
        ]
    
    def _generate_priority_file_recommendations(self, priority_files: List[Dict]) -> List[str]:
        """Generate recommendations for priority files"""
        recommendations = []
        for i, file_info in enumerate(priority_files, 1):
            recommendations.append(f"{i}. {file_info['file']}")
            recommendations.append(f"   • {len(file_info['functions'])} functions, {len(file_info['classes'])} classes")
            recommendations.append(f"   • Complexity: {file_info['complexity']:.1f}")
            recommendations.append("")
        return recommendations
    
    def _detect_test_framework(self) -> Dict[str, Any]:
        """Detect existing test framework and configuration"""
        framework_info = {
            "framework": "pytest",  # Default based on our project
            "config_files": [],
            "test_directory": None,
            "coverage_tool": None,
            "existing_tests": []
        }
        
        # Check for pytest
        if os.path.exists("pytest.ini") or os.path.exists("pyproject.toml"):
            framework_info["framework"] = "pytest"
            if os.path.exists("pytest.ini"):
                framework_info["config_files"].append("pytest.ini")
            if os.path.exists("pyproject.toml"):
                framework_info["config_files"].append("pyproject.toml")
        
        # Detect test directory
        for test_dir in ["tests", "test", "testing"]:
            if os.path.exists(test_dir):
                framework_info["test_directory"] = test_dir
                # Count existing test files
                test_files = glob.glob(f"{test_dir}/**/test_*.py", recursive=True)
                framework_info["existing_tests"] = test_files
                break
        
        return framework_info

    def generate_tdd_refactoring_guidance(self, content: str, function_name: Optional[str] = None, test_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate TDD-based refactoring guidance following Red-Green-Refactor pattern"""
        result = {
            "tdd_workflow": [],
            "current_tests": {},
            "missing_tests": [],
            "refactoring_targets": [],
            "step_by_step_plan": [],
            "test_templates": {}
        }
        
        try:
            # Parse code to identify refactoring targets
            tree = ast.parse(content)
            refactoring_targets = []
            
            # Find complex functions/classes that need refactoring
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if function_name and node.name != function_name:
                        continue
                    
                    # Calculate complexity
                    complexity = self._calculate_function_complexity(node, content)
                    if complexity > 10 or (hasattr(node, 'end_lineno') and (node.end_lineno - node.lineno) > 20):
                        refactoring_targets.append({
                            "type": "function",
                            "name": node.name,
                            "line": node.lineno,
                            "complexity": complexity,
                            "needs_test": True
                        })
                
                elif isinstance(node, ast.ClassDef):
                    if function_name and node.name != function_name:
                        continue
                    
                    method_count = len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                    if method_count > 5:
                        refactoring_targets.append({
                            "type": "class", 
                            "name": node.name,
                            "line": node.lineno,
                            "methods": method_count,
                            "needs_test": True
                        })
            
            result["refactoring_targets"] = refactoring_targets
            
            # Overall TDD workflow
            result["tdd_workflow"] = [
                "🔴 RED: Write failing tests first",
                "🟢 GREEN: Make tests pass with minimal code", 
                "🔵 REFACTOR: Improve code while keeping tests green",
                "🔄 REPEAT: Continue cycle for each improvement"
            ]
            
        except Exception as e:
            result["error"] = f"TDD analysis failed: {str(e)}"
        
        return result
    
    def _calculate_function_complexity(self, node: ast.FunctionDef, content: str) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity


def _create_analysis_summary(guidance: List[Any]) -> Dict[str, int]:
    """Create analysis summary statistics from guidance list"""
    return {
        "total_issues_found": len(guidance),
        "critical_issues": len([g for g in guidance if hasattr(g, 'severity') and g.severity == "critical"]),
        "high_priority": len([g for g in guidance if hasattr(g, 'severity') and g.severity == "high"]),
        "medium_priority": len([g for g in guidance if hasattr(g, 'severity') and g.severity == "medium"]),
        "low_priority": len([g for g in guidance if hasattr(g, 'severity') and g.severity == "low"]),
    }


# MCP Server Implementation
try:
    import mcp
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server import Server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

if MCP_AVAILABLE:
    # Create the server instance
    server = Server("python-refactoring-assistant")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available refactoring analysis tools"""
        return [
            types.Tool(
                name="analyze_python_file",
                description="Analyze Python file for refactoring opportunities with precise guidance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file to analyze",
                        },
                        "content": {
                            "type": "string",
                            "description": "Python file content to analyze",
                        },
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="get_extraction_guidance",
                description="Get detailed step-by-step guidance for extracting functions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file",
                        },
                        "content": {
                            "type": "string",
                            "description": "Python file content",
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Name of function to analyze for extraction",
                        },
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="find_long_functions",
                description="Find functions that are candidates for extraction",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python file content to analyze",
                        },
                        "line_threshold": {
                            "type": "integer",
                            "description": "Minimum lines to consider a function long (default: 20)",
                        },
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="analyze_test_coverage",
                description="Analyze Python test coverage and suggest improvements",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_path": {
                            "type": "string",
                            "description": "Path to source code directory or file",
                        },
                        "test_path": {
                            "type": "string", 
                            "description": "Path to test directory (optional)",
                        },
                        "target_coverage": {
                            "type": "integer",
                            "description": "Target coverage percentage (default: 80)",
                            "default": 80
                        }
                    },
                    "required": ["source_path"],
                },
            ),
            types.Tool(
                name="tdd_refactoring_guidance",
                description="Generate TDD-based refactoring guidance: test first, refactor, test again",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Python code content to refactor",
                        },
                        "function_name": {
                            "type": "string",
                            "description": "Specific function/class to refactor (optional)",
                        },
                        "test_path": {
                            "type": "string",
                            "description": "Path to test directory (optional)",
                        }
                    },
                    "required": ["content"],
                },
            ),
            types.Tool(
                name="analyze_python_package",
                description="Comprehensive package/folder analysis for refactoring opportunities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "package_path": {
                            "type": "string",
                            "description": "Path to Python package/folder to analyze",
                        },
                        "package_name": {
                            "type": "string",
                            "description": "Name of the package (optional, will be inferred from path)",
                        },
                    },
                    "required": ["package_path"],
                },
            ),
            types.Tool(
                name="get_package_metrics",
                description="Get aggregated metrics for a Python package",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "package_path": {
                            "type": "string",
                            "description": "Path to Python package/folder",
                        },
                        "package_name": {
                            "type": "string",
                            "description": "Name of the package (optional)",
                        },
                    },
                    "required": ["package_path"],
                },
            ),
            types.Tool(
                name="find_package_issues",
                description="Identify package-level refactoring opportunities and structural issues",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "package_path": {
                            "type": "string",
                            "description": "Path to Python package/folder",
                        },
                        "issue_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific types of issues to look for (optional): scattered_functionality, god_package, circular_dependency, etc.",
                        },
                    },
                    "required": ["package_path"],
                },
            ),
            types.Tool(
                name="analyze_security_and_patterns",
                description="Comprehensive security scanning and modern Python patterns analysis",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Python file to analyze",
                        },
                        "content": {
                            "type": "string",
                            "description": "Python file content to analyze",
                        },
                        "include_dependency_scan": {
                            "type": "boolean",
                            "description": "Include dependency vulnerability scanning (default: true)",
                            "default": True
                        },
                        "include_security_scan": {
                            "type": "boolean", 
                            "description": "Include code security vulnerability scanning (default: true)",
                            "default": True
                        },
                        "include_modernization": {
                            "type": "boolean",
                            "description": "Include modern Python pattern suggestions (default: true)",
                            "default": True
                        },
                    },
                    "required": ["content"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls for refactoring analysis"""

        try:
            analyzer = EnhancedRefactoringAnalyzer()
            advanced_features = AdvancedFeatures()

            if name == "analyze_python_file":
                file_path = arguments.get("file_path", "unknown.py")
                content = arguments["content"]

                guidance = analyzer.analyze_file(file_path, content)

                result = {
                    "analysis_summary": _create_analysis_summary(guidance),
                    "refactoring_guidance": [g.to_dict() for g in guidance],
                    "tools_used": {
                        "rope": True,
                        "radon": True,
                        "vulture": True,
                        "pyrefly": True,
                        "mccabe": True,
                        "complexipy": True,
                        "structure_analysis": True,
                        "ast_patterns": True,
                    },
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "find_long_functions":
                content = arguments["content"]
                line_threshold = arguments.get("line_threshold", 20)

                try:
                    tree = ast.parse(content)
                    long_functions = []

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if hasattr(node, "end_lineno") and node.end_lineno:
                                length = node.end_lineno - node.lineno + 1
                                if length >= line_threshold:
                                    long_functions.append(
                                        {
                                            "name": node.name,
                                            "start_line": node.lineno,
                                            "end_line": node.end_lineno,
                                            "length": length,
                                            "location": f"lines {node.lineno}-{node.end_lineno}",
                                        }
                                    )

                    result = {
                        "total_functions_analyzed": len(
                            [
                                n
                                for n in ast.walk(tree)
                                if isinstance(n, ast.FunctionDef)
                            ]
                        ),
                        "long_functions_found": len(long_functions),
                        "line_threshold": line_threshold,
                        "functions": long_functions,
                    }

                    return [
                        types.TextContent(
                            type="text", text=json.dumps(result, indent=2)
                        )
                    ]

                except SyntaxError as e:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps({"error": f"Syntax error: {e}"}, indent=2),
                        )
                    ]

            elif name == "get_extraction_guidance":
                content = arguments["content"]
                function_name = arguments.get("function_name")

                guidance = analyzer.analyze_file("temp.py", content)
                extraction_guidance = [
                    g for g in guidance if g.issue_type == "extract_function"
                ]

                if function_name:
                    extraction_guidance = [
                        g for g in extraction_guidance if function_name in g.location
                    ]

                result = {
                    "extraction_opportunities": len(extraction_guidance),
                    "guidance": [g.to_dict() for g in extraction_guidance],
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "analyze_test_coverage":
                source_path = arguments["source_path"]
                test_path = arguments.get("test_path")
                target_coverage = arguments.get("target_coverage", 80)

                # Analyze test coverage
                coverage_analysis = advanced_features.analyze_test_coverage(source_path, test_path, target_coverage)

                return [
                    types.TextContent(type="text", text=json.dumps(coverage_analysis, indent=2))
                ]

            elif name == "tdd_refactoring_guidance":
                content = arguments["content"]
                function_name = arguments.get("function_name")
                test_path = arguments.get("test_path")

                # Generate TDD refactoring guidance
                tdd_guidance = advanced_features.generate_tdd_refactoring_guidance(content, function_name, test_path)

                return [
                    types.TextContent(type="text", text=json.dumps(tdd_guidance, indent=2))
                ]

            elif name == "analyze_python_package":
                package_path = arguments["package_path"]
                package_name = arguments.get("package_name")

                # Initialize package analyzer
                package_analyzer = PackageAnalyzer()

                # Analyze the package
                guidance = package_analyzer.analyze_package(package_path, package_name)

                # Create comprehensive result
                result = {
                    "package_analysis": guidance.to_dict(),
                    "summary": package_analyzer.get_package_summary(guidance),
                    "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "tools_used": {
                        "dependency_analyzer": True,
                        "cohesion_analyzer": True,
                        "coupling_analyzer": True,
                        "structure_analyzer": True,
                        "radon_metrics": True,
                        "vulture_dead_code": True
                    }
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "get_package_metrics":
                package_path = arguments["package_path"]
                package_name = arguments.get("package_name")

                # Initialize package analyzer
                package_analyzer = PackageAnalyzer()

                # Analyze the package to get metrics
                guidance = package_analyzer.analyze_package(package_path, package_name)

                # Extract just the metrics
                result = {
                    "package_name": guidance.package_name,
                    "package_path": guidance.package_path,
                    "metrics": guidance.metrics.to_dict(),
                    "cohesion_metrics": guidance.cohesion_metrics.to_dict(),
                    "coupling_metrics": guidance.coupling_metrics.to_dict(),
                    "overall_health": {
                        "score": guidance.overall_health_score,
                        "rating": guidance.maintainability_rating
                    },
                    "dependency_stats": {
                        "total_dependencies": len(guidance.dependencies),
                        "circular_dependencies": len(guidance.circular_dependencies),
                        "local_dependencies": len([d for d in guidance.dependencies if d.import_type == "local"]),
                        "third_party_dependencies": len([d for d in guidance.dependencies if d.import_type == "third_party"]),
                        "standard_dependencies": len([d for d in guidance.dependencies if d.import_type == "standard"])
                    }
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "find_package_issues":
                package_path = arguments["package_path"]
                issue_types = arguments.get("issue_types", [])

                # Initialize package analyzer
                package_analyzer = PackageAnalyzer()

                # Analyze the package
                guidance = package_analyzer.analyze_package(package_path)

                # Filter issues if specific types requested
                filtered_issues = guidance.structural_issues
                if issue_types:
                    filtered_issues = [
                        issue for issue in guidance.structural_issues
                        if issue.issue_type in issue_types
                    ]

                # Create focused result
                result = {
                    "package_name": guidance.package_name,
                    "package_path": guidance.package_path,
                    "issues_found": len(filtered_issues),
                    "issues_by_severity": {
                        "critical": len([i for i in filtered_issues if i.severity == "critical"]),
                        "high": len([i for i in filtered_issues if i.severity == "high"]),
                        "medium": len([i for i in filtered_issues if i.severity == "medium"]),
                        "low": len([i for i in filtered_issues if i.severity == "low"])
                    },
                    "structural_issues": [issue.to_dict() for issue in filtered_issues],
                    "reorganization_suggestions": [
                        suggestion.to_dict() for suggestion in guidance.reorganization_suggestions
                    ],
                    "circular_dependencies": guidance.circular_dependencies,
                    "immediate_actions": guidance.high_priority_actions[:5],  # Top 5 priority actions
                    "tools_used": ["DependencyAnalyzer", "CohesionAnalyzer", "CouplingAnalyzer", "StructureAnalyzer"]
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "analyze_security_and_patterns":
                file_path = arguments.get("file_path", "unknown.py")
                content = arguments["content"]
                include_dependency_scan = arguments.get("include_dependency_scan", True)
                include_security_scan = arguments.get("include_security_scan", True) 
                include_modernization = arguments.get("include_modernization", True)

                # Initialize the unified security and patterns analyzer
                security_patterns_analyzer = SecurityAndPatternsAnalyzer()

                # Run the comprehensive analysis
                guidance = security_patterns_analyzer.analyze(content, file_path)

                # Get analysis summary
                analysis_summary = security_patterns_analyzer.get_analysis_summary(guidance)

                # Filter results based on user preferences
                filtered_guidance = guidance
                if not include_dependency_scan:
                    filtered_guidance = [g for g in filtered_guidance if 'dependency' not in g.issue_type]
                if not include_security_scan:
                    filtered_guidance = [g for g in filtered_guidance if 'security_vulnerability' != g.issue_type]
                if not include_modernization:
                    filtered_guidance = [g for g in filtered_guidance if 'modernization' not in g.issue_type]

                # Create comprehensive result
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

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            else:
                return [
                    types.TextContent(
                        type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
                    )
                ]

        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"Analysis failed: {str(e)}"}),
                )
            ]

    async def main() -> None:
        """MCP server main function"""
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options()
            )

else:
    print("MCP not available. Running in standalone mode for testing.")
    
    # Mock types for testing when MCP is not available
    class MockTypes:
        class TextContent:
            def __init__(self, type, text):
                self.type = type
                self.text = text
    
    types = MockTypes()

    async def handle_call_tool(name: str, arguments: dict) -> list:
        """Mock MCP tool handler for testing when MCP is not available"""
        try:
            analyzer = EnhancedRefactoringAnalyzer()
            advanced_features = AdvancedFeatures()

            if name == "analyze_python_file":
                file_path = arguments.get("file_path", "unknown.py")
                content = arguments["content"]

                guidance = analyzer.analyze_file(file_path, content)

                result = {
                    "analysis_summary": _create_analysis_summary(guidance),
                    "refactoring_guidance": [g.to_dict() for g in guidance],
                    "tools_used": {
                        "rope": True,
                        "radon": True,
                        "vulture": True,
                        "pyrefly": True,
                        "mccabe": True,
                        "complexipy": True,
                        "structure_analysis": True,
                        "ast_patterns": True,
                    },
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            elif name == "analyze_security_and_patterns":
                file_path = arguments.get("file_path", "unknown.py")
                content = arguments["content"]
                include_dependency_scan = arguments.get("include_dependency_scan", True)
                include_security_scan = arguments.get("include_security_scan", True) 
                include_modernization = arguments.get("include_modernization", True)

                # Initialize the unified security and patterns analyzer
                security_patterns_analyzer = SecurityAndPatternsAnalyzer()

                # Run the comprehensive analysis
                guidance = security_patterns_analyzer.analyze(content, file_path)

                # Get analysis summary
                analysis_summary = security_patterns_analyzer.get_analysis_summary(guidance)

                # Filter results based on user preferences
                filtered_guidance = guidance
                if not include_dependency_scan:
                    filtered_guidance = [g for g in filtered_guidance if 'dependency' not in g.issue_type]
                if not include_security_scan:
                    filtered_guidance = [g for g in filtered_guidance if 'security_vulnerability' != g.issue_type]
                if not include_modernization:
                    filtered_guidance = [g for g in filtered_guidance if 'modernization' not in g.issue_type]

                # Create comprehensive result
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

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            else:
                return [
                    types.TextContent(
                        type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
                    )
                ]

        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"Analysis failed: {str(e)}"}),
                )
            ]

    def main() -> None:
        """Standalone mode for testing without MCP"""
        if len(sys.argv) < 2:
            print("Usage: python server.py <python_file>")
            return

        file_path = sys.argv[1]
        with open(file_path, "r") as f:
            content = f.read()

        analyzer = EnhancedRefactoringAnalyzer()
        guidance = analyzer.analyze_file(file_path, content)

        print("\n=== REFACTORING ANALYSIS ===")
        for i, g in enumerate(guidance, 1):
            print(f"\n{i}. {g.issue_type.upper()} [{g.severity}]")
            print(f"   Location: {g.location}")
            print(f"   Description: {g.description}")
            print("   Steps:")
            for step in g.precise_steps[:5]:  # Show first 5 steps
                print(f"     {step}")
            if len(g.precise_steps) > 5:
                print(f"     ... and {len(g.precise_steps) - 5} more steps")


if __name__ == "__main__":
    if MCP_AVAILABLE:
        import asyncio
        asyncio.run(main())
    else:
        main()