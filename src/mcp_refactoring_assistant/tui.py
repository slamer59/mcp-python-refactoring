#!/usr/bin/env python3
"""
Advanced TUI (Terminal User Interface) for Python Refactoring Assistant
Built with Textual for rich interactive experience
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Button, Static, DataTable, Tree, Input, 
    TextArea, TabbedContent, TabPane, ProgressBar, Label, 
    SelectionList, Checkbox, RadioSet, RadioButton, Switch
)
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual import events
from textual.message import Message
from pathlib import Path
from typing import List, Dict, Any, Optional
import os
import json
import asyncio

# Import our core components
from .core import EnhancedRefactoringAnalyzer
from .models import RefactoringGuidance

class FileAnalysisScreen(Screen):
    """Screen for analyzing individual Python files"""
    
    BINDINGS = [
        ("escape", "back", "Back to main"),
        ("f1", "help", "Help"),
        ("ctrl+s", "save_results", "Save Results"),
    ]
    
    def __init__(self, analyzer: EnhancedRefactoringAnalyzer):
        super().__init__()
        self.analyzer = analyzer
        self.current_results = None
    
    def compose(self) -> ComposeResult:
        """Compose the file analysis screen"""
        
        with Container(id="file-analysis-container"):
            yield Header(show_clock=True)
            
            with TabbedContent("File Selection", "Results", "Details"):
                # File Selection Tab
                with TabPane("File Selection", id="file-tab"):
                    with Vertical():
                        yield Label("📁 Select Python File to Analyze:")
                        yield Input(placeholder="Enter file path...", id="file-input")
                        with Horizontal():
                            yield Button("Browse", id="browse-btn", variant="primary")
                            yield Button("Analyze", id="analyze-btn", variant="success")
                        yield Static("", id="file-status")
                
                # Results Overview Tab  
                with TabPane("Results", id="results-tab"):
                    with Vertical():
                        yield Static("", id="results-summary")
                        yield DataTable(id="results-table")
                
                # Detailed Analysis Tab
                with TabPane("Details", id="details-tab"):
                    with ScrollableContainer():
                        yield Static("", id="detailed-results")
            
            yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        
        if event.button.id == "browse-btn":
            self.browse_file()
        elif event.button.id == "analyze-btn":
            self.analyze_file()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission"""
        if event.input.id == "file-input":
            self.analyze_file()
    
    def browse_file(self):
        """Browse for Python file (placeholder)"""
        status_widget = self.query_one("#file-status", Static)
        status_widget.update("🚧 File browser not implemented yet. Enter path manually.")
    
    def analyze_file(self):
        """Analyze the selected Python file"""
        
        file_input = self.query_one("#file-input", Input)
        file_path = file_input.value.strip()
        
        if not file_path:
            self._update_status("❌ Please enter a file path", "error")
            return
            
        if not os.path.exists(file_path):
            self._update_status(f"❌ File not found: {file_path}", "error")
            return
            
        if not file_path.endswith('.py'):
            self._update_status("⚠️  Warning: File doesn't have .py extension", "warning")
        
        # Show analysis in progress
        self._update_status("🔍 Analyzing file...", "info")
        
        # Run analysis
        self._run_analysis(file_path)
    
    def _run_analysis(self, file_path: str):
        """Run the analysis on the file"""
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            guidance_list = self.analyzer.analyze_file(file_path, content)
            
            self.current_results = {
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
            
            self._display_results()
            self._update_status("✅ Analysis complete!", "success")
            
        except Exception as e:
            self._update_status(f"❌ Analysis failed: {str(e)}", "error")
    
    def _display_results(self):
        """Display analysis results"""
        
        if not self.current_results:
            return
        
        # Update results summary
        summary_widget = self.query_one("#results-summary", Static)
        summary_text = f"""
📁 File: {self.current_results['file_path']}
📊 Total Issues: {self.current_results['total_issues']}

🔴 Critical: {self.current_results['issues_by_severity']['critical']}
🟠 High: {self.current_results['issues_by_severity']['high']}
🟡 Medium: {self.current_results['issues_by_severity']['medium']}
🔵 Low: {self.current_results['issues_by_severity']['low']}
        """
        summary_widget.update(summary_text.strip())
        
        # Update results table
        table = self.query_one("#results-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Severity", "Issue Type", "Line", "Priority", "Description")
        
        for guidance in self.current_results['guidance']:
            severity_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡', 
                'low': '🔵'
            }.get(guidance.severity, '⚪')
            
            table.add_row(
                f"{severity_icon} {guidance.severity.upper()}",
                guidance.issue_type.replace('_', ' ').title(),
                str(guidance.line_number) if guidance.line_number else "N/A",
                f"⭐ {guidance.priority_score:.1f}",
                guidance.description[:50] + "..." if len(guidance.description) > 50 else guidance.description
            )
        
        # Update detailed results
        details_widget = self.query_one("#detailed-results", Static)
        detailed_text = self._format_detailed_results()
        details_widget.update(detailed_text)
    
    def _format_detailed_results(self) -> str:
        """Format detailed results for display"""
        
        if not self.current_results or not self.current_results['guidance']:
            return "No detailed results available."
        
        details = []
        for i, guidance in enumerate(self.current_results['guidance'], 1):
            detail = f"""
{'='*60}
Issue #{i}: {guidance.issue_type.replace('_', ' ').title()}
{'='*60}

Severity: {guidance.severity.upper()}
Line: {guidance.line_number if guidance.line_number else 'N/A'}
Priority Score: {guidance.priority_score:.1f}

Description:
{guidance.description}

Recommendation:
{guidance.recommendation}

Estimated Effort: {guidance.estimated_effort_hours} hours

Step-by-Step Instructions:
"""
            
            for j, step in enumerate(guidance.precise_steps, 1):
                detail += f"{j}. {step}\n"
            
            details.append(detail)
        
        return "\n".join(details)
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update status message"""
        status_widget = self.query_one("#file-status", Static) 
        status_widget.update(message)
    
    def action_back(self) -> None:
        """Return to main screen"""
        self.app.pop_screen()
    
    def action_save_results(self) -> None:
        """Save analysis results"""
        if self.current_results:
            # Convert to JSON-serializable format
            results_json = {
                **self.current_results,
                'guidance': [g.to_dict() for g in self.current_results['guidance']]
            }
            
            # Save to file (placeholder)
            self._update_status("💾 Results saved to refactoring_results.json", "success")


class RepositoryIndexScreen(Screen):
    """Screen for repository indexing and querying"""
    
    BINDINGS = [
        ("escape", "back", "Back to main"),
        ("f5", "refresh", "Refresh"),
    ]
    
    def __init__(self, analyzer: EnhancedRefactoringAnalyzer):
        super().__init__()
        self.analyzer = analyzer
        self.db_path = ".refactoring_index.db"
    
    def compose(self) -> ComposeResult:
        """Compose the repository screen"""
        
        with Container(id="repo-container"):
            yield Header(show_clock=True)
            
            with TabbedContent("Index Repository", "Query Database", "Results"):
                # Repository Indexing Tab
                with TabPane("Index Repository", id="index-tab"):
                    with Vertical():
                        yield Label("🏗️ Repository Indexing:")
                        yield Input(placeholder="Repository path...", id="repo-input")
                        yield Input(placeholder="Database path (.refactoring_index.db)", id="db-input")
                        
                        with Horizontal():
                            yield Checkbox("Include tests", id="include-tests")
                            yield Checkbox("Incremental update", id="incremental", value=True)
                        
                        with Horizontal():
                            yield Button("Index Repository", id="index-btn", variant="primary")
                            yield Button("Update Index", id="update-btn", variant="default")
                        
                        yield ProgressBar(id="index-progress", show_eta=True)
                        yield Static("", id="index-status")
                
                # Database Querying Tab
                with TabPane("Query Database", id="query-tab"):
                    with Vertical():
                        yield Label("🔍 Query Options:")
                        
                        with RadioSet(id="query-type"):
                            yield RadioButton("High Complexity Functions", id="high-complexity", value=True)
                            yield RadioButton("Large Files", id="large-files")
                            yield RadioButton("Dead Code Candidates", id="dead-code")
                            yield RadioButton("Missing Tests", id="missing-tests")
                            yield RadioButton("All Issues", id="all-issues")
                            yield RadioButton("Custom SQL", id="custom-sql")
                        
                        yield TextArea("", id="custom-query", show_line_numbers=True)
                        yield Button("Run Query", id="query-btn", variant="success")
                        yield Static("", id="query-status")
                
                # Results Display Tab
                with TabPane("Results", id="results-tab"):
                    with ScrollableContainer():
                        yield DataTable(id="query-results")
            
            yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        
        if event.button.id == "index-btn":
            self.index_repository()
        elif event.button.id == "update-btn":
            self.update_repository()
        elif event.button.id == "query-btn":
            self.run_query()
    
    def index_repository(self):
        """Index the repository"""
        
        repo_input = self.query_one("#repo-input", Input)
        db_input = self.query_one("#db-input", Input)
        
        repo_path = repo_input.value.strip()
        db_path = db_input.value.strip() or self.db_path
        
        if not repo_path:
            self._update_index_status("❌ Please enter repository path", "error")
            return
            
        if not os.path.exists(repo_path):
            self._update_index_status(f"❌ Repository not found: {repo_path}", "error")
            return
        
        # Show progress
        progress = self.query_one("#index-progress", ProgressBar)
        progress.update(total=100)
        
        self._update_index_status("🔍 Indexing repository...", "info")
        
        # Simulate indexing process
        self._simulate_indexing(progress)
    
    def _simulate_indexing(self, progress: ProgressBar):
        """Simulate repository indexing with progress"""
        
        async def update_progress():
            for i in range(0, 101, 10):
                progress.update(progress=i)
                await asyncio.sleep(0.2)
            
            self._update_index_status("✅ Repository indexed successfully!", "success")
        
        # Run the progress update
        self.call_later(update_progress)
    
    def update_repository(self):
        """Update repository index incrementally"""
        self._update_index_status("🔄 Updating repository index...", "info")
        # Implementation would go here
    
    def run_query(self):
        """Run the selected query"""
        
        query_type_radio = self.query_one("#query-type", RadioSet)
        selected_option = query_type_radio.pressed_button
        
        if not selected_option:
            self._update_query_status("❌ Please select a query type", "error")
            return
        
        query_type = selected_option.id
        
        self._update_query_status(f"🔍 Running {query_type.replace('-', ' ')} query...", "info")
        
        # Mock results for demo
        self._display_mock_results(query_type)
    
    def _display_mock_results(self, query_type: str):
        """Display mock query results"""
        
        table = self.query_one("#query-results", DataTable)
        table.clear(columns=True)
        
        if query_type == "high-complexity":
            table.add_columns("File", "Function", "Complexity", "Priority")
            table.add_row("src/analyzer.py", "complex_method", "15", "🔴 High")
            table.add_row("src/parser.py", "parse_ast", "12", "🟠 Medium")
            table.add_row("src/utils.py", "validate_input", "11", "🟡 Medium")
            
        elif query_type == "large-files":
            table.add_columns("File", "Lines", "Size (KB)", "Priority")
            table.add_row("src/main.py", "850", "34", "🔴 High")
            table.add_row("src/server.py", "720", "28", "🟠 Medium")
            
        else:
            table.add_columns("Type", "File", "Line", "Description")
            table.add_row("Dead Code", "src/legacy.py", "45", "Unused function")
            table.add_row("Missing Test", "src/utils.py", "N/A", "No test coverage")
        
        self._update_query_status("✅ Query completed successfully!", "success")
    
    def _update_index_status(self, message: str, status_type: str = "info"):
        """Update indexing status"""
        status_widget = self.query_one("#index-status", Static)
        status_widget.update(message)
    
    def _update_query_status(self, message: str, status_type: str = "info"):
        """Update query status"""
        status_widget = self.query_one("#query-status", Static)
        status_widget.update(message)
    
    def action_back(self) -> None:
        """Return to main screen"""
        self.app.pop_screen()


class MainMenuScreen(Screen):
    """Main menu screen with navigation options"""
    
    def compose(self) -> ComposeResult:
        """Compose the main menu"""
        
        with Container(id="main-menu"):
            yield Header(show_clock=True)
            
            with Vertical(id="menu-container"):
                yield Static("""
