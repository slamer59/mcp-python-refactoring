#!/usr/bin/env python3
"""
Package-level refactoring analyzer orchestrator
"""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..models.package_models import (
    PackageGuidance,
    PackageMetrics,
    DependencyGraph,
    CohesionMetrics,
    CouplingMetrics,
    PackageStructureIssue,
    PackageReorganizationSuggestion
)
from ..analyzers.package import (
    DependencyAnalyzer,
    CohesionAnalyzer,
    CouplingAnalyzer,
    PackageStructureAnalyzer
)
from ..analyzers import RadonAnalyzer, VultureAnalyzer


class PackageAnalyzer:
    """Professional package-level refactoring analyzer orchestrating specialized analyzers"""
    
    def __init__(self):
        # Initialize specialized package analyzers
        self.dependency_analyzer = DependencyAnalyzer()
        self.cohesion_analyzer = CohesionAnalyzer()
        self.coupling_analyzer = CouplingAnalyzer()
        self.structure_analyzer = PackageStructureAnalyzer()
        
        # Initialize file-level analyzers for aggregation
        self.radon_analyzer = RadonAnalyzer()
        self.vulture_analyzer = VultureAnalyzer()
    
    def analyze_package(self, package_path: str, package_name: Optional[str] = None) -> PackageGuidance:
        """
        Comprehensive package analysis using all available analyzers
        
        Args:
            package_path: Path to the package directory
            package_name: Optional name for the package (will be inferred if not provided)
            
        Returns:
            PackageGuidance containing comprehensive analysis results
        """
        package_path = Path(package_path)
        
        if not package_path.exists():
            raise ValueError(f"Package path does not exist: {package_path}")
        
        if not package_path.is_dir():
            raise ValueError(f"Package path is not a directory: {package_path}")
        
        # Infer package name if not provided
        if package_name is None:
            package_name = package_path.name
        
        # Step 1: Analyze dependencies
        print(f"Analyzing dependencies for {package_name}...")
        dependency_graph = self.dependency_analyzer.analyze_package_dependencies(str(package_path))
        
        # Step 2: Calculate aggregated metrics
        print(f"Calculating package metrics...")
        package_metrics = self._calculate_package_metrics(package_path, dependency_graph)
        
        # Step 3: Analyze cohesion
        print(f"Analyzing package cohesion...")
        cohesion_metrics = self.cohesion_analyzer.analyze_package_cohesion(str(package_path), package_name)
        
        # Step 4: Analyze coupling
        print(f"Analyzing package coupling...")
        coupling_metrics = self.coupling_analyzer.analyze_package_coupling(str(package_path), package_name, dependency_graph)
        
        # Step 5: Analyze structure and detect issues
        print(f"Analyzing package structure...")
        structural_issues, reorganization_suggestions = self.structure_analyzer.analyze_package_structure(
            str(package_path), dependency_graph
        )
        
        # Step 6: Generate prioritized recommendations
        high_priority, medium_priority, low_priority = self._prioritize_recommendations(
            structural_issues, reorganization_suggestions, package_metrics
        )
        
        # Create comprehensive guidance
        guidance = PackageGuidance(
            package_path=str(package_path),
            package_name=package_name,
            metrics=package_metrics,
            cohesion_metrics=cohesion_metrics,
            coupling_metrics=coupling_metrics,
            structural_issues=structural_issues,
            reorganization_suggestions=reorganization_suggestions,
            dependencies=dependency_graph.edges,
            circular_dependencies=dependency_graph.cycles,
            high_priority_actions=high_priority,
            medium_priority_actions=medium_priority,
            low_priority_actions=low_priority
        )
        
        return guidance
    
    def _calculate_package_metrics(self, package_path: Path, dependency_graph: DependencyGraph) -> PackageMetrics:
        """Calculate aggregated metrics for the package"""
        metrics = PackageMetrics()
        
        # Find all Python files
        python_files = list(package_path.rglob("*.py"))
        python_files = [f for f in python_files if "__pycache__" not in str(f)]
        
        metrics.total_files = len(python_files)
        
        # Aggregate metrics from individual files
        complexity_scores = []
        maintainability_scores = []
        complexity_grades = []
        maintainability_grades = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count lines, functions, classes
                metrics.total_lines += len(content.splitlines())
                
                try:
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            metrics.total_functions += 1
                        elif isinstance(node, ast.ClassDef):
                            metrics.total_classes += 1
                
                except SyntaxError:
                    continue  # Skip files with syntax errors
                
                # Get Radon metrics for complexity and maintainability
                try:
                    radon_guidance = self.radon_analyzer.analyze(content, str(file_path))
                    for guidance in radon_guidance:
                        if guidance.metrics:
                            if "complexity" in guidance.metrics:
                                complexity_scores.append(guidance.metrics["complexity"])
                                if "grade" in guidance.metrics:
                                    complexity_grades.append(guidance.metrics["grade"])
                            
                            if "maintainability" in guidance.metrics:
                                maintainability_scores.append(guidance.metrics["maintainability"])
                                if "maintainability_grade" in guidance.metrics:
                                    maintainability_grades.append(guidance.metrics["maintainability_grade"])
                
                except Exception:
                    continue  # Skip if Radon analysis fails
                
                # Get Vulture metrics for dead code
                try:
                    vulture_guidance = self.vulture_analyzer.analyze(content, str(file_path))
                    for guidance in vulture_guidance:
                        if guidance.metrics and "unused_items" in guidance.metrics:
                            unused_items = guidance.metrics["unused_items"]
                            metrics.unused_imports += len([item for item in unused_items if "import" in item.get("type", "")])
                            metrics.dead_code_lines += len(unused_items) * 2  # Rough estimate
                
                except Exception:
                    continue  # Skip if Vulture analysis fails
            
            except Exception as e:
                print(f"Warning: Could not analyze {file_path}: {e}")
                continue
        
        # Calculate averages and distributions
        if complexity_scores:
            metrics.average_complexity = sum(complexity_scores) / len(complexity_scores)
            metrics.max_complexity = max(complexity_scores)
            
            # Create complexity distribution
            from collections import Counter
            grade_counts = Counter(complexity_grades)
            for grade, count in grade_counts.items():
                metrics.complexity_distribution[grade] = count
        
        if maintainability_scores:
            metrics.average_maintainability = sum(maintainability_scores) / len(maintainability_scores)
            
            # Create maintainability distribution  
            from collections import Counter
            grade_counts = Counter(maintainability_grades)
            for grade, count in grade_counts.items():
                metrics.maintainability_distribution[grade] = count
        
        # Calculate dependency metrics
        metrics.total_dependencies = len(dependency_graph.edges)
        metrics.circular_dependencies = len(dependency_graph.cycles)
        metrics.external_dependencies = len([
            dep for dep in dependency_graph.edges 
            if dep.import_type in ["third_party", "standard"]
        ])
        
        return metrics
    
    def _prioritize_recommendations(self, structural_issues: List[PackageStructureIssue],
                                  reorganization_suggestions: List[PackageReorganizationSuggestion],
                                  package_metrics: PackageMetrics) -> tuple[List[str], List[str], List[str]]:
        """Prioritize recommendations based on severity and impact"""
        high_priority = []
        medium_priority = []
        low_priority = []
        
        # Prioritize structural issues
        for issue in structural_issues:
            action = f"Address {issue.issue_type}: {issue.description}"
            
            if issue.severity == "critical":
                high_priority.append(action)
            elif issue.severity == "high":
                high_priority.append(action)
            elif issue.severity == "medium":
                medium_priority.append(action)
            else:
                low_priority.append(action)
        
        # Prioritize reorganization suggestions
        for suggestion in reorganization_suggestions:
            action = f"Consider {suggestion.suggestion_type}: {suggestion.rationale}"
            
            if suggestion.priority == "critical":
                high_priority.append(action)
            elif suggestion.priority == "high":
                high_priority.append(action)
            elif suggestion.priority == "medium":
                medium_priority.append(action)
            else:
                low_priority.append(action)
        
        # Add general recommendations based on metrics
        if package_metrics.circular_dependencies > 0:
            high_priority.insert(0, f"CRITICAL: Resolve {package_metrics.circular_dependencies} circular dependencies")
        
        if package_metrics.average_complexity > 10:
            medium_priority.append(f"Reduce average complexity from {package_metrics.average_complexity:.1f}")
        
        if package_metrics.average_maintainability < 20:
            medium_priority.append(f"Improve maintainability from {package_metrics.average_maintainability:.1f}")
        
        if package_metrics.dead_code_lines > 0:
            low_priority.append(f"Remove {package_metrics.dead_code_lines} lines of dead code")
        
        if package_metrics.unused_imports > 0:
            low_priority.append(f"Clean up {package_metrics.unused_imports} unused imports")
        
        return high_priority, medium_priority, low_priority
    
    def get_package_summary(self, guidance: PackageGuidance) -> Dict[str, Any]:
        """Generate a concise summary of package analysis"""
        return {
            "package_name": guidance.package_name,
            "overall_health": {
                "score": guidance.overall_health_score,
                "rating": guidance.maintainability_rating,
                "status": self._get_health_status(guidance.overall_health_score)
            },
            "key_metrics": {
                "files": guidance.metrics.total_files,
                "functions": guidance.metrics.total_functions,
                "classes": guidance.metrics.total_classes,
                "dependencies": guidance.metrics.total_dependencies,
                "circular_deps": guidance.metrics.circular_dependencies
            },
            "top_issues": [
                issue.description for issue in guidance.structural_issues
                if issue.severity in ["critical", "high"]
            ][:5],
            "immediate_actions": guidance.high_priority_actions[:3],
            "complexity_assessment": {
                "average": guidance.metrics.average_complexity,
                "max": guidance.metrics.max_complexity,
                "status": "high" if guidance.metrics.average_complexity > 10 else 
                         "medium" if guidance.metrics.average_complexity > 5 else "low"
            },
            "coupling_assessment": {
                "instability": guidance.coupling_metrics.instability,
                "distance_from_main": guidance.coupling_metrics.distance_from_main,
                "status": "high" if guidance.coupling_metrics.instability > 0.7 else
                         "medium" if guidance.coupling_metrics.instability > 0.3 else "low"
            }
        }
    
    def _get_health_status(self, score: float) -> str:
        """Convert health score to descriptive status"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.7:
            return "fair"
        elif score >= 0.6:
            return "poor"
        else:
            return "critical"
    
    def analyze_package_evolution(self, current_package_path: str, 
                                previous_analysis: PackageGuidance = None) -> Dict[str, Any]:
        """Analyze how package structure has evolved over time"""
        if previous_analysis is None:
            return {"message": "No previous analysis available for comparison"}
        
        current_analysis = self.analyze_package(current_package_path)
        
        evolution = {
            "health_trend": self._compare_health_scores(
                previous_analysis.overall_health_score,
                current_analysis.overall_health_score
            ),
            "metrics_changes": {
                "files": current_analysis.metrics.total_files - previous_analysis.metrics.total_files,
                "functions": current_analysis.metrics.total_functions - previous_analysis.metrics.total_functions,
                "classes": current_analysis.metrics.total_classes - previous_analysis.metrics.total_classes,
                "complexity": current_analysis.metrics.average_complexity - previous_analysis.metrics.average_complexity,
                "dependencies": current_analysis.metrics.total_dependencies - previous_analysis.metrics.total_dependencies
            },
            "new_issues": [
                issue for issue in current_analysis.structural_issues
                if not any(prev_issue.description == issue.description 
                          for prev_issue in previous_analysis.structural_issues)
            ],
            "resolved_issues": [
                issue for issue in previous_analysis.structural_issues
                if not any(curr_issue.description == issue.description 
                          for curr_issue in current_analysis.structural_issues)
            ]
        }
        
        return evolution
    
    def _compare_health_scores(self, previous: float, current: float) -> str:
        """Compare health scores and determine trend"""
        diff = current - previous
        
        if diff > 0.1:
            return "significantly_improved"
        elif diff > 0.05:
            return "improved"
        elif diff > -0.05:
            return "stable"
        elif diff > -0.1:
            return "declined"
        else:
            return "significantly_declined"