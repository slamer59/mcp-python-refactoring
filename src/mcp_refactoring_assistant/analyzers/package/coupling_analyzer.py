#!/usr/bin/env python3
"""
Coupling analyzer for package-level analysis
"""

import ast
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from ...models.package_models import CouplingMetrics, DependencyGraph


class CouplingAnalyzer:
    """Analyzes coupling between modules and packages"""
    
    def __init__(self):
        self.name = "CouplingAnalyzer"
    
    def analyze_package_coupling(self, package_path: str, package_name: str, 
                               dependency_graph: DependencyGraph) -> CouplingMetrics:
        """
        Analyze coupling metrics for a package
        
        Args:
            package_path: Path to the package directory
            package_name: Name of the package
            dependency_graph: Pre-computed dependency graph
            
        Returns:
            CouplingMetrics containing coupling analysis results
        """
        package_path = Path(package_path)
        
        # Calculate basic coupling metrics
        afferent_coupling = self._calculate_afferent_coupling(dependency_graph, package_name)
        efferent_coupling = self._calculate_efferent_coupling(dependency_graph, package_name)
        
        # Calculate derived metrics
        instability = self._calculate_instability(afferent_coupling, efferent_coupling)
        abstractness = self._calculate_abstractness(package_path)
        distance_from_main = self._calculate_distance_from_main_sequence(instability, abstractness)
        
        # Find tightly coupled modules
        tightly_coupled = self._find_tightly_coupled_modules(dependency_graph)
        
        return CouplingMetrics(
            package_name=package_name,
            afferent_coupling=afferent_coupling,
            efferent_coupling=efferent_coupling,
            instability=instability,
            abstractness=abstractness,
            distance_from_main=distance_from_main,
            tightly_coupled_modules=tightly_coupled
        )
    
    def _calculate_afferent_coupling(self, graph: DependencyGraph, package_name: str) -> int:
        """
        Calculate afferent coupling (Ca) - number of classes outside the package 
        that depend on classes inside the package
        """
        afferent_count = 0
        package_modules = {node for node in graph.nodes if node.startswith(package_name)}
        
        # Count dependencies FROM external modules TO package modules
        for edge in graph.edges:
            if (edge.target_module in package_modules and 
                not edge.source_module.startswith(package_name) and
                edge.import_type == "local"):
                afferent_count += 1
        
        return afferent_count
    
    def _calculate_efferent_coupling(self, graph: DependencyGraph, package_name: str) -> int:
        """
        Calculate efferent coupling (Ce) - number of classes inside the package 
        that depend on classes outside the package
        """
        efferent_count = 0
        package_modules = {node for node in graph.nodes if node.startswith(package_name)}
        
        # Count dependencies FROM package modules TO external modules
        for edge in graph.edges:
            if (edge.source_module in package_modules and 
                not edge.target_module.startswith(package_name) and
                edge.import_type == "local"):
                efferent_count += 1
        
        return efferent_count
    
    def _calculate_instability(self, afferent: int, efferent: int) -> float:
        """
        Calculate instability metric (I) = Ce / (Ca + Ce)
        Range: 0 (stable) to 1 (unstable)
        """
        total_coupling = afferent + efferent
        return efferent / total_coupling if total_coupling > 0 else 0.0
    
    def _calculate_abstractness(self, package_path: Path) -> float:
        """
        Calculate abstractness metric (A) = abstract classes / total classes
        Range: 0 (concrete) to 1 (abstract)
        """
        total_classes = 0
        abstract_classes = 0
        
        # Find all Python files
        python_files = list(package_path.rglob("*.py"))
        python_files = [f for f in python_files if "__pycache__" not in str(f)]
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        total_classes += 1
                        
                        # Check if class is abstract (has ABC or abstract methods)
                        if self._is_abstract_class(node):
                            abstract_classes += 1
                            
            except Exception as e:
                print(f"Warning: Could not analyze {file_path}: {e}")
                continue
        
        return abstract_classes / total_classes if total_classes > 0 else 0.0
    
    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if a class is abstract"""
        # Check if inherits from ABC
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id in ('ABC', 'AbstractBaseClass'):
                return True
            elif isinstance(base, ast.Attribute) and base.attr in ('ABC', 'AbstractBaseClass'):
                return True
        
        # Check for abstract methods
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == 'abstractmethod':
                        return True
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == 'abstractmethod':
                        return True
        
        return False
    
    def _calculate_distance_from_main_sequence(self, instability: float, abstractness: float) -> float:
        """
        Calculate distance from main sequence (D) = |A + I - 1|
        Range: 0 (on main sequence) to 1 (maximum distance)
        """
        return abs(abstractness + instability - 1.0)
    
    def _find_tightly_coupled_modules(self, graph: DependencyGraph) -> List[Dict[str, Any]]:
        """Find modules that are tightly coupled"""
        tightly_coupled = []
        
        # Count dependencies between each pair of modules
        module_dependencies = defaultdict(lambda: defaultdict(int))
        
        for edge in graph.edges:
            if edge.import_type == "local":  # Only consider local dependencies
                module_dependencies[edge.source_module][edge.target_module] += 1
        
        # Find bidirectional dependencies (strong indicator of tight coupling)
        for module1 in module_dependencies:
            for module2 in module_dependencies[module1]:
                if module2 in module_dependencies and module1 in module_dependencies[module2]:
                    # Bidirectional dependency found
                    coupling_strength = (module_dependencies[module1][module2] + 
                                       module_dependencies[module2][module1])
                    
                    tightly_coupled.append({
                        "modules": [module1, module2],
                        "coupling_type": "bidirectional",
                        "strength": coupling_strength,
                        "description": f"Bidirectional dependency between {module1} and {module2}",
                        "suggestion": "Consider introducing an interface or mediator pattern"
                    })
        
        # Find modules with high fan-out (depend on many others)
        for module, dependencies in module_dependencies.items():
            if len(dependencies) > 5:  # Threshold for high coupling
                tightly_coupled.append({
                    "modules": [module],
                    "coupling_type": "high_fan_out",
                    "strength": len(dependencies),
                    "description": f"{module} depends on {len(dependencies)} other modules",
                    "suggestion": "Consider breaking down this module or using dependency injection"
                })
        
        # Find modules with high fan-in (many others depend on them)
        fan_in_count = defaultdict(int)
        for module_deps in module_dependencies.values():
            for target in module_deps:
                fan_in_count[target] += 1
        
        for module, fan_in in fan_in_count.items():
            if fan_in > 5:  # Threshold for high coupling
                tightly_coupled.append({
                    "modules": [module],
                    "coupling_type": "high_fan_in",
                    "strength": fan_in,
                    "description": f"{module} is depended upon by {fan_in} other modules",
                    "suggestion": "Consider if this module has too many responsibilities"
                })
        
        # Detect data coupling (modules that share complex data structures)
        data_coupling = self._detect_data_coupling(graph)
        tightly_coupled.extend(data_coupling)
        
        return tightly_coupled
    
    def _detect_data_coupling(self, graph: DependencyGraph) -> List[Dict[str, Any]]:
        """Detect data coupling between modules"""
        data_coupling = []
        
        # This is a simplified detection - in practice, you'd need to analyze
        # the actual data structures being passed between modules
        
        # Look for modules that have multiple types of dependencies
        module_dependency_types = defaultdict(set)
        
        for edge in graph.edges:
            if edge.import_type == "local":
                # Analyze the import statement to infer coupling type
                if "class" in edge.import_statement.lower():
                    module_dependency_types[f"{edge.source_module}->{edge.target_module}"].add("class")
                if "function" in edge.import_statement.lower():
                    module_dependency_types[f"{edge.source_module}->{edge.target_module}"].add("function")
                if any(keyword in edge.import_statement.lower() 
                       for keyword in ["data", "config", "settings", "constant"]):
                    module_dependency_types[f"{edge.source_module}->{edge.target_module}"].add("data")
        
        # Find modules with multiple types of coupling
        for modules, coupling_types in module_dependency_types.items():
            if len(coupling_types) > 1:
                source, target = modules.split("->")
                data_coupling.append({
                    "modules": [source, target],
                    "coupling_type": "data_coupling",
                    "strength": len(coupling_types),
                    "description": f"Multiple coupling types between {source} and {target}: {', '.join(coupling_types)}",
                    "suggestion": "Consider using interfaces or data transfer objects to reduce coupling"
                })
        
        return data_coupling
    
    def analyze_coupling_evolution(self, current_graph: DependencyGraph, 
                                 previous_graph: DependencyGraph = None) -> Dict[str, Any]:
        """Analyze how coupling has evolved (if previous graph is available)"""
        if not previous_graph:
            return {"message": "No previous graph available for evolution analysis"}
        
        evolution_analysis = {
            "new_dependencies": [],
            "removed_dependencies": [],
            "coupling_trend": "stable"
        }
        
        # Find new dependencies
        current_edges = {(edge.source_module, edge.target_module) for edge in current_graph.edges}
        previous_edges = {(edge.source_module, edge.target_module) for edge in previous_graph.edges}
        
        new_deps = current_edges - previous_edges
        removed_deps = previous_edges - current_edges
        
        evolution_analysis["new_dependencies"] = list(new_deps)
        evolution_analysis["removed_dependencies"] = list(removed_deps)
        
        # Determine coupling trend
        if len(new_deps) > len(removed_deps) * 1.2:
            evolution_analysis["coupling_trend"] = "increasing"
        elif len(removed_deps) > len(new_deps) * 1.2:
            evolution_analysis["coupling_trend"] = "decreasing"
        else:
            evolution_analysis["coupling_trend"] = "stable"
        
        return evolution_analysis