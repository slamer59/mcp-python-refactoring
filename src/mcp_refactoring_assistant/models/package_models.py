#!/usr/bin/env python3
"""
Package-level data models for refactoring analysis using Pydantic
"""

from typing import Any, Dict, List, Literal, Optional, Set
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class ModuleDependency(BaseModel):
    """Represents a dependency relationship between modules"""
    
    source_module: str = Field(..., description="Source module that imports")
    target_module: str = Field(..., description="Target module being imported")
    import_type: Literal["standard", "third_party", "local"] = Field(..., description="Type of import")
    import_statement: str = Field(..., description="Original import statement")
    line_number: int = Field(..., description="Line number of import", gt=0)
    is_circular: bool = Field(default=False, description="Whether this creates a circular dependency")
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()


class PackageMetrics(BaseModel):
    """Aggregated metrics for a package or folder"""
    
    total_files: int = Field(default=0, description="Total Python files", ge=0)
    total_lines: int = Field(default=0, description="Total lines of code", ge=0)
    total_functions: int = Field(default=0, description="Total functions", ge=0)
    total_classes: int = Field(default=0, description="Total classes", ge=0)
    
    # Complexity metrics (aggregated from Radon)
    average_complexity: float = Field(default=0.0, description="Average cyclomatic complexity", ge=0.0)
    max_complexity: float = Field(default=0.0, description="Maximum complexity found", ge=0.0)
    complexity_distribution: Dict[str, int] = Field(default_factory=dict, description="Complexity grade distribution")
    
    # Maintainability metrics
    average_maintainability: float = Field(default=0.0, description="Average maintainability index", ge=0.0)
    maintainability_distribution: Dict[str, int] = Field(default_factory=dict, description="Maintainability grade distribution")
    
    # Dependency metrics
    total_dependencies: int = Field(default=0, description="Total dependencies found", ge=0)
    circular_dependencies: int = Field(default=0, description="Number of circular dependencies", ge=0)
    external_dependencies: int = Field(default=0, description="External package dependencies", ge=0)
    
    # Dead code metrics
    dead_code_lines: int = Field(default=0, description="Lines of dead code", ge=0)
    unused_imports: int = Field(default=0, description="Number of unused imports", ge=0)
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()


class PackageStructureIssue(BaseModel):
    """Represents a structural issue in package organization"""
    
    issue_type: Literal["scattered_functionality", "god_package", "feature_envy", "inappropriate_intimacy", 
                       "circular_dependency", "long_parameter_list", "large_class"] = Field(..., description="Type of structural issue")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Issue severity level")
    affected_modules: List[str] = Field(default_factory=list, description="Modules affected by this issue")
    description: str = Field(..., description="Detailed description of the issue")
    suggested_reorganization: Optional[str] = Field(default=None, description="Suggested package reorganization")
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()


class CohesionMetrics(BaseModel):
    """Metrics related to package cohesion"""
    
    package_name: str = Field(..., description="Name of the package")
    lcom_score: float = Field(default=0.0, description="Lack of Cohesion of Methods score", ge=0.0)
    functional_cohesion: float = Field(default=0.0, description="Functional cohesion score", ge=0.0, le=1.0)
    sequential_cohesion: float = Field(default=0.0, description="Sequential cohesion score", ge=0.0, le=1.0)
    communicational_cohesion: float = Field(default=0.0, description="Communicational cohesion score", ge=0.0, le=1.0)
    
    # Related functions/classes that should be grouped
    related_components: List[Dict[str, Any]] = Field(default_factory=list, description="Components that should be grouped together")
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()


class CouplingMetrics(BaseModel):
    """Metrics related to coupling between modules"""
    
    package_name: str = Field(..., description="Name of the package")
    afferent_coupling: int = Field(default=0, description="Number of classes that depend on this package", ge=0)
    efferent_coupling: int = Field(default=0, description="Number of classes this package depends on", ge=0)
    instability: float = Field(default=0.0, description="Instability metric (Ce/(Ca+Ce))", ge=0.0, le=1.0)
    abstractness: float = Field(default=0.0, description="Abstractness metric", ge=0.0, le=1.0)
    distance_from_main: float = Field(default=0.0, description="Distance from main sequence", ge=0.0)
    
    # Tight coupling indicators
    tightly_coupled_modules: List[Dict[str, Any]] = Field(default_factory=list, description="Modules with tight coupling")
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()