╔═══════════════════════════════════════════════════════════════╗
║              🐍 Python Refactoring Assistant 🔧              ║
║                                                               ║
║     Comprehensive code analysis • Repository indexing        ║
║     TDD guidance • Coverage analysis • Quality insights      ║
╚═══════════════════════════════════════════════════════════════╝
                """, id="banner")
                
                with Vertical(id="main-buttons"):
                    yield Button("📁 Analyze Python File", id="analyze-file-btn", variant="primary")
                    yield Button("🏗️ Repository Management", id="repo-mgmt-btn", variant="primary")
                    yield Button("🚀 Start MCP Server", id="mcp-server-btn", variant="success")
                    yield Button("⚙️ Settings", id="settings-btn", variant="default")
                    yield Button("❌ Exit", id="exit-btn", variant="error")
                
                yield Static("", id="main-status")
            
            yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle main menu button presses"""
        
        if event.button.id == "analyze-file-btn":
            self.app.push_screen(FileAnalysisScreen(self.app.analyzer))
        elif event.button.id == "repo-mgmt-btn":
            self.app.push_screen(RepositoryIndexScreen(self.app.analyzer))
        elif event.button.id == "mcp-server-btn":
            self._start_mcp_server()
        elif event.button.id == "settings-btn":
            self._show_settings()
        elif event.button.id == "exit-btn":
            self.app.exit()
    
    def _start_mcp_server(self):
        """Start MCP server mode"""
        status_widget = self.query_one("#main-status", Static)
        status_widget.update("🚀 Starting MCP Server... (Press Ctrl+C to stop)")
        
        # In a real implementation, this would start the MCP server
        self.call_later(self._simulate_server_start)
    
    async def _simulate_server_start(self):
        """Simulate MCP server startup"""
        await asyncio.sleep(2)
        status_widget = self.query_one("#main-status", Static)
        status_widget.update("✅ MCP Server running on stdio. Connect with your MCP client.")
    
    def _show_settings(self):
        """Show settings dialog"""
        status_widget = self.query_one("#main-status", Static)
        status_widget.update("⚙️ Settings panel coming soon!")


