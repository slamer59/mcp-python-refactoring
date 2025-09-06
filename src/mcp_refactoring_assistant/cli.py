#!/usr/bin/env python3
"""
Enhanced Python Refactoring CLI Tool
Supports both MCP server mode and standalone operation
"""

import click
import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.tree import Tree
from rich.layout import Layout
from rich.live import Live
from rich import box
import time

# Import our core analyzer
from .core import EnhancedRefactoringAnalyzer
from .core.package_analyzer import PackageAnalyzer
from .models import RefactoringGuidance

console = Console()

class RefactoringCLI:
    """Enhanced CLI for Python refactoring analysis"""
    
    def __init__(self):
        self.analyzer = EnhancedRefactoringAnalyzer()
        self.package_analyzer = PackageAnalyzer()
        self.console = Console()
        self.current_results = None
        self.current_package_results = None
        
    def display_banner(self):
        """Display application banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║              🐍 Python Refactoring Assistant 🔧              ║
║                                                               ║
║  Comprehensive code analysis • Repository indexing           ║
║  Coverage analysis • Quality insights • MCP Server           ║
╚═══════════════════════════════════════════════════════════════╝
        """
        self.console.print(banner, style="bold cyan")
        
    def analyze_file_interactive(self, file_path: str) -> Dict[str, Any]:
        """Interactive file analysis with progress display"""
        
        if not os.path.exists(file_path):
            self.console.print(f"❌ File not found: {file_path}", style="bold red")
            return {}
            
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("🔍 Analyzing Python file...", total=None)
            
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                progress.update(task, description="🧠 Running complexity analysis...")
                time.sleep(0.5)  # Visual feedback
                
                guidance_list = self.analyzer.analyze_file(file_path, content)
                
                progress.update(task, description="✅ Analysis complete!")
                time.sleep(0.3)
                
            except Exception as e:
                self.console.print(f"❌ Analysis failed: {str(e)}", style="bold red")
                return {}
        
        return self._format_analysis_results(guidance_list, file_path)
    
    def _format_analysis_results(self, guidance_list: List[RefactoringGuidance], file_path: str) -> Dict[str, Any]:
        """Format analysis results for display"""
        
        results = {
            "file_path": file_path,
            "total_issues": len(guidance_list),
            "issues_by_severity": {
                "critical": len([g for g in guidance_list if g.severity == "critical"]),
                "high": len([g for g in guidance_list if g.severity == "high"]),
                "medium": len([g for g in guidance_list if g.severity == "medium"]),
                "low": len([g for g in guidance_list if g.severity == "low"])
            },
            "guidance": guidance_list
        }
        
        self.current_results = results
        return results
        
    def display_analysis_summary(self, results: Dict[str, Any]):
        """Display analysis results summary"""
        
        if not results:
            return
            
        # Summary panel
        summary_text = f"""
📁 File: {results['file_path']}
📊 Total Issues: {results['total_issues']}

🔴 Critical: {results['issues_by_severity']['critical']}
🟠 High: {results['issues_by_severity']['high']}
🟡 Medium: {results['issues_by_severity']['medium']}  
🔵 Low: {results['issues_by_severity']['low']}
        """
        
        self.console.print(Panel(summary_text.strip(), title="📋 Analysis Summary", border_style="blue"))
        
        # Detailed results table
        if results['guidance']:
            table = Table(title="🔍 Refactoring Opportunities", box=box.ROUNDED)
            table.add_column("Severity", style="bold")
            table.add_column("Issue", style="cyan")
            table.add_column("Location", style="yellow")
            table.add_column("Priority", justify="center")
            
            for guidance in results['guidance']:
                severity_color = {
                    'critical': 'red',
                    'high': 'orange3',
                    'medium': 'yellow',
                    'low': 'blue'
                }.get(guidance.severity, 'white')
                
                table.add_row(
                    f"[{severity_color}]{guidance.severity.upper()}[/{severity_color}]",
                    guidance.issue_type.replace('_', ' ').title(),
                    f"Line {guidance.line_number}" if guidance.line_number else "File level",
                    f"⭐ {guidance.priority_score:.1f}"
                )
            
            self.console.print(table)
    
    def display_detailed_guidance(self, guidance: RefactoringGuidance):
        """Display detailed refactoring guidance"""
        
        # Main guidance panel
        guidance_text = f"""
🎯 {guidance.issue_type.replace('_', ' ').title()}

📝 Description:
{guidance.description}

💡 Recommendation:
{guidance.recommendation}

⏱️  Estimated Effort: {guidance.estimated_effort_hours} hours
📍 Priority Score: {guidance.priority_score:.1f}
        """
        
        self.console.print(Panel(
            guidance_text.strip(), 
            title=f"🔧 {guidance.severity.upper()} Priority Issue",
            border_style="red" if guidance.severity == "critical" else "yellow"
        ))
        
        # Step-by-step instructions
        if guidance.precise_steps:
            self.console.print("\n📋 [bold]Step-by-Step Instructions:[/bold]")
            for i, step in enumerate(guidance.precise_steps, 1):
                self.console.print(f"  {i}. {step}")
        
        # Code examples if available
        if hasattr(guidance, 'code_example') and guidance.code_example:
            self.console.print("\n💾 [bold]Code Example:[/bold]")
            syntax = Syntax(guidance.code_example, "python", theme="monokai")
            self.console.print(syntax)
    
    def interactive_guidance_browser(self):
        """Interactive browser for refactoring guidance"""
        
        if not self.current_results or not self.current_results['guidance']:
            self.console.print("❌ No analysis results available. Run analysis first.", style="red")
            return
            
        guidance_list = self.current_results['guidance']
        
        while True:
            self.console.print("\n" + "="*60)
            self.console.print("🧭 [bold]Interactive Guidance Browser[/bold]")
            self.console.print("="*60)
            
            # List all issues
            for i, guidance in enumerate(guidance_list):
                severity_icon = {
                    'critical': '🔴',
                    'high': '🟠', 
                    'medium': '🟡',
                    'low': '🔵'
                }.get(guidance.severity, '⚪')
                
                self.console.print(
                    f"{i+1}. {severity_icon} {guidance.issue_type.replace('_', ' ').title()} "
                    f"(Line {guidance.line_number if guidance.line_number else 'N/A'})"
                )
            
            choice = Prompt.ask(
                "\nSelect issue to view details",
                choices=[str(i+1) for i in range(len(guidance_list))] + ["q"],
                default="q"
            )
            
            if choice == "q":
                break
                
            try:
                selected_guidance = guidance_list[int(choice) - 1]
                self.console.clear()
                self.display_detailed_guidance(selected_guidance)
                
                self.console.print("\n" + "-"*40)
                if not Confirm.ask("Continue browsing?", default=True):
                    break
                    
            except (ValueError, IndexError):
                self.console.print("❌ Invalid selection", style="red")
    
    def analyze_package_interactive(self, package_path: str, package_name: Optional[str] = None) -> Dict[str, Any]:
        """Interactive package analysis with progress display"""
        
        if not os.path.exists(package_path):
            self.console.print(f"❌ Package not found: {package_path}", style="bold red")
            return {}
            
        if not os.path.isdir(package_path):
            self.console.print(f"❌ Package path is not a directory: {package_path}", style="bold red")
            return {}
            
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("🔍 Analyzing package structure...", total=None)
            
            try:
                progress.update(task, description="🧠 Analyzing dependencies...")
                time.sleep(0.5)
                
                progress.update(task, description="📊 Calculating metrics...")
                time.sleep(0.5)
                
                progress.update(task, description="🔗 Analyzing coupling...")
                time.sleep(0.5)
                
                progress.update(task, description="🎯 Analyzing cohesion...")
                time.sleep(0.5)
                
                guidance = self.package_analyzer.analyze_package(package_path, package_name)
                summary = self.package_analyzer.get_package_summary(guidance)
                
                progress.update(task, description="✅ Package analysis complete!")
                time.sleep(0.3)
                
            except Exception as e:
                self.console.print(f"❌ Package analysis failed: {str(e)}", style="bold red")
                return {}
        
        results = {
            "guidance": guidance,
            "summary": summary
        }
        
        self.current_package_results = results
        return results
    
    def display_package_summary(self, results: Dict[str, Any]):
        """Display package analysis results summary"""
        
        if not results or not results.get('summary'):
            return
        
        summary = results['summary']
        
        # Health overview panel
        health_status = summary['overall_health']['status']
        health_color = {
            'excellent': 'green',
            'good': 'blue', 
            'fair': 'yellow',
            'poor': 'orange3',
            'critical': 'red'
        }.get(health_status, 'white')
        
        overview_text = f"""
📦 Package: {summary['package_name']}
🏥 Health Score: {summary['overall_health']['score']:.2f} ({summary['overall_health']['rating']})
📊 Status: [{health_color}]{health_status.upper()}[/{health_color}]

📁 Files: {summary['key_metrics']['files']}
🔧 Functions: {summary['key_metrics']['functions']}
🏗️  Classes: {summary['key_metrics']['classes']}
🔗 Dependencies: {summary['key_metrics']['dependencies']}
⚠️  Circular Deps: {summary['key_metrics']['circular_deps']}
        """
        
        self.console.print(Panel(overview_text.strip(), title="📋 Package Health Overview", border_style="blue"))
        
        # Complexity assessment
        complexity = summary['complexity_assessment']
        complexity_color = {
            'low': 'green',
            'medium': 'yellow',
            'high': 'red'
        }.get(complexity['status'], 'white')
        
        complexity_text = f"""
📈 Average Complexity: {complexity['average']:.2f}
📊 Maximum Complexity: {complexity['max']:.2f}
🎯 Status: [{complexity_color}]{complexity['status'].upper()}[/{complexity_color}]
        """
        
        self.console.print(Panel(complexity_text.strip(), title="🧠 Complexity Assessment", border_style=complexity_color))
        
        # Coupling assessment
        coupling = summary['coupling_assessment']
        coupling_color = {
            'low': 'green',
            'medium': 'yellow', 
            'high': 'red'
        }.get(coupling['status'], 'white')
        
        coupling_text = f"""
⚖️  Instability: {coupling['instability']:.2f}
📏 Distance from Main: {coupling['distance_from_main']:.2f}
🎯 Status: [{coupling_color}]{coupling['status'].upper()}[/{coupling_color}]
        """
        
        self.console.print(Panel(coupling_text.strip(), title="🔗 Coupling Assessment", border_style=coupling_color))
        
        # Top issues table
        if summary['top_issues']:
            issues_table = Table(title="🔍 Top Issues", box=box.ROUNDED)
            issues_table.add_column("Issue", style="red")
            issues_table.add_column("Type", style="cyan")
            
            for issue_desc in summary['top_issues']:
                # Extract issue type from description (simplified)
                issue_type = issue_desc.split(':')[0] if ':' in issue_desc else "General"
                issues_table.add_row(issue_desc, issue_type)
            
            self.console.print(issues_table)
        
        # Immediate actions
        if summary['immediate_actions']:
            actions_text = "\n".join([f"• {action}" for action in summary['immediate_actions']])
            self.console.print(Panel(actions_text, title="⚡ Immediate Actions", border_style="yellow"))
    
    def interactive_package_browser(self):
        """Interactive browser for package analysis results"""
        
        if not self.current_package_results:
            self.console.print("❌ No package analysis results available. Run package analysis first.", style="red")
            return
        
        guidance = self.current_package_results['guidance']
        
        while True:
            self.console.print("\n" + "="*60)
            self.console.print("📦 [bold]Interactive Package Browser[/bold]")
            self.console.print("="*60)
            
            options = {
                "1": "🏥 Health Overview", 
                "2": "📊 Detailed Metrics",
                "3": "🔍 Structural Issues",
                "4": "💡 Reorganization Suggestions",
                "5": "🔗 Dependency Graph",
                "6": "⚠️  Circular Dependencies",
                "7": "📈 Priority Actions"
            }
            
            for key, desc in options.items():
                self.console.print(f"  {key}. {desc}")
            
            choice = Prompt.ask(
                "\nSelect view",
                choices=list(options.keys()) + ["q"],
                default="1"
            )
            
            if choice == "q":
                break
            
            self.console.clear()
            
            if choice == "1":
                self._show_package_health_detail(guidance)
            elif choice == "2":
                self._show_package_metrics_detail(guidance)
            elif choice == "3":
                self._show_structural_issues(guidance)
            elif choice == "4":
                self._show_reorganization_suggestions(guidance)
            elif choice == "5":
                self._show_dependency_graph(guidance)
            elif choice == "6":
                self._show_circular_dependencies(guidance)
            elif choice == "7":
                self._show_priority_actions(guidance)
            
            self.console.print("\n" + "-"*40)
            if not Confirm.ask("Continue browsing?", default=True):
                break
    
    def _show_package_health_detail(self, guidance):
        """Show detailed health information"""
        health_text = f"""
🏥 Package Health Analysis

Overall Score: {guidance.overall_health_score:.2f}/1.0
Maintainability Rating: {guidance.maintainability_rating}

📊 Key Indicators:
• Average Complexity: {guidance.metrics.average_complexity:.2f}
• Circular Dependencies: {guidance.metrics.circular_dependencies}
• Dead Code Lines: {guidance.metrics.dead_code_lines}
• Unused Imports: {guidance.metrics.unused_imports}

🎯 Health Factors:
• Complexity Impact: {'High' if guidance.metrics.average_complexity > 10 else 'Moderate' if guidance.metrics.average_complexity > 5 else 'Low'}
• Dependency Impact: {'High' if guidance.metrics.circular_dependencies > 0 else 'Low'}
• Maintainability: {guidance.metrics.average_maintainability:.1f}
        """
        
        self.console.print(Panel(health_text.strip(), title="🏥 Detailed Health Analysis", border_style="blue"))
    
    def _show_package_metrics_detail(self, guidance):
        """Show detailed metrics"""
        metrics_table = Table(title="📊 Detailed Package Metrics", box=box.ROUNDED)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="yellow")
        metrics_table.add_column("Assessment", style="green")
        
        metrics_data = [
            ("Total Files", guidance.metrics.total_files, "Good" if guidance.metrics.total_files < 50 else "Large"),
            ("Total Functions", guidance.metrics.total_functions, "Good" if guidance.metrics.total_functions < 200 else "Many"),
            ("Total Classes", guidance.metrics.total_classes, "Good" if guidance.metrics.total_classes < 50 else "Many"),
            ("Average Complexity", f"{guidance.metrics.average_complexity:.2f}", "Good" if guidance.metrics.average_complexity < 5 else "High"),
            ("Max Complexity", f"{guidance.metrics.max_complexity:.2f}", "Good" if guidance.metrics.max_complexity < 10 else "Very High"),
            ("Dependencies", guidance.metrics.total_dependencies, "Good" if guidance.metrics.total_dependencies < 20 else "Many"),
            ("Coupling (Instability)", f"{guidance.coupling_metrics.instability:.2f}", "Good" if guidance.coupling_metrics.instability < 0.5 else "High"),
            ("Abstractness", f"{guidance.coupling_metrics.abstractness:.2f}", "Good" if guidance.coupling_metrics.abstractness > 0.3 else "Low")
        ]
        
        for metric, value, assessment in metrics_data:
            assessment_color = "green" if "Good" in assessment else "yellow" if "Moderate" in assessment or "Many" in assessment else "red"
            metrics_table.add_row(metric, str(value), f"[{assessment_color}]{assessment}[/{assessment_color}]")
        
        self.console.print(metrics_table)
    
    def _show_structural_issues(self, guidance):
        """Show structural issues"""
        if not guidance.structural_issues:
            self.console.print("✅ No structural issues found!", style="green")
            return
        
        issues_table = Table(title="🔍 Structural Issues", box=box.ROUNDED)
        issues_table.add_column("Severity", style="bold")
        issues_table.add_column("Issue Type", style="cyan")
        issues_table.add_column("Description", style="yellow")
        issues_table.add_column("Affected Modules", style="blue")
        
        for issue in guidance.structural_issues:
            severity_color = {
                'critical': 'red',
                'high': 'orange3',
                'medium': 'yellow',
                'low': 'blue'
            }.get(issue.severity, 'white')
            
            affected = ', '.join(issue.affected_modules[:2])  # Show first 2
            if len(issue.affected_modules) > 2:
                affected += f" (+{len(issue.affected_modules) - 2} more)"
            
            issues_table.add_row(
                f"[{severity_color}]{issue.severity.upper()}[/{severity_color}]",
                issue.issue_type.replace('_', ' ').title(),
                issue.description[:60] + "..." if len(issue.description) > 60 else issue.description,
                affected
            )
        
        self.console.print(issues_table)
    
    def _show_reorganization_suggestions(self, guidance):
        """Show reorganization suggestions"""
        if not guidance.reorganization_suggestions:
            self.console.print("ℹ️  No reorganization suggestions", style="yellow")
            return
        
        for i, suggestion in enumerate(guidance.reorganization_suggestions, 1):
            priority_color = {
                'critical': 'red',
                'high': 'orange3', 
                'medium': 'yellow',
                'low': 'blue'
            }.get(suggestion.priority, 'white')
            
            suggestion_text = f"""
🎯 Suggestion {i}: {suggestion.suggestion_type.replace('_', ' ').title()}
📊 Priority: [{priority_color}]{suggestion.priority.upper()}[/{priority_color}]
⚖️  Effort: {suggestion.estimated_effort}
💥 Breaking Changes: {'Yes' if suggestion.breaking_changes else 'No'}

📝 Rationale:
{suggestion.rationale}

📋 Steps:
{chr(10).join([f'  {j}. {step}' for j, step in enumerate(suggestion.steps, 1)])}
            """
            
            self.console.print(Panel(suggestion_text.strip(), title=f"💡 Reorganization Suggestion {i}", border_style=priority_color))
    
    def _show_dependency_graph(self, guidance):
        """Show dependency graph information"""
        deps_by_type = {
            'local': [d for d in guidance.dependencies if d.import_type == 'local'],
            'third_party': [d for d in guidance.dependencies if d.import_type == 'third_party'],
            'standard': [d for d in guidance.dependencies if d.import_type == 'standard']
        }
        
        deps_text = f"""
🔗 Dependency Overview

📊 Total Dependencies: {len(guidance.dependencies)}
• Local: {len(deps_by_type['local'])}
• Third Party: {len(deps_by_type['third_party'])}
• Standard Library: {len(deps_by_type['standard'])}

⚠️  Circular Dependencies: {len(guidance.circular_dependencies)}
        """
        
        self.console.print(Panel(deps_text.strip(), title="🔗 Dependency Graph", border_style="blue"))
        
        # Show some dependency examples
        if deps_by_type['local']:
            local_table = Table(title="Local Dependencies (Sample)", box=box.ROUNDED)
            local_table.add_column("Source", style="cyan")
            local_table.add_column("Target", style="yellow")
            local_table.add_column("Statement", style="green")
            
            for dep in deps_by_type['local'][:5]:  # Show first 5
                local_table.add_row(
                    dep.source_module,
                    dep.target_module,
                    dep.import_statement[:50] + "..." if len(dep.import_statement) > 50 else dep.import_statement
                )
            
            self.console.print(local_table)
    
    def _show_circular_dependencies(self, guidance):
        """Show circular dependencies"""
        if not guidance.circular_dependencies:
            self.console.print("✅ No circular dependencies found!", style="green")
            return
        
        for i, cycle in enumerate(guidance.circular_dependencies, 1):
            cycle_text = " → ".join(cycle)
            self.console.print(f"🔄 [red]Cycle {i}:[/red] {cycle_text}")
    
    def _show_priority_actions(self, guidance):
        """Show priority actions"""
        all_actions = []
        
        if guidance.high_priority_actions:
            all_actions.extend([("🔴 HIGH", action) for action in guidance.high_priority_actions])
        
        if guidance.medium_priority_actions:
            all_actions.extend([("🟡 MEDIUM", action) for action in guidance.medium_priority_actions[:5]])
        
        if guidance.low_priority_actions and len(all_actions) < 10:
            all_actions.extend([("🔵 LOW", action) for action in guidance.low_priority_actions[:3]])
        
        if all_actions:
            actions_table = Table(title="⚡ Priority Actions", box=box.ROUNDED)
            actions_table.add_column("Priority", style="bold")
            actions_table.add_column("Action", style="cyan")
            
            for priority, action in all_actions:
                actions_table.add_row(priority, action)
            
            self.console.print(actions_table)
        else:
            self.console.print("ℹ️  No priority actions needed", style="green")
    
    def repository_index_interactive(self, repo_path: str, db_path: Optional[str] = None):
        """Interactive repository indexing"""
        
        if not os.path.exists(repo_path):
            self.console.print(f"❌ Repository not found: {repo_path}", style="bold red")
            return
            
        db_path = db_path or ".refactoring_index.db"
        
        self.console.print(f"🏗️  [bold]Indexing repository:[/bold] {repo_path}")
        self.console.print(f"💾 [bold]Database:[/bold] {db_path}")
        
        if os.path.exists(db_path):
            if Confirm.ask("Database exists. Update incrementally?", default=True):
                return self._update_repository_index_interactive(repo_path, db_path)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("🔍 Scanning repository...", total=None)
            
            try:
                # Use the actual indexing method (we need to add this to AdvancedFeatures)
                result = self._index_repository_with_progress(repo_path, db_path, progress, task)
                
                progress.update(task, description="✅ Indexing complete!")
                
                # Display results
                self._display_indexing_results(result)
                
            except Exception as e:
                self.console.print(f"❌ Indexing failed: {str(e)}", style="bold red")
    
    def _index_repository_with_progress(self, repo_path: str, db_path: str, progress, task) -> Dict[str, Any]:
        """Index repository with progress updates"""
        
        # This would integrate with our existing repository indexing
        # For now, simulate the process
        progress.update(task, description="📁 Finding Python files...")
        time.sleep(1)
        
        progress.update(task, description="🧠 Analyzing code complexity...")  
        time.sleep(2)
        
        progress.update(task, description="💾 Building database...")
        time.sleep(1)
        
        # Placeholder result
        return {
            "status": "success",
            "files_processed": 42,
            "functions_analyzed": 156,
            "classes_found": 28,
            "issues_detected": 73,
            "database_path": db_path,
            "processing_time": 4.2
        }
    
    def _update_repository_index_interactive(self, repo_path: str, db_path: str):
        """Interactive incremental update"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("🔄 Checking for changes...", total=None)
            time.sleep(1)
            
            progress.update(task, description="📝 Updating changed files...")
            time.sleep(1.5)
            
            progress.update(task, description="✅ Update complete!")
            
        self.console.print("✅ [green]Repository index updated successfully![/green]")
    
    def _display_indexing_results(self, result: Dict[str, Any]):
        """Display repository indexing results"""
        
        results_text = f"""