class PackageReorganizationSuggestion(BaseModel):
    """Suggestion for reorganizing package structure"""
    
    suggestion_type: Literal["extract_package", "merge_packages", "move_module", "split_module", 
                           "create_facade", "introduce_layer"] = Field(..., description="Type of reorganization")
    priority: Literal["low", "medium", "high", "critical"] = Field(..., description="Priority of this suggestion")
    affected_files: List[str] = Field(default_factory=list, description="Files that would be affected")
    rationale: str = Field(..., description="Why this reorganization is suggested")
    
    # Detailed reorganization plan
    steps: List[str] = Field(default_factory=list, description="Step-by-step reorganization plan")
    new_structure: Optional[Dict[str, Any]] = Field(default=None, description="Proposed new package structure")
    estimated_effort: Literal["low", "medium", "high"] = Field(default="medium", description="Estimated effort required")
    
    # Impact analysis
    breaking_changes: bool = Field(default=False, description="Whether this change would be breaking")
    affected_imports: List[str] = Field(default_factory=list, description="Import statements that would need updating")
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()


class PackageGuidance(BaseModel):
    """Complete package-level refactoring guidance"""
    
    package_path: str = Field(..., description="Path to the analyzed package")
    package_name: str = Field(..., description="Name of the package")
    
    # Overall metrics and analysis
    metrics: PackageMetrics = Field(..., description="Aggregated package metrics")
    cohesion_metrics: CohesionMetrics = Field(..., description="Cohesion analysis results")
    coupling_metrics: CouplingMetrics = Field(..., description="Coupling analysis results")
    
    # Issues and suggestions
    structural_issues: List[PackageStructureIssue] = Field(default_factory=list, description="Structural issues found")
    reorganization_suggestions: List[PackageReorganizationSuggestion] = Field(default_factory=list, description="Reorganization suggestions")
    
    # Dependencies
    dependencies: List[ModuleDependency] = Field(default_factory=list, description="All module dependencies")
    circular_dependencies: List[List[str]] = Field(default_factory=list, description="Circular dependency chains")
    
    # Quality assessment
    overall_health_score: float = Field(default=0.0, description="Overall package health score", ge=0.0, le=1.0)
    maintainability_rating: Literal["A", "B", "C", "D", "F"] = Field(default="C", description="Overall maintainability rating")
    
    # Recommendations by priority
    high_priority_actions: List[str] = Field(default_factory=list, description="High priority actions to take")
    medium_priority_actions: List[str] = Field(default_factory=list, description="Medium priority actions to take")
    low_priority_actions: List[str] = Field(default_factory=list, description="Low priority actions to take")
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()
    
    @model_validator(mode='after')
    def calculate_health_score(self):
        """Calculate overall health score based on metrics"""
        # Simple health score calculation based on various factors
        score = 1.0
        
        # Deduct for complexity issues
        if self.metrics.average_complexity > 10:
            score -= 0.2
        elif self.metrics.average_complexity > 5:
            score -= 0.1
            
        # Deduct for circular dependencies
        if self.metrics.circular_dependencies > 0:
            score -= 0.3
            
        # Deduct for maintainability issues
        if self.metrics.average_maintainability < 20:
            score -= 0.2
        elif self.metrics.average_maintainability < 50:
            score -= 0.1
            
        # Deduct for coupling issues
        if self.coupling_metrics.instability > 0.8:
            score -= 0.1
            
        # Deduct for dead code
        if self.metrics.dead_code_lines > 0:
            score -= min(0.1, self.metrics.dead_code_lines / self.metrics.total_lines)
        
        self.overall_health_score = max(0.0, score)
        
        # Set maintainability rating based on score
        if self.overall_health_score >= 0.9:
            self.maintainability_rating = "A"
        elif self.overall_health_score >= 0.8:
            self.maintainability_rating = "B"
        elif self.overall_health_score >= 0.7:
            self.maintainability_rating = "C"
        elif self.overall_health_score >= 0.6:
            self.maintainability_rating = "D"
        else:
            self.maintainability_rating = "F"
            
        return self


class DependencyGraph(BaseModel):
    """Represents the dependency graph of a package"""
    
    nodes: List[str] = Field(default_factory=list, description="All modules in the graph")
    edges: List[ModuleDependency] = Field(default_factory=list, description="Dependencies between modules")
    cycles: List[List[str]] = Field(default_factory=list, description="Detected dependency cycles")
    strongly_connected_components: List[List[str]] = Field(default_factory=list, description="Strongly connected components")
    
    def to_dict(self) -> dict:
        """Convert to dictionary with proper serialization"""
        return self.model_dump()