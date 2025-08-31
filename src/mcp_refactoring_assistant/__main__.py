#!/usr/bin/env python3
"""
Main entry point for Python Refactoring Assistant
Supports multiple modes: CLI, TUI, and MCP Server
"""

import sys
import os
from typing import Optional

def main():
    """Main entry point with mode detection"""
    
    # Check for MCP server mode (when called via stdio)
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        # Running as MCP server
        try:
            from .server import main as mcp_main
            import asyncio
            asyncio.run(mcp_main())
        except ImportError:
            print("❌ MCP not available. Install with: pip install mcp", file=sys.stderr)
            sys.exit(1)
        return
    
    # Check for explicit mode arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "server":
            # Explicit MCP server mode
            try:
                from .server import main as mcp_main
                import asyncio
                asyncio.run(mcp_main())
            except ImportError:
                print("❌ MCP not available. Install with: pip install mcp", file=sys.stderr)
                sys.exit(1)
            return
            
        elif mode == "tui":
            # Explicit TUI mode
            try:
                from .tui import main as tui_main
                tui_main()
            except ImportError:
                print("❌ Textual not available. Install with: pip install textual", file=sys.stderr)
                sys.exit(1)
            return
            
        elif mode in ["cli", "help", "--help", "-h"]:
            # Explicit CLI mode or help
            from .cli import cli
            sys.argv = sys.argv[1:]  # Remove the mode argument
            cli()
            return
    
    # Default to CLI mode
    from .cli import cli
    cli()


if __name__ == "__main__":
    main()