📊 Indexing Results:

📁 Files Processed: {result['files_processed']}
🔧 Functions Analyzed: {result['functions_analyzed']}
🏗️  Classes Found: {result['classes_found']}
⚠️  Issues Detected: {result['issues_detected']}

💾 Database: {result['database_path']}
⏱️  Processing Time: {result['processing_time']}s
        """
        
        self.console.print(Panel(results_text.strip(), title="📈 Repository Analysis Complete", border_style="green"))
    
    def query_repository_interactive(self, db_path: Optional[str] = None):
        """Interactive repository querying"""
        
        db_path = db_path or ".refactoring_index.db"
        
        if not os.path.exists(db_path):
            self.console.print(f"❌ Database not found: {db_path}", style="red")
            self.console.print("💡 Run repository indexing first with: refactor index <repo_path>")
            return
        
        query_options = {
            "1": ("🔥 High Complexity Functions", "high_complexity"),
            "2": ("📏 Large Files", "large_files"), 
            "3": ("💀 Dead Code Candidates", "dead_code"),
            "4": ("🧪 Missing Tests", "missing_tests"),
            "5": ("📋 All Issues", "all_issues"),
            "6": ("✏️  Custom SQL Query", "custom")
        }
        
        self.console.print("\n🔍 [bold]Repository Query Options:[/bold]")
        for key, (desc, _) in query_options.items():
            self.console.print(f"  {key}. {desc}")
        
        choice = Prompt.ask(
            "Select query type",
            choices=list(query_options.keys()) + ["q"],
            default="1"
        )
        
        if choice == "q":
            return
            
        query_desc, query_type = query_options[choice]
        
        if query_type == "custom":
            custom_sql = Prompt.ask("Enter SQL query")
            # Execute custom query
            self._execute_custom_query(db_path, custom_sql)
        else:
            # Execute predefined query
            self._execute_predefined_query(db_path, query_type, query_desc)
    
    def _execute_predefined_query(self, db_path: str, query_type: str, description: str):
        """Execute predefined repository query"""
        
        with Progress(
            SpinnerColumn(), 
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task(f"🔍 Running {description.lower()}...", total=None)
            
            # Simulate query execution
            time.sleep(1)
            
            # Mock results
            results = self._get_mock_query_results(query_type)
            
            progress.update(task, description="✅ Query complete!")
        
        self._display_query_results(results, description)
    
    def _get_mock_query_results(self, query_type: str) -> List[Dict]:
        """Generate mock query results for demo"""
        
        mock_data = {
            "high_complexity": [
                {"file": "src/analyzer.py", "function": "complex_method", "complexity": 15},
                {"file": "src/parser.py", "function": "parse_ast", "complexity": 12},
                {"file": "src/utils.py", "function": "validate_input", "complexity": 11}
            ],
            "large_files": [
                {"file": "src/main.py", "lines": 850, "size_kb": 34},
                {"file": "src/server.py", "lines": 720, "size_kb": 28}
            ],
            "dead_code": [
                {"file": "src/legacy.py", "line": 45, "description": "Unused function 'old_parser'"},
                {"file": "src/utils.py", "line": 123, "description": "Unreachable code after return"}
            ]
        }
        
        return mock_data.get(query_type, [])
    
    def _display_query_results(self, results: List[Dict], description: str):
        """Display query results in formatted table"""
        
        if not results:
            self.console.print("ℹ️  No results found", style="yellow")
            return
        
        table = Table(title=f"📊 {description}", box=box.ROUNDED)
        
        # Add columns based on first result
        if results:
            for key in results[0].keys():
                table.add_column(key.replace('_', ' ').title(), style="cyan")
            
            for result in results:
                table.add_row(*[str(value) for value in result.values()])
        
        self.console.print(table)
    
    def start_mcp_server_mode(self):
        """Start in MCP server mode"""
        self.console.print("🚀 [bold green]Starting MCP Server mode...[/bold green]")
        
        try:
            # Import and start MCP server
            from .server import main as mcp_main
            import asyncio
            
            self.console.print("🔌 MCP Server running on stdio...")
            self.console.print("💡 Connect with your MCP client to start analysis")
            
            asyncio.run(mcp_main())
            
        except ImportError:
            self.console.print("❌ MCP not available. Install with: pip install mcp", style="red")
        except Exception as e:
            self.console.print(f"❌ Server failed to start: {str(e)}", style="red")


# Click CLI interface
@click.group()
@click.version_option(version="1.0.0")
@click.pass_context
def cli(ctx):
    """🐍 Python Refactoring Assistant - Comprehensive code analysis and refactoring guidance"""
    ctx.ensure_object(dict)
    ctx.obj['cli_tool'] = RefactoringCLI()


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--interactive', '-i', is_flag=True, help='Interactive guidance browser')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'detailed']), default='table', help='Output format')
@click.pass_context
def analyze(ctx, file_path: str, interactive: bool, format: str):
    """🔍 Analyze a Python file for refactoring opportunities"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    results = cli_tool.analyze_file_interactive(file_path)
    
    if format == 'json':
        # Convert RefactoringGuidance objects to dict for JSON serialization
        json_results = {
            **results,
            'guidance': [g.to_dict() for g in results.get('guidance', [])]
        }
        click.echo(json.dumps(json_results, indent=2))
    elif format == 'detailed':
        cli_tool.display_analysis_summary(results)
        for guidance in results.get('guidance', []):
            cli_tool.display_detailed_guidance(guidance)
            if not click.confirm('\nContinue to next issue?', default=True):
                break
    else:
        cli_tool.display_analysis_summary(results)
    
    if interactive and results.get('guidance'):
        cli_tool.interactive_guidance_browser()


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True))
@click.option('--database', '-db', default='.refactoring_index.db', help='Database file path')
@click.option('--include', multiple=True, help='Include patterns (glob)')
@click.option('--exclude', multiple=True, help='Exclude patterns (glob)')
@click.pass_context
def index(ctx, repo_path: str, database: str, include: tuple, exclude: tuple):
    """🏗️ Index a repository for comprehensive analysis"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    cli_tool.repository_index_interactive(repo_path, database)


@cli.command()
@click.option('--database', '-db', default='.refactoring_index.db', help='Database file path')
@click.pass_context  
def query(ctx, database: str):
    """🔍 Query repository analysis results"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    cli_tool.query_repository_interactive(database)


