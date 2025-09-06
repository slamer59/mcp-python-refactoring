#!/usr/bin/env python3
"""
Cohesion analyzer for package-level analysis
"""

import ast
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from ...models.package_models import CohesionMetrics


class CohesionAnalyzer:
    """Analyzes cohesion within packages and modules"""
    
    def __init__(self):
        self.name = "CohesionAnalyzer"
    
    def analyze_package_cohesion(self, package_path: str, package_name: str) -> CohesionMetrics:
        """
        Analyze cohesion metrics for a package
        
        Args:
            package_path: Path to the package directory
            package_name: Name of the package
            
        Returns:
            CohesionMetrics containing cohesion analysis results
        """
        package_path = Path(package_path)
        
        # Initialize metrics
        metrics = CohesionMetrics(package_name=package_name)
        
        # Find all Python files
        python_files = list(package_path.rglob("*.py"))
        python_files = [f for f in python_files if "__pycache__" not in str(f)]
        
        # Analyze each file for cohesion
        all_classes = []
        all_functions = []
        shared_data = defaultdict(set)  # Track shared data usage
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_analysis = self._analyze_file_cohesion(content, str(file_path))
                all_classes.extend(file_analysis["classes"])
                all_functions.extend(file_analysis["functions"])
                
                # Track shared data usage
                for data_item, users in file_analysis["shared_data"].items():
                    shared_data[data_item].update(users)
                    
            except Exception as e:
                print(f"Warning: Could not analyze {file_path}: {e}")
                continue
        
        # Calculate LCOM (Lack of Cohesion of Methods) for classes
        metrics.lcom_score = self._calculate_lcom_score(all_classes)
        
        # Calculate different types of cohesion
        metrics.functional_cohesion = self._calculate_functional_cohesion(all_functions, shared_data)
        metrics.sequential_cohesion = self._calculate_sequential_cohesion(all_functions)
        metrics.communicational_cohesion = self._calculate_communicational_cohesion(all_functions, shared_data)
        
        # Find related components that should be grouped
        metrics.related_components = self._find_related_components(all_functions, all_classes, shared_data)
        
        return metrics
    
    def _analyze_file_cohesion(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze cohesion within a single file"""
        analysis = {
            "classes": [],
            "functions": [],
            "shared_data": defaultdict(set)
        }
        
        try:
            tree = ast.parse(content)
            
            # Analyze classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_analysis = self._analyze_class_cohesion(node, content)
                    class_analysis["file"] = file_path
                    analysis["classes"].append(class_analysis)
                
                elif isinstance(node, ast.FunctionDef):
                    if not self._is_method(node, tree):  # Only standalone functions
                        func_analysis = self._analyze_function_cohesion(node, content)
                        func_analysis["file"] = file_path
                        analysis["functions"].append(func_analysis)
            
            # Track shared data (variables, imports, etc.)
            analysis["shared_data"] = self._find_shared_data_usage(tree, file_path)
            
        except SyntaxError:
            pass  # Skip files with syntax errors
        
        return analysis
    
    def _analyze_class_cohesion(self, class_node: ast.ClassDef, content: str) -> Dict[str, Any]:
        """Analyze cohesion within a class"""
        methods = []
        attributes = set()
        method_attribute_usage = {}
        
        # Find all methods and their attribute usage
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "attributes_used": set(),
                    "calls_methods": set()
                }
                
                # Find attribute usage (self.attribute)
                for child in ast.walk(node):
                    if isinstance(child, ast.Attribute):
                        if isinstance(child.value, ast.Name) and child.value.id == "self":
                            method_info["attributes_used"].add(child.attr)
                            attributes.add(child.attr)
                    elif isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute) and isinstance(child.func.value, ast.Name) and child.func.value.id == "self":
                            method_info["calls_methods"].add(child.func.attr)
                
                methods.append(method_info)
                method_attribute_usage[node.name] = method_info["attributes_used"]
        
        return {
            "name": class_node.name,
            "line": class_node.lineno,
            "methods": methods,
            "attributes": attributes,
            "method_attribute_usage": method_attribute_usage
        }
    
    def _analyze_function_cohesion(self, func_node: ast.FunctionDef, content: str) -> Dict[str, Any]:
        """Analyze cohesion-related aspects of a function"""
        return {
            "name": func_node.name,
            "line": func_node.lineno,
            "parameters": [arg.arg for arg in func_node.args.args],
            "calls_functions": self._find_function_calls(func_node),
            "uses_globals": self._find_global_usage(func_node)
        }
    
    def _find_function_calls(self, func_node: ast.FunctionDef) -> Set[str]:
        """Find all function calls within a function"""
        calls = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return calls
    
    def _find_global_usage(self, func_node: ast.FunctionDef) -> Set[str]:
        """Find global variables used in a function"""
        globals_used = set()
        local_vars = set()
        
        # First, collect all local variable names
        for node in ast.walk(func_node):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                local_vars.add(node.id)
        
        # Then find names that are used but not defined locally
        for node in ast.walk(func_node):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in local_vars and not node.id.startswith('_'):
                    globals_used.add(node.id)
        
        return globals_used
    
    def _find_shared_data_usage(self, tree: ast.AST, file_path: str) -> Dict[str, Set[str]]:
        """Find shared data usage patterns in a file"""
        shared_data = defaultdict(set)
        
        # Find global variables
        global_vars = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                # Simple heuristic: if it's at module level, it's global
                if hasattr(node, 'parent') and isinstance(getattr(node, 'parent', None), ast.Module):
                    global_vars.add(node.targets[0].id)
        
        # Find which functions/classes use these globals
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and child.id in global_vars:
                        shared_data[child.id].add(f"{file_path}:{node.name}")
        
        return shared_data
    
    def _calculate_lcom_score(self, classes: List[Dict[str, Any]]) -> float:
        """Calculate Lack of Cohesion of Methods (LCOM) score"""
        if not classes:
            return 0.0
        
        total_lcom = 0.0
        class_count = 0
        
        for class_info in classes:
            if len(class_info["methods"]) <= 1:
                continue
            
            methods = class_info["methods"]
            method_pairs = []
            
            # Calculate LCOM for this class
            shared_attributes_pairs = 0
            total_pairs = 0
            
            for i, method1 in enumerate(methods):
                for method2 in methods[i+1:]:
                    total_pairs += 1
                    shared_attrs = method1["attributes_used"] & method2["attributes_used"]
                    if shared_attrs:
                        shared_attributes_pairs += 1
            
            if total_pairs > 0:
                class_lcom = 1.0 - (shared_attributes_pairs / total_pairs)
                total_lcom += class_lcom
                class_count += 1
        
        return total_lcom / class_count if class_count > 0 else 0.0
    
    def _calculate_functional_cohesion(self, functions: List[Dict[str, Any]], 
                                     shared_data: Dict[str, Set[str]]) -> float:
        """Calculate functional cohesion score"""
        if not functions:
            return 0.0
        
        # Functions have high functional cohesion if they work together toward a common goal
        # Measured by shared data usage and function calls
        cohesive_pairs = 0
        total_pairs = 0
        
        for i, func1 in enumerate(functions):
            for func2 in functions[i+1:]:
                total_pairs += 1
                
                # Check if functions share data or call each other
                func1_data = func1.get("uses_globals", set())
                func2_data = func2.get("uses_globals", set())
                shared_globals = func1_data & func2_data
                
                func1_calls = func1.get("calls_functions", set())
                func2_calls = func2.get("calls_functions", set())
                calls_each_other = (func1["name"] in func2_calls or func2["name"] in func1_calls)
                
                if shared_globals or calls_each_other:
                    cohesive_pairs += 1
        
        return cohesive_pairs / total_pairs if total_pairs > 0 else 0.0
    
    def _calculate_sequential_cohesion(self, functions: List[Dict[str, Any]]) -> float:
        """Calculate sequential cohesion score"""
        if len(functions) <= 1:
            return 0.0
        
        # Sequential cohesion exists when output of one function is input to another
        # This is a simplified heuristic based on function call patterns
        sequential_pairs = 0
        total_pairs = len(functions) - 1  # Adjacent pairs
        
        for i in range(len(functions) - 1):
            func1 = functions[i]
            func2 = functions[i + 1]
            
            # Check if func2 calls func1 (simple sequential pattern)
            func2_calls = func2.get("calls_functions", set())
            if func1["name"] in func2_calls:
                sequential_pairs += 1
        
        return sequential_pairs / total_pairs if total_pairs > 0 else 0.0
    
    def _calculate_communicational_cohesion(self, functions: List[Dict[str, Any]], 
                                          shared_data: Dict[str, Set[str]]) -> float:
        """Calculate communicational cohesion score"""
        if not functions:
            return 0.0
        
        # Communicational cohesion: functions work on the same data
        data_sharing_score = 0.0
        function_count = len(functions)
        
        # Count how many functions share the same data
        for data_item, users in shared_data.items():
            if len(users) > 1:
                data_sharing_score += len(users) / function_count
        
        # Normalize the score
        total_data_items = len(shared_data)
        return data_sharing_score / total_data_items if total_data_items > 0 else 0.0
    
    def _find_related_components(self, functions: List[Dict[str, Any]], 
                               classes: List[Dict[str, Any]], 
                               shared_data: Dict[str, Set[str]]) -> List[Dict[str, Any]]:
        """Find components that should be grouped together"""
        related_groups = []
        
        # Group functions that share data
        data_groups = defaultdict(list)
        for data_item, users in shared_data.items():
            if len(users) > 1:
                for user in users:
                    data_groups[data_item].append(user)
        
        for data_item, users in data_groups.items():
            if len(users) > 2:  # Only suggest grouping if 3+ components share data
                related_groups.append({
                    "type": "shared_data_group",
                    "reason": f"Multiple components access '{data_item}'",
                    "components": list(users),
                    "shared_data": data_item,
                    "cohesion_strength": "medium"
                })
        
        # Group classes with similar method patterns
        if len(classes) > 1:
            for i, class1 in enumerate(classes):
                for class2 in classes[i+1:]:
                    method_similarity = self._calculate_method_similarity(class1, class2)
                    if method_similarity > 0.6:
                        related_groups.append({
                            "type": "similar_classes",
                            "reason": f"Classes have similar method patterns (similarity: {method_similarity:.2f})",
                            "components": [f"{class1['file']}:{class1['name']}", f"{class2['file']}:{class2['name']}"],
                            "similarity_score": method_similarity,
                            "cohesion_strength": "high" if method_similarity > 0.8 else "medium"
                        })
        
        return related_groups
    
    def _calculate_method_similarity(self, class1: Dict[str, Any], class2: Dict[str, Any]) -> float:
        """Calculate similarity between two classes based on their methods"""
        methods1 = {m["name"] for m in class1["methods"]}
        methods2 = {m["name"] for m in class2["methods"]}
        
        if not methods1 and not methods2:
            return 0.0
        
        intersection = len(methods1 & methods2)
        union = len(methods1 | methods2)
        
        return intersection / union if union > 0 else 0.0
    
    def _is_method(self, func_node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if a function is a method (inside a class)"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if func_node in node.body:
                    return True
        return False