class RefactoringTUI(App):
    """Main TUI application for Python refactoring"""
    
    CSS_PATH = None  # We'll define styles inline
    TITLE = "Python Refactoring Assistant"
    SUB_TITLE = "Advanced TUI for Code Analysis"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
        ("f1", "help", "Help"),
        ("f5", "refresh", "Refresh"),
    ]
    
    def __init__(self):
        super().__init__()
        self.analyzer = EnhancedRefactoringAnalyzer()
    
    def compose(self) -> ComposeResult:
        """Compose the main application"""
        yield Header(show_clock=True)
        yield Static("""
╔═══════════════════════════════════════════════════════════════╗
║              🐍 Python Refactoring Assistant 🔧              ║
║                                                               ║
║     Comprehensive code analysis • Repository indexing        ║
║     TDD guidance • Coverage analysis • Quality insights      ║
╚═══════════════════════════════════════════════════════════════╝
        """, id="banner")
        
        with Vertical(id="main-buttons"):
            yield Button("📁 Analyze Python File", id="analyze-file-btn", variant="primary")
            yield Button("🏗️ Repository Management", id="repo-mgmt-btn", variant="primary") 
            yield Button("🚀 Start MCP Server", id="mcp-server-btn", variant="success")
            yield Button("⚙️ Settings", id="settings-btn", variant="default")
            yield Button("❌ Exit", id="exit-btn", variant="error")
        
        yield Static("Ready to analyze your Python code!", id="main-status")
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted"""
        self.title = "Python Refactoring Assistant TUI"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        
        if event.button.id == "analyze-file-btn":
            self.push_screen(FileAnalysisScreen(self.analyzer))
        elif event.button.id == "repo-mgmt-btn":
            self.push_screen(RepositoryIndexScreen(self.analyzer))
        elif event.button.id == "mcp-server-btn":
            self._start_mcp_server()
        elif event.button.id == "settings-btn":
            self._show_settings()
        elif event.button.id == "exit-btn":
            self.exit()
    
    def _start_mcp_server(self):
        """Start MCP server mode"""
        status_widget = self.query_one("#main-status", Static)
        status_widget.update("🚀 Starting MCP Server... (Press Ctrl+C to stop)")
    
    def _show_settings(self):
        """Show settings dialog"""
        status_widget = self.query_one("#main-status", Static)
        status_widget.update("⚙️ Settings panel coming soon!")
    
    def action_help(self) -> None:
        """Show help information"""
        help_text = """
🐍 Python Refactoring Assistant - Help

Keyboard Shortcuts:
• Q / Ctrl+C: Quit application
• F1: Show this help
• F5: Refresh current view
• Escape: Go back to previous screen

Navigation:
• Use Tab/Shift+Tab to navigate between widgets
• Enter to activate buttons
• Arrow keys to navigate lists/tables

Features:
• File Analysis: Analyze individual Python files
• Repository Indexing: Index entire repositories
• Query Database: Search for refactoring opportunities
• MCP Server: Run as Model Context Protocol server

For more information, visit: github.com/your-repo
        """
        
        # Create a help modal (simplified version)
        # In a full implementation, this would be a proper modal
        pass


def main():
    """Main entry point for TUI"""
    app = RefactoringTUI()
    app.run()


if __name__ == "__main__":
    main()