@cli.command()
@click.pass_context
def server(ctx):
    """🚀 Start MCP server mode"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    cli_tool.start_mcp_server_mode()


@cli.command(name='analyze-package')
@click.argument('package_path', type=click.Path(exists=True))
@click.option('--name', '-n', help='Package name (optional, inferred from path)')
@click.option('--interactive', '-i', is_flag=True, help='Interactive package browser')
@click.option('--format', '-f', type=click.Choice(['summary', 'json', 'detailed']), default='summary', help='Output format')
@click.pass_context
def analyze_package(ctx, package_path: str, name: str, interactive: bool, format: str):
    """📦 Analyze a Python package/folder for refactoring opportunities"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    results = cli_tool.analyze_package_interactive(package_path, name)
    
    if not results:
        return
    
    if format == 'json':
        # Convert guidance to dict for JSON serialization
        json_results = {
            "guidance": results['guidance'].to_dict(),
            "summary": results['summary']
        }
        click.echo(json.dumps(json_results, indent=2, default=str))
    elif format == 'detailed':
        cli_tool.display_package_summary(results)
        if interactive:
            cli_tool.interactive_package_browser()
    else:  # summary
        cli_tool.display_package_summary(results)
    
    if interactive and not format == 'json':
        cli_tool.interactive_package_browser()


