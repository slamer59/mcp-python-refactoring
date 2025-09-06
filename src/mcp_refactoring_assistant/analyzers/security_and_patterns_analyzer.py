#!/usr/bin/env python3
"""
Unified security and patterns analyzer that orchestrates all security and modernization analyses
"""

import ast
from typing import Dict, List, Optional

from ..models import RefactoringGuidance
from .base import BaseAnalyzer
from .dependency_security_analyzer import DependencySecurityAnalyzer
from .modern_patterns_analyzer import ModernPatternsAnalyzer
from .security_analyzer import SecurityAnalyzer


class SecurityAndPatternsAnalyzer(BaseAnalyzer):
    """Unified analyzer that orchestrates security and modernization pattern analysis"""

    def __init__(self):
        super().__init__()
        self.security_analyzer = SecurityAnalyzer()
        self.patterns_analyzer = ModernPatternsAnalyzer()
        self.dependency_analyzer = DependencySecurityAnalyzer()

    def analyze(self, content: str, file_path: str, tree: ast.AST = None) -> List[RefactoringGuidance]:
        """
        Comprehensive security and patterns analysis
        
        Args:
            content: Python code content
            file_path: Path to the file being analyzed
            tree: Optional pre-parsed AST tree
            
        Returns:
            List of prioritized refactoring guidance items
        """
        all_guidance = []
        analysis_results = {}

        # Parse AST if not provided
        if tree is None:
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                return [
                    RefactoringGuidance(
                        issue_type="syntax_error",
                        severity="critical",
                        location=f"Line {e.lineno} in {file_path}",
                        description=f"Syntax error prevents analysis: {e.msg}",
                        benefits=["Fix syntax to enable comprehensive analysis"],
                        precise_steps=[
                            "1. Review syntax error message",
                            "2. Fix the syntax issue",
                            "3. Re-run security and patterns analysis"
                        ]
                    )
                ]

        # Run security analysis
        try:
            security_guidance = self.security_analyzer._safe_analyze(content, file_path, tree)
            all_guidance.extend(security_guidance)
            analysis_results['security_issues'] = len(security_guidance)
        except Exception as e:
            print(f"Warning: Security analysis failed: {e}")
            analysis_results['security_issues'] = 0

        # Run modern patterns analysis
        try:
            patterns_guidance = self.patterns_analyzer._safe_analyze(content, file_path, tree)
            all_guidance.extend(patterns_guidance)
            analysis_results['modernization_opportunities'] = len(patterns_guidance)
        except Exception as e:
            print(f"Warning: Patterns analysis failed: {e}")
            analysis_results['modernization_opportunities'] = 0

        # Run dependency security analysis (once per project, not per file)
        try:
            dependency_guidance = self.dependency_analyzer._safe_analyze(content, file_path, tree)
            all_guidance.extend(dependency_guidance)
            analysis_results['dependency_vulnerabilities'] = len(dependency_guidance)
        except Exception as e:
            print(f"Warning: Dependency analysis failed: {e}")
            analysis_results['dependency_vulnerabilities'] = 0

        # Prioritize and deduplicate guidance
        prioritized_guidance = self._prioritize_guidance(all_guidance, analysis_results)

        return prioritized_guidance

    def _prioritize_guidance(self, guidance_list: List[RefactoringGuidance], 
                           analysis_results: Dict[str, int]) -> List[RefactoringGuidance]:
        """
        Prioritize guidance based on severity, issue type, and overall analysis results
        """
        if not guidance_list:
            return guidance_list

        # Define priority weights for different issue types
        issue_type_priorities = {
            # Critical security issues
            'security_vulnerability': 100,
            'dependency_vulnerability': 95,
            
            # Syntax and analysis errors
            'syntax_error': 90,
            'security_analysis_error': 20,
            'modernization_analysis_error': 15,
            'dependency_scan_error': 25,
            
            # Modernization opportunities
            'modernization_opportunity': 60,
            
            # Tool availability
            'security_tool_missing': 80,
            'modernization_tool_missing': 50,
            'dependency_tool_missing': 85,
            
            # Performance and timeouts
            'security_analysis_timeout': 10,
            'modernization_analysis_timeout': 10,
            'dependency_scan_timeout': 15,
        }

        # Define severity weights
        severity_weights = {
            'critical': 1000,
            'high': 500,
            'medium': 100,
            'low': 50
        }

        # Calculate priority score for each guidance item
        scored_guidance = []
        for guidance in guidance_list:
            base_priority = issue_type_priorities.get(guidance.issue_type, 50)
            severity_weight = severity_weights.get(guidance.severity, 50)
            
            # Calculate final priority score
            priority_score = base_priority + severity_weight
            
            # Boost priority for critical security issues
            if guidance.issue_type in ['security_vulnerability', 'dependency_vulnerability']:
                if guidance.severity in ['critical', 'high']:
                    priority_score += 200
            
            scored_guidance.append((priority_score, guidance))

        # Sort by priority score (highest first) and remove duplicates
        scored_guidance.sort(key=lambda x: x[0], reverse=True)
        
        # Remove near-duplicate guidance (same issue type and location)
        unique_guidance = []
        seen_combinations = set()
        
        for score, guidance in scored_guidance:
            # Create a key for deduplication
            key = (guidance.issue_type, guidance.location, guidance.severity)
            
            if key not in seen_combinations:
                seen_combinations.add(key)
                unique_guidance.append(guidance)

        return unique_guidance

    def get_analysis_summary(self, guidance_list: List[RefactoringGuidance]) -> Dict[str, any]:
        """
        Generate a comprehensive analysis summary
        """
        if not guidance_list:
            return {
                'total_issues': 0,
                'security_status': 'excellent',
                'modernization_status': 'up_to_date',
                'recommendations': ['No issues found - excellent code quality!']
            }

        # Categorize issues
        security_issues = [g for g in guidance_list if 'security' in g.issue_type or 'dependency' in g.issue_type]
        modernization_issues = [g for g in guidance_list if 'modernization' in g.issue_type]
        tool_issues = [g for g in guidance_list if 'tool_missing' in g.issue_type]
        
        # Count by severity
        severity_counts = {}
        for guidance in guidance_list:
            severity_counts[guidance.severity] = severity_counts.get(guidance.severity, 0) + 1

        # Determine overall status
        security_status = self._determine_security_status(security_issues)
        modernization_status = self._determine_modernization_status(modernization_issues)

        # Generate top recommendations
        recommendations = self._generate_top_recommendations(guidance_list, security_issues, modernization_issues)

        return {
            'total_issues': len(guidance_list),
            'security_issues': len(security_issues),
            'modernization_opportunities': len(modernization_issues),
            'tool_issues': len(tool_issues),
            'severity_breakdown': severity_counts,
            'security_status': security_status,
            'modernization_status': modernization_status,
            'top_recommendations': recommendations[:5],  # Top 5 recommendations
            'immediate_actions': [g for g in guidance_list if g.severity in ['critical', 'high']][:3]
        }

    def _determine_security_status(self, security_issues: List[RefactoringGuidance]) -> str:
        """Determine overall security status"""
        if not security_issues:
            return 'excellent'
        
        critical_count = len([g for g in security_issues if g.severity == 'critical'])
        high_count = len([g for g in security_issues if g.severity == 'high'])
        
        if critical_count > 0:
            return 'critical'
        elif high_count > 2:
            return 'concerning'
        elif high_count > 0:
            return 'needs_attention'
        else:
            return 'good'

    def _determine_modernization_status(self, modernization_issues: List[RefactoringGuidance]) -> str:
        """Determine overall modernization status"""
        if not modernization_issues:
            return 'up_to_date'
        
        high_priority_count = len([g for g in modernization_issues if g.severity in ['high', 'medium']])
        
        if high_priority_count > 10:
            return 'needs_modernization'
        elif high_priority_count > 5:
            return 'could_be_improved'
        else:
            return 'mostly_modern'

    def _generate_top_recommendations(self, all_guidance: List[RefactoringGuidance],
                                    security_issues: List[RefactoringGuidance],
                                    modernization_issues: List[RefactoringGuidance]) -> List[str]:
        """Generate top-level recommendations"""
        recommendations = []

        # Security recommendations
        critical_security = [g for g in security_issues if g.severity == 'critical']
        if critical_security:
            recommendations.append(f"🚨 URGENT: Address {len(critical_security)} critical security vulnerabilities immediately")

        high_security = [g for g in security_issues if g.severity == 'high']
        if high_security:
            recommendations.append(f"🔒 HIGH PRIORITY: Fix {len(high_security)} high-severity security issues")

        # Dependency recommendations
        dependency_issues = [g for g in security_issues if 'dependency' in g.issue_type]
        if dependency_issues:
            recommendations.append(f"📦 Update {len(dependency_issues)} vulnerable dependencies")

        # Modernization recommendations
        high_modernization = [g for g in modernization_issues if g.severity in ['high', 'medium']]
        if high_modernization:
            recommendations.append(f"⚡ Modernize code: {len(high_modernization)} opportunities for improvement")

        # Tool installation recommendations
        tool_issues = [g for g in all_guidance if 'tool_missing' in g.issue_type]
        if tool_issues:
            missing_tools = [g.description.split()[0] for g in tool_issues]
            recommendations.append(f"🛠️ Install missing tools: {', '.join(set(missing_tools))}")

        # General recommendations if no specific issues
        if not recommendations:
            recommendations.extend([
                "✅ Security status looks good",
                "🔍 Continue regular security and pattern analysis",
                "📈 Consider setting up automated scanning in CI/CD"
            ])

        return recommendations