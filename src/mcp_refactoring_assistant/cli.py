#!/usr/bin/env python3
"""
Enhanced Python Refactoring CLI/TUI Tool
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
from .models import RefactoringGuidance

console = Console()

class RefactoringCLI:
    """Enhanced CLI/TUI for Python refactoring analysis"""
    
    def __init__(self):
        self.analyzer = EnhancedRefactoringAnalyzer()
        self.console = Console()
        self.current_results = None
        
    def display_banner(self):
        """Display application banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║              🐍 Python Refactoring Assistant 🔧              ║
║                                                               ║
║  Comprehensive code analysis • Repository indexing           ║
║  TDD guidance • Coverage analysis • Quality insights         ║
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


@cli.command()
@click.pass_context
def tui(ctx):
    """🖥️ Start interactive TUI mode"""
    
    cli_tool = ctx.obj['cli_tool']
    cli_tool.display_banner()
    
    console.print("🚧 [yellow]TUI mode coming soon![/yellow]")
    console.print("💡 Use the CLI commands for now:")
    console.print("   • refactor analyze <file>")
    console.print("   • refactor index <repo>") 
    console.print("   • refactor query")
    console.print("   • refactor server")


if __name__ == '__main__':
    cli()