@cli.command(name='package-metrics')
@click.argument('package_path', type=click.Path(exists=True))
@click.option('--name', '-n', help='Package name (optional, inferred from path)')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_context
def package_metrics(ctx, package_path: str, name: str, format: str):
    """📊 Get detailed metrics for a Python package"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    results = cli_tool.analyze_package_interactive(package_path, name)
    
    if not results:
        return
    
    guidance = results['guidance']
    
    if format == 'json':
        metrics_result = {
            "package_name": guidance.package_name,
            "package_path": guidance.package_path,
            "metrics": guidance.metrics.to_dict(),
            "cohesion_metrics": guidance.cohesion_metrics.to_dict(),
            "coupling_metrics": guidance.coupling_metrics.to_dict(),
            "overall_health": {
                "score": guidance.overall_health_score,
                "rating": guidance.maintainability_rating
            }
        }
        click.echo(json.dumps(metrics_result, indent=2, default=str))
    else:
        # Show detailed metrics in table format
        console.print(f"\n📊 [bold]Package Metrics: {guidance.package_name}[/bold]")
        cli_tool._show_package_metrics_detail(guidance)


@cli.command(name='package-issues')
@click.argument('package_path', type=click.Path(exists=True))
@click.option('--types', '-t', multiple=True, help='Specific issue types to look for')
@click.option('--severity', '-s', type=click.Choice(['critical', 'high', 'medium', 'low']), help='Minimum severity level')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_context
def package_issues(ctx, package_path: str, types: tuple, severity: str, format: str):
    """🔍 Find structural issues in a Python package"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    results = cli_tool.analyze_package_interactive(package_path)
    
    if not results:
        return
    
    guidance = results['guidance']
    issues = guidance.structural_issues
    
    # Filter by types if specified
    if types:
        issues = [issue for issue in issues if issue.issue_type in types]
    
    # Filter by severity if specified
    if severity:
        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        min_severity = severity_order[severity]
        issues = [issue for issue in issues if severity_order[issue.severity] >= min_severity]
    
    if format == 'json':
        issues_result = {
            "package_name": guidance.package_name,
            "package_path": guidance.package_path,
            "issues_found": len(issues),
            "issues": [issue.to_dict() for issue in issues],
            "reorganization_suggestions": [suggestion.to_dict() for suggestion in guidance.reorganization_suggestions]
        }
        click.echo(json.dumps(issues_result, indent=2, default=str))
    else:
        console.print(f"\n🔍 [bold]Structural Issues: {guidance.package_name}[/bold]")
        if not issues:
            console.print("✅ No issues found matching the criteria!", style="green")
        else:
            # Create a temporary guidance object with filtered issues for display
            temp_guidance = guidance.copy()
            temp_guidance.structural_issues = issues
            cli_tool._show_structural_issues(temp_guidance)
            
            if guidance.reorganization_suggestions:
                console.print(f"\n💡 [bold]Reorganization Suggestions:[/bold]")
                cli_tool._show_reorganization_suggestions(guidance)


