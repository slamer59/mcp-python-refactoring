#!/usr/bin/env python3
"""
Package structure analyzer for detecting organizational issues
"""

import ast
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from ...models.package_models import (
    PackageStructureIssue, 
    PackageReorganizationSuggestion,
    DependencyGraph
)


class PackageStructureAnalyzer:
    """Analyzes package structure and suggests reorganization"""
    
    def __init__(self):
        self.name = "PackageStructureAnalyzer"
    
    def analyze_package_structure(self, package_path: str, dependency_graph: DependencyGraph) -> Tuple[List[PackageStructureIssue], List[PackageReorganizationSuggestion]]:
        """
        Analyze package structure for organizational issues
        
        Args:
            package_path: Path to the package directory
            dependency_graph: Pre-computed dependency graph
            
        Returns:
            Tuple of (structural issues, reorganization suggestions)
        """
        package_path = Path(package_path)
        
        issues = []
        suggestions = []
        
        # Analyze package structure
        structure_info = self._analyze_directory_structure(package_path)
        
        # Detect various structural issues
        issues.extend(self._detect_scattered_functionality(structure_info, dependency_graph))
        issues.extend(self._detect_god_packages(structure_info))
        issues.extend(self._detect_inappropriate_intimacy(dependency_graph))
        issues.extend(self._detect_circular_dependencies(dependency_graph))
        issues.extend(self._detect_large_classes(structure_info))
        
        # Generate reorganization suggestions based on issues
        suggestions.extend(self._generate_reorganization_suggestions(issues, structure_info, dependency_graph))
        
        return issues, suggestions
    
    def _analyze_directory_structure(self, package_path: Path) -> Dict[str, Any]:
        """Analyze the directory structure and file organization"""
        structure_info = {
            "total_files": 0,
            "directories": [],
            "files_by_directory": defaultdict(list),
            "file_sizes": {},
            "module_info": [],
            "naming_patterns": defaultdict(list)
        }
        
        # Traverse directory structure
        for item in package_path.rglob("*"):
            if item.is_file() and item.suffix == ".py" and "__pycache__" not in str(item):
                structure_info["total_files"] += 1
                
                # Get relative path info
                relative_path = item.relative_to(package_path)
                directory = str(relative_path.parent) if relative_path.parent != Path(".") else "root"
                
                structure_info["files_by_directory"][directory].append(str(item))
                structure_info["file_sizes"][str(item)] = item.stat().st_size
                
                # Analyze file content
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    module_analysis = self._analyze_module_content(content, str(item))
                    module_analysis["file_path"] = str(item)
                    module_analysis["directory"] = directory
                    structure_info["module_info"].append(module_analysis)
                    
                    # Track naming patterns
                    structure_info["naming_patterns"][item.stem.split("_")[0]].append(str(item))
                    
                except Exception as e:
                    print(f"Warning: Could not analyze {item}: {e}")
        
        # Collect directory information
        for directory in package_path.rglob("*"):
            if directory.is_dir() and "__pycache__" not in str(directory):
                structure_info["directories"].append(str(directory))
        
        return structure_info
    
    def _analyze_module_content(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze the content of a single module"""
        analysis = {
            "functions": [],
            "classes": [],
            "lines_of_code": len(content.splitlines()),
            "imports": [],
            "complexity_indicators": []
        }
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "length": getattr(node, 'end_lineno', node.lineno) - node.lineno + 1,
                        "parameters": len(node.args.args),
                        "is_private": node.name.startswith("_"),
                        "complexity": self._estimate_function_complexity(node)
                    }
                    analysis["functions"].append(func_info)
                
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "length": getattr(node, 'end_lineno', node.lineno) - node.lineno + 1,
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
                        "attributes": self._count_class_attributes(node),
                        "is_private": node.name.startswith("_")
                    }
                    analysis["classes"].append(class_info)
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            analysis["imports"].append(alias.name)
                    else:
                        if node.module:
                            analysis["imports"].append(node.module)
        
        except SyntaxError:
            pass  # Skip files with syntax errors
        
        return analysis
    
    def _estimate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """Estimate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity
        
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    
    def _count_class_attributes(self, class_node: ast.ClassDef) -> int:
        """Count the number of class attributes"""
        attributes = set()
        
        for node in ast.walk(class_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                        attributes.add(target.attr)
        
        return len(attributes)
    
    def _detect_scattered_functionality(self, structure_info: Dict[str, Any], 
                                      dependency_graph: DependencyGraph) -> List[PackageStructureIssue]:
        """Detect scattered functionality across multiple modules"""
        issues = []
        
        # Group functions/classes by naming patterns
        function_groups = defaultdict(list)
        class_groups = defaultdict(list)
        
        for module in structure_info["module_info"]:
            for func in module["functions"]:
                # Group by prefix (e.g., handle_, process_, validate_)
                prefix = func["name"].split("_")[0]
                function_groups[prefix].append({
                    "function": func,
                    "module": module["file_path"]
                })
            
            for cls in module["classes"]:
                # Group by suffix (e.g., Handler, Manager, Service)
                if "_" in cls["name"]:
                    suffix = cls["name"].split("_")[-1]
                else:
                    # CamelCase - extract suffix
                    import re
                    words = re.findall(r'[A-Z][a-z]*', cls["name"])
                    suffix = words[-1] if words else cls["name"]
                
                class_groups[suffix].append({
                    "class": cls,
                    "module": module["file_path"]
                })
        
        # Find scattered functionality
        for prefix, functions in function_groups.items():
            if len(functions) > 3 and len(set(f["module"] for f in functions)) > 2:
                affected_modules = list(set(f["module"] for f in functions))
                issues.append(PackageStructureIssue(
                    issue_type="scattered_functionality",
                    severity="medium",
                    affected_modules=affected_modules,
                    description=f"Functions with prefix '{prefix}_*' are scattered across {len(affected_modules)} modules",
                    suggested_reorganization=f"Consider grouping {prefix}_* functions in a dedicated module"
                ))
        
        for suffix, classes in class_groups.items():
            if len(classes) > 2 and len(set(c["module"] for c in classes)) > 1:
                affected_modules = list(set(c["module"] for c in classes))
                issues.append(PackageStructureIssue(
                    issue_type="scattered_functionality",
                    severity="medium",
                    affected_modules=affected_modules,
                    description=f"Classes ending with '{suffix}' are scattered across {len(affected_modules)} modules",
                    suggested_reorganization=f"Consider grouping {suffix} classes in a dedicated module or package"
                ))
        
        return issues
    
    def _detect_god_packages(self, structure_info: Dict[str, Any]) -> List[PackageStructureIssue]:
        """Detect packages/modules that are too large or have too many responsibilities"""
        issues = []
        
        # Check for modules that are too large
        for module in structure_info["module_info"]:
            total_entities = len(module["functions"]) + len(module["classes"])
            
            if total_entities > 20:  # Threshold for too many entities
                issues.append(PackageStructureIssue(
                    issue_type="god_package",
                    severity="high" if total_entities > 30 else "medium",
                    affected_modules=[module["file_path"]],
                    description=f"Module has {total_entities} functions/classes, indicating too many responsibilities",
                    suggested_reorganization="Consider splitting this module into smaller, more focused modules"
                ))
            
            if module["lines_of_code"] > 1000:  # Threshold for too many lines
                issues.append(PackageStructureIssue(
                    issue_type="god_package",
                    severity="high" if module["lines_of_code"] > 2000 else "medium",
                    affected_modules=[module["file_path"]],
                    description=f"Module has {module['lines_of_code']} lines of code",
                    suggested_reorganization="Consider breaking this large module into smaller modules"
                ))
        
        # Check for directories with too many files
        for directory, files in structure_info["files_by_directory"].items():
            if len(files) > 15:  # Threshold for too many files in one directory
                issues.append(PackageStructureIssue(
                    issue_type="god_package",
                    severity="medium",
                    affected_modules=files,
                    description=f"Directory '{directory}' contains {len(files)} Python files",
                    suggested_reorganization="Consider organizing files into subdirectories by functionality"
                ))
        
        return issues
    
    def _detect_inappropriate_intimacy(self, dependency_graph: DependencyGraph) -> List[PackageStructureIssue]:
        """Detect modules that are too tightly coupled (inappropriate intimacy)"""
        issues = []
        
        # Count bidirectional dependencies
        bidirectional_deps = defaultdict(int)
        
        for edge1 in dependency_graph.edges:
            for edge2 in dependency_graph.edges:
                if (edge1.source_module == edge2.target_module and 
                    edge1.target_module == edge2.source_module and
                    edge1.import_type == "local" and edge2.import_type == "local"):
                    modules = tuple(sorted([edge1.source_module, edge1.target_module]))
                    bidirectional_deps[modules] += 1
        
        # Report inappropriate intimacy
        for (module1, module2), count in bidirectional_deps.items():
            if count > 1:  # Multiple bidirectional dependencies
                issues.append(PackageStructureIssue(
                    issue_type="inappropriate_intimacy",
                    severity="high" if count > 3 else "medium",
                    affected_modules=[module1, module2],
                    description=f"Modules have {count} bidirectional dependencies, indicating tight coupling",
                    suggested_reorganization="Consider merging these modules or introducing an interface/mediator"
                ))
        
        return issues
    
    def _detect_circular_dependencies(self, dependency_graph: DependencyGraph) -> List[PackageStructureIssue]:
        """Detect circular dependencies"""
        issues = []
        
        for cycle in dependency_graph.cycles:
            if len(cycle) > 2:  # Ignore self-references
                issues.append(PackageStructureIssue(
                    issue_type="circular_dependency",
                    severity="critical" if len(cycle) > 4 else "high",
                    affected_modules=cycle[:-1],  # Remove duplicate at end
                    description=f"Circular dependency detected: {' -> '.join(cycle)}",
                    suggested_reorganization="Break the circular dependency by introducing interfaces or moving shared code"
                ))
        
        return issues
    
    def _detect_large_classes(self, structure_info: Dict[str, Any]) -> List[PackageStructureIssue]:
        """Detect classes that are too large"""
        issues = []
        
        for module in structure_info["module_info"]:
            for cls in module["classes"]:
                if cls["methods"] > 15:  # Threshold for too many methods
                    issues.append(PackageStructureIssue(
                        issue_type="large_class",
                        severity="high" if cls["methods"] > 25 else "medium",
                        affected_modules=[module["file_path"]],
                        description=f"Class '{cls['name']}' has {cls['methods']} methods",
                        suggested_reorganization=f"Consider breaking down class '{cls['name']}' using composition or inheritance"
                    ))
                
                if cls["length"] > 200:  # Threshold for too many lines
                    issues.append(PackageStructureIssue(
                        issue_type="large_class",
                        severity="high" if cls["length"] > 400 else "medium",
                        affected_modules=[module["file_path"]],
                        description=f"Class '{cls['name']}' has {cls['length']} lines of code",
                        suggested_reorganization=f"Consider extracting functionality from class '{cls['name']}' into separate classes"
                    ))
        
        return issues
    
    def _generate_reorganization_suggestions(self, issues: List[PackageStructureIssue], 
                                           structure_info: Dict[str, Any],
                                           dependency_graph: DependencyGraph) -> List[PackageReorganizationSuggestion]:
        """Generate specific reorganization suggestions based on detected issues"""
        suggestions = []
        
        # Group issues by type for better suggestions
        issues_by_type = defaultdict(list)
        for issue in issues:
            issues_by_type[issue.issue_type].append(issue)
        
        # Suggestions for scattered functionality
        for issue in issues_by_type["scattered_functionality"]:
            suggestion = PackageReorganizationSuggestion(
                suggestion_type="extract_package",
                priority="medium",
                affected_files=issue.affected_modules,
                rationale=issue.description,
                steps=[
                    f"Create a new module for related functionality",
                    f"Move related functions/classes to the new module", 
                    f"Update import statements in affected modules",
                    f"Run tests to ensure functionality is preserved"
                ],
                estimated_effort="medium",
                breaking_changes=True,
                affected_imports=self._find_affected_imports(issue.affected_modules, dependency_graph)
            )
            suggestions.append(suggestion)
        
        # Suggestions for god packages
        for issue in issues_by_type["god_package"]:
            suggestion = PackageReorganizationSuggestion(
                suggestion_type="split_module",
                priority="high" if issue.severity == "high" else "medium",
                affected_files=issue.affected_modules,
                rationale=issue.description,
                steps=[
                    f"Identify logical groupings within the large module",
                    f"Create separate modules for each logical group",
                    f"Move functions/classes to appropriate modules",
                    f"Create __init__.py to maintain public interface",
                    f"Update import statements and run tests"
                ],
                estimated_effort="high",
                breaking_changes=True,
                affected_imports=self._find_affected_imports(issue.affected_modules, dependency_graph)
            )
            suggestions.append(suggestion)
        
        # Suggestions for inappropriate intimacy
        for issue in issues_by_type["inappropriate_intimacy"]:
            suggestion = PackageReorganizationSuggestion(
                suggestion_type="merge_packages",
                priority="high",
                affected_files=issue.affected_modules,
                rationale=issue.description,
                steps=[
                    f"Evaluate if the tightly coupled modules should be merged",
                    f"If merging is appropriate, combine the modules",
                    f"If not, introduce interfaces or abstract base classes",
                    f"Refactor to reduce direct dependencies",
                    f"Update tests and documentation"
                ],
                estimated_effort="high",
                breaking_changes=True,
                affected_imports=self._find_affected_imports(issue.affected_modules, dependency_graph)
            )
            suggestions.append(suggestion)
        
        # Suggestions for circular dependencies
        for issue in issues_by_type["circular_dependency"]:
            suggestion = PackageReorganizationSuggestion(
                suggestion_type="introduce_layer",
                priority="critical",
                affected_files=issue.affected_modules,
                rationale=issue.description,
                steps=[
                    f"Identify the root cause of the circular dependency",
                    f"Extract shared interfaces or base classes",
                    f"Create a common module for shared abstractions",
                    f"Refactor modules to depend on abstractions",
                    f"Ensure the circular dependency is broken",
                    f"Run comprehensive tests"
                ],
                estimated_effort="high",
                breaking_changes=True,
                affected_imports=self._find_affected_imports(issue.affected_modules, dependency_graph)
            )
            suggestions.append(suggestion)
        
        # Suggestions for large classes
        for issue in issues_by_type["large_class"]:
            suggestion = PackageReorganizationSuggestion(
                suggestion_type="extract_package",
                priority="medium",
                affected_files=issue.affected_modules,
                rationale=issue.description,
                steps=[
                    f"Identify cohesive groups of methods in the large class",
                    f"Extract groups into separate classes",
                    f"Use composition to maintain relationships",
                    f"Update existing code to use the new structure",
                    f"Ensure all functionality is preserved"
                ],
                estimated_effort="medium",
                breaking_changes=False,
                affected_imports=[]
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _find_affected_imports(self, affected_modules: List[str], 
                              dependency_graph: DependencyGraph) -> List[str]:
        """Find import statements that would be affected by reorganization"""
        affected_imports = []
        
        for edge in dependency_graph.edges:
            if (edge.source_module in affected_modules or 
                edge.target_module in affected_modules):
                affected_imports.append(edge.import_statement)
        
        return list(set(affected_imports))  # Remove duplicates