#!/usr/bin/env python3
"""
MCP Python Refactoring Assistant Wrapper Script
Provides a convenient CLI interface for testing and running the MCP server.
Can be run with: uv run mcp_wrapper.py
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click>=8.0.0",
#     "mcp>=1.13.1",
#     "rope>=1.11.0",
#     "radon>=6.0.1", 
#     "vulture>=2.10",
#     "jedi>=0.19.1",
#     "libcst>=1.1.0",
#     "mccabe>=0.7.0",
#     "fastapi>=0.104.0",
#     "uvicorn>=0.24.0",
#     "pyrefly>=0.30.0",
#     "complexipy>=4.0.2",
# ]
# ///

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click

# Import the MCP server
try:
    from src.mcp_refactoring_assistant.mcp_server import run_server, EnhancedRefactoringAnalyzer
    MCP_AVAILABLE = True
except ImportError:
    try:
        # Fallback for when running as standalone script
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from mcp_refactoring_assistant.mcp_server import run_server, EnhancedRefactoringAnalyzer
        MCP_AVAILABLE = True
    except ImportError:
        MCP_AVAILABLE = False


@click.group(invoke_without_command=True)
@click.version_option(version="0.1.0", prog_name="mcp-python-refactoring")
@click.pass_context
def cli(ctx):
    """MCP Python Refactoring Assistant - Wrapper Script
    
    A convenient CLI for testing and running the MCP Python refactoring server.
    Defaults to starting the MCP server in STDIO mode if no command is provided.
    
    Examples:
        # Start MCP server (default behavior)
        uv run mcp_wrapper.py
        
        # Start MCP server with SSE on port 3001  
        uv run mcp_wrapper.py server --sse --port 3001
        
        # Analyze a Python file directly
        uv run mcp_wrapper.py analyze example.py
        
        # Test with example code
        uv run mcp_wrapper.py test
    """
    if not MCP_AVAILABLE:
        click.echo("❌ MCP server not available. Install dependencies first.", err=True)
        sys.exit(1)
    
    # If no command is provided, default to starting the server
    if ctx.invoked_subcommand is None:
        click.echo("🚀 Starting Python Refactoring MCP Server (default)")
        click.echo("📡 STDIO Mode: Listening on stdin/stdout")
        asyncio.run(run_server())


@cli.command()
@click.option('--sse', is_flag=True, help='Run in SSE mode instead of stdio')
@click.option('--port', default=3001, type=int, help='Port for SSE mode (default: 3001)')
@click.option('--host', default='0.0.0.0', help='Host for SSE mode (default: 0.0.0.0)')
def server(sse: bool, port: int, host: str):
    """Start the MCP Python Refactoring server.
    
    By default starts in stdio mode for MCP protocol communication.
    Use --sse flag to start HTTP server for web-based testing.
    """
    click.echo("🚀 Starting Python Refactoring MCP Server")
    
    if sse:
        click.echo(f"🌐 SSE Mode: http://{host}:{port}")
        sys.argv = ['mcp_wrapper.py', '--sse', str(port)]
    else:
        click.echo("📡 STDIO Mode: Listening on stdin/stdout")
        sys.argv = ['mcp_wrapper.py']
    
    asyncio.run(run_server())


@cli.command()
@click.argument('file_path', type=click.Path(exists=True), required=False)
@click.option('--content', help='Python code content to analyze directly')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress messages')
def analyze(file_path: Optional[str], content: Optional[str], output_json: bool, quiet: bool):
    """Analyze Python code for refactoring opportunities.
    
    Can analyze a file or direct code content.
    
    Examples:
        uv run mcp_wrapper.py analyze example.py
        uv run mcp_wrapper.py analyze --content "def long_function(): pass"
    """
    if not file_path and not content:
        click.echo("❌ Either provide a file path or --content", err=True)
        sys.exit(1)
    
    if file_path and content:
        click.echo("❌ Provide either file path OR content, not both", err=True)
        sys.exit(1)
    
    try:
        if file_path:
            if not quiet:
                click.echo(f"🔍 Analyzing file: {file_path}")
            with open(file_path, 'r') as f:
                code_content = f.read()
            analysis_file_path = file_path
        else:
            if not quiet:
                click.echo("🔍 Analyzing provided code content")
            code_content = content
            analysis_file_path = "inline_code.py"
        
        # Initialize analyzer
        analyzer = EnhancedRefactoringAnalyzer()
        guidance = analyzer.analyze_file(analysis_file_path, code_content)
        
        if output_json:
            # JSON output for programmatic use
            result = {
                "file": analysis_file_path,
                "analysis_summary": {
                    "total_issues": len(guidance),
                    "critical": len([g for g in guidance if g.severity == "critical"]),
                    "high": len([g for g in guidance if g.severity == "high"]),
                    "medium": len([g for g in guidance if g.severity == "medium"]),
                    "low": len([g for g in guidance if g.severity == "low"])
                },
                "issues": [g.to_dict() for g in guidance]
            }
            click.echo(json.dumps(result, indent=2))
        else:
            # Human-readable output
            if not guidance:
                click.echo("✅ No refactoring opportunities found!")
                return
            
            click.echo(f"\n📊 Analysis Results for {analysis_file_path}")
            click.echo("=" * 60)
            
            # Summary
            severities = {"critical": "🚨", "high": "⚠️", "medium": "💡", "low": "ℹ️"}
            for severity, icon in severities.items():
                count = len([g for g in guidance if g.severity == severity])
                if count > 0:
                    click.echo(f"{icon} {severity.title()}: {count}")
            
            click.echo("\n🔧 Refactoring Opportunities:")
            click.echo("-" * 40)
            
            for i, issue in enumerate(guidance, 1):
                severity_icon = severities.get(issue.severity, "•")
                click.echo(f"\n{i}. {severity_icon} {issue.issue_type.replace('_', ' ').title()}")
                click.echo(f"   📍 {issue.location}")
                click.echo(f"   📝 {issue.description}")
                
                if issue.benefits:
                    click.echo("   ✨ Benefits:")
                    for benefit in issue.benefits[:2]:  # Show first 2 benefits
                        click.echo(f"      • {benefit}")
                
                if issue.precise_steps:
                    click.echo("   📋 Next Steps:")
                    for step in issue.precise_steps[:3]:  # Show first 3 steps
                        if step.strip():
                            click.echo(f"      {step}")
                    if len(issue.precise_steps) > 3:
                        click.echo(f"      ... and {len(issue.precise_steps) - 3} more steps")
        
    except Exception as e:
        click.echo(f"❌ Analysis failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def test():
    """Run a quick test with example code to verify the server works."""
    
    # Example code with obvious refactoring opportunities
    test_code = '''
def process_data(data1, data2, data3, data4, data5, data6):
    """Function with multiple refactoring opportunities"""
    
    # This block could be extracted
    if not data1:
        print("Data1 missing")
        return None
    if len(data1) < 5:
        print("Data1 too short") 
        return None
    if not isinstance(data1, str):
        print("Data1 must be string")
        return None
        
    # Another extractable block
    result = data1.upper()
    result = result.strip()
    result = result.replace(" ", "_")
    
    # Yet another block
    for i in range(100):  # Long loop
        if i % 10 == 0:
            result += str(i)
            
    # Complex calculation block
    total = 0
    for i in range(data3):
        if i % 2 == 0:
            total += i * 0.1
        else:
            total -= i * 0.05
            
    return result, total
'''
    
    click.echo("🧪 Testing MCP Python Refactoring Assistant")
    click.echo("=" * 50)
    
    try:
        analyzer = EnhancedRefactoringAnalyzer()
        guidance = analyzer.analyze_file("test_example.py", test_code)
        
        if guidance:
            click.echo(f"✅ Test successful! Found {len(guidance)} refactoring opportunities:")
            
            for i, issue in enumerate(guidance[:3], 1):  # Show first 3 issues
                click.echo(f"\n{i}. {issue.issue_type.replace('_', ' ').title()}")
                click.echo(f"   📍 {issue.location}")
                click.echo(f"   📝 {issue.description}")
            
            if len(guidance) > 3:
                click.echo(f"\n... and {len(guidance) - 3} more issues found!")
                
            click.echo(f"\n💡 Run 'uv run mcp_wrapper.py analyze --content \"{test_code[:50]}...\"' for detailed analysis")
            
        else:
            click.echo("⚠️  No issues found - this might indicate a problem with the analyzer")
            
        click.echo("\n🚀 MCP Server is working correctly!")
        click.echo("   • Start server: uv run mcp_wrapper.py server")
        click.echo("   • Web interface: uv run mcp_wrapper.py server --sse")
        
    except Exception as e:
        click.echo(f"❌ Test failed: {str(e)}")
        click.echo("\nThis might indicate missing dependencies or configuration issues.")
        sys.exit(1)


@cli.command()
@click.option('--host', default='localhost', help='Inspector host (default: localhost)')
@click.option('--port', default=6274, help='Inspector port (default: 6274)')
def inspector(host: str, port: int):
    """Instructions for connecting to MCP Inspector.
    
    Provides the correct configuration for MCP Inspector to test this server.
    """
    script_path = Path(__file__).absolute()
    
    click.echo("🔍 MCP Inspector Configuration")
    click.echo("=" * 40)
    click.echo("\n1. Start MCP Inspector:")
    click.echo("   bunx @modelcontextprotocol/inspector")
    
    click.echo("\n2. In the inspector, use these settings:")
    click.echo(f"   📋 Command: uv")
    click.echo(f"   📋 Args: run {script_path}")
    click.echo(f"   📋 Env: (leave default)")
    click.echo(f"   📝 Note: Server starts by default, no 'server' command needed!")
    
    click.echo("\n3. Or test manually:")
    click.echo(f"   uv run {script_path} test")
    click.echo(f"   uv run {script_path} server --sse --port 3001")
    
    click.echo(f"\n🌐 Inspector should be available at: http://{host}:{port}")


if __name__ == "__main__":
    cli()