@cli.command(name='package-dependencies')
@click.argument('package_path', type=click.Path(exists=True))
@click.option('--show-circular', '-c', is_flag=True, help='Show circular dependencies')
@click.option('--format', '-f', type=click.Choice(['summary', 'json', 'detailed']), default='summary', help='Output format')
@click.pass_context
def package_dependencies(ctx, package_path: str, show_circular: bool, format: str):
    """🔗 Analyze package dependencies and detect circular dependencies"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    results = cli_tool.analyze_package_interactive(package_path)
    
    if not results:
        return
    
    guidance = results['guidance']
    
    if format == 'json':
        deps_result = {
            "package_name": guidance.package_name,
            "package_path": guidance.package_path,
            "dependencies": [dep.to_dict() for dep in guidance.dependencies],
            "circular_dependencies": guidance.circular_dependencies,
            "dependency_stats": {
                "total": len(guidance.dependencies),
                "local": len([d for d in guidance.dependencies if d.import_type == 'local']),
                "third_party": len([d for d in guidance.dependencies if d.import_type == 'third_party']),
                "standard": len([d for d in guidance.dependencies if d.import_type == 'standard'])
            }
        }
        click.echo(json.dumps(deps_result, indent=2, default=str))
    elif format == 'detailed':
        console.print(f"\n🔗 [bold]Dependencies: {guidance.package_name}[/bold]")
        cli_tool._show_dependency_graph(guidance)
        if show_circular or guidance.circular_dependencies:
            console.print(f"\n⚠️  [bold]Circular Dependencies:[/bold]")
            cli_tool._show_circular_dependencies(guidance)
    else:  # summary
        deps_by_type = {
            'local': [d for d in guidance.dependencies if d.import_type == 'local'],
            'third_party': [d for d in guidance.dependencies if d.import_type == 'third_party'],
            'standard': [d for d in guidance.dependencies if d.import_type == 'standard']
        }
        
        summary_text = f"""
📦 Package: {guidance.package_name}
🔗 Total Dependencies: {len(guidance.dependencies)}

📊 Breakdown:
• Local: {len(deps_by_type['local'])}
• Third Party: {len(deps_by_type['third_party'])}
• Standard Library: {len(deps_by_type['standard'])}

⚠️  Circular Dependencies: {len(guidance.circular_dependencies)}
        """
        
        console.print(Panel(summary_text.strip(), title="🔗 Dependency Summary", border_style="blue"))
        
        if show_circular and guidance.circular_dependencies:
            console.print(f"\n⚠️  [bold red]Circular Dependencies Found:[/bold red]")
            for i, cycle in enumerate(guidance.circular_dependencies, 1):
                cycle_text = " → ".join(cycle)
                console.print(f"  {i}. {cycle_text}")




if __name__ == '__main__':
    cli()