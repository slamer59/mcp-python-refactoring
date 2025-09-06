#!/usr/bin/env python3
"""
Dependency analyzer for package-level analysis
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import importlib.util

from ...models.package_models import ModuleDependency, DependencyGraph


class DependencyAnalyzer:
    """Analyzes dependencies between modules in a package"""
    
    def __init__(self):
        self.name = "DependencyAnalyzer"
    
    def analyze_package_dependencies(self, package_path: str) -> DependencyGraph:
        """
        Analyze all dependencies within a package
        
        Args:
            package_path: Path to the package directory
            
        Returns:
            DependencyGraph containing all dependency information
        """
        package_path = Path(package_path)
        if not package_path.exists():
            raise ValueError(f"Package path does not exist: {package_path}")
        
        # Find all Python files in the package
        python_files = self._find_python_files(package_path)
        
        # Extract dependencies from each file
        all_dependencies = []
        module_names = set()
        
        for file_path in python_files:
            module_name = self._get_module_name(file_path, package_path)
            module_names.add(module_name)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_dependencies = self._extract_dependencies(content, module_name, str(file_path))
                all_dependencies.extend(file_dependencies)
                
            except Exception as e:
                print(f"Warning: Could not analyze {file_path}: {e}")
                continue
        
        # Build dependency graph
        graph = DependencyGraph(
            nodes=list(module_names),
            edges=all_dependencies
        )
        
        # Detect cycles
        graph.cycles = self._detect_cycles(graph)
        graph.strongly_connected_components = self._find_strongly_connected_components(graph)
        
        return graph
    
    def _find_python_files(self, package_path: Path) -> List[Path]:
        """Find all Python files in the package recursively"""
        python_files = []
        
        for file_path in package_path.rglob("*.py"):
            # Skip __pycache__ directories and test files for now
            if "__pycache__" not in str(file_path) and not file_path.name.startswith("test_"):
                python_files.append(file_path)
        
        return python_files
    
    def _get_module_name(self, file_path: Path, package_root: Path) -> str:
        """Convert file path to module name"""
        try:
            relative_path = file_path.relative_to(package_root)
            # Remove .py extension and convert path separators to dots
            module_parts = list(relative_path.parts[:-1])  # Exclude filename
            if relative_path.stem != "__init__":
                module_parts.append(relative_path.stem)
            
            return ".".join(module_parts) if module_parts else "__main__"
        except ValueError:
            # If file is not under package_root, use the filename
            return file_path.stem
    
    def _extract_dependencies(self, content: str, source_module: str, file_path: str) -> List[ModuleDependency]:
        """Extract all import dependencies from a file"""
        dependencies = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep = ModuleDependency(
                            source_module=source_module,
                            target_module=alias.name,
                            import_type=self._classify_import(alias.name),
                            import_statement=f"import {alias.name}",
                            line_number=node.lineno
                        )
                        dependencies.append(dep)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:  # Skip relative imports without module
                        dep = ModuleDependency(
                            source_module=source_module,
                            target_module=node.module,
                            import_type=self._classify_import(node.module),
                            import_statement=f"from {node.module} import {', '.join(alias.name for alias in node.names)}",
                            line_number=node.lineno
                        )
                        dependencies.append(dep)
        
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
        
        return dependencies
    
    def _classify_import(self, module_name: str) -> str:
        """Classify import as standard, third_party, or local"""
        # Standard library modules (simplified check)
        stdlib_modules = {
            'os', 'sys', 'json', 'ast', 'pathlib', 'typing', 'collections', 
            'itertools', 'functools', 'operator', 'datetime', 'time', 'math',
            'random', 're', 'subprocess', 'tempfile', 'shutil', 'glob',
            'abc', 'dataclasses', 'enum', 'warnings', 'logging'
        }
        
        first_part = module_name.split('.')[0]
        
        if first_part in stdlib_modules:
            return "standard"
        elif module_name.startswith('.') or not self._is_third_party_module(first_part):
            return "local"
        else:
            return "third_party"
    
    def _is_third_party_module(self, module_name: str) -> bool:
        """Check if a module is a third-party package"""
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return False
            
            # If the module is in site-packages, it's likely third-party
            if spec.origin and ('site-packages' in spec.origin or 'dist-packages' in spec.origin):
                return True
            
            return False
        except (ImportError, ValueError):
            return False
    
    def _detect_cycles(self, graph: DependencyGraph) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # Find all nodes this node depends on
            dependencies = [dep.target_module for dep in graph.edges 
                          if dep.source_module == node and dep.target_module in graph.nodes]
            
            for neighbor in dependencies:
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start_idx = path.index(neighbor)
                    cycle = path[cycle_start_idx:] + [neighbor]
                    if cycle not in cycles and len(cycle) > 2:  # Ignore self-loops
                        cycles.append(cycle)
                        # Mark edges as circular
                        for i in range(len(cycle) - 1):
                            for dep in graph.edges:
                                if dep.source_module == cycle[i] and dep.target_module == cycle[i + 1]:
                                    dep.is_circular = True
            
            rec_stack.remove(node)
        
        for node in graph.nodes:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def _find_strongly_connected_components(self, graph: DependencyGraph) -> List[List[str]]:
        """Find strongly connected components using Tarjan's algorithm"""
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        sccs = []
        
        def strongconnect(node: str) -> None:
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True
            
            # Find all nodes this node depends on
            dependencies = [dep.target_module for dep in graph.edges 
                          if dep.source_module == node and dep.target_module in graph.nodes]
            
            for neighbor in dependencies:
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif on_stack.get(neighbor, False):
                    lowlinks[node] = min(lowlinks[node], index[neighbor])
            
            # If node is a root node, pop the stack and create SCC
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break
                if len(component) > 1:  # Only include non-trivial SCCs
                    sccs.append(component)
        
        for node in graph.nodes:
            if node not in index:
                strongconnect(node)
        
        return sccs
    
    def get_dependency_statistics(self, graph: DependencyGraph) -> Dict[str, int]:
        """Get statistics about the dependency graph"""
        return {
            "total_modules": len(graph.nodes),
            "total_dependencies": len(graph.edges),
            "circular_dependencies": len(graph.cycles),
            "strongly_connected_components": len(graph.strongly_connected_components),
            "local_dependencies": len([dep for dep in graph.edges if dep.import_type == "local"]),
            "third_party_dependencies": len([dep for dep in graph.edges if dep.import_type == "third_party"]),
            "standard_library_dependencies": len([dep for dep in graph.edges if dep.import_type == "standard"])
        }