# MCP Python Refactoring

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![Registry](https://img.shields.io/badge/MCP-Registry-blue.svg)](https://registry.modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-MCP_Catalog-2496ED.svg)](https://github.com/docker/mcp-registry)

**A Model Context Protocol (MCP) server that analyzes Python code and provides guided refactoring suggestions without automatically modifying your code.**

## Keywords
`python` `refactoring` `code-analysis` `mcp-server` `ai-assistant` `claude` `rope` `radon` `vulture` `jedi` `educational` `mentoring` `code-quality` `static-analysis` `complexity-analysis`

This tool integrates with AI coding assistants (Claude, ChatGPT, Cursor, etc.) to provide intelligent refactoring guidance. Instead of making automatic code changes, it gives you precise instructions on how to improve your Python code, acting as your refactoring mentor.

## What This Tool Does

**For AI Coding Assistants:**
- Provides structured JSON responses with refactoring opportunities
- Identifies long functions, high complexity code, and dead code
- Gives precise line numbers for extract method refactoring
- Uses professional tools for comprehensive analysis

**For Developers:**
- Get step-by-step refactoring instructions
- Maintain full control over code changes
- Learn refactoring patterns through guided practice
- Improve code quality systematically

## How It Differs

| Approach    | This Tool                                   | Traditional Refactoring Tools |
| ----------- | ------------------------------------------- | ----------------------------- |
| Integration | Works with any LLM/AI assistant             | IDE-specific or standalone    |
| Guidance    | Step-by-step instructions with line numbers | Automatic changes only        |
| Learning    | Educational approach teaches patterns       | No learning component         |
| Control     | Developer maintains full control            | Tool makes all decisions      |

## Registry Submissions

This MCP server is available across the entire MCP ecosystem:

### Official MCP Registry
**Published and Live**: [registry.modelcontextprotocol.io](https://registry.modelcontextprotocol.io/)
- Server name: `io.github.slamer59/mcp-python-refactoring`
- Discoverable by all MCP-compatible clients

### 🟡 Docker MCP Registry  
**Pull Request Submitted**: [docker/mcp-registry #207](https://github.com/docker/mcp-registry/pull/207)
- Will be available as `mcp/mcp-python-refactoring` on Docker Hub
- Includes enhanced security: signatures, SBOM, provenance tracking
- Integrated into Docker Desktop's MCP Toolkit

### 🟡 Awesome MCP Servers Lists
**Community Curated Lists**:
- [appcypher/awesome-mcp-servers #180](https://github.com/appcypher/awesome-mcp-servers/pull/180) - Development Tools section
- [punkpeye/awesome-mcp-servers #1321](https://github.com/punkpeye/awesome-mcp-servers/pull/1321) - Code Execution section

### 📦 Installation Options
Once all registries are live, users can discover via:
- **MCP catalog** - Official registry search
- **Docker Desktop** - MCP Toolkit integration  
- **Community lists** - GitHub awesome lists
- **Docker Hub** - `mcp/mcp-python-refactoring` (with enhanced security)

## Docker Support

### Using with Docker MCP Catalog

```bash
# Pull from Docker Hub (after registry approval)
docker run -i mcp/mcp-python-refactoring

# Or build locally
docker build -t mcp-python-refactoring .
docker run -i mcp-python-refactoring
```

### Dockerfile

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package
RUN pip install --no-cache-dir -e .

# Expose MCP server port (optional, for documentation)
EXPOSE 3000

# Run the MCP server
ENTRYPOINT ["python-refactor", "server"]
```

## Installation

### Quick Start with uvx (Recommended)

```bash
# Install and run MCP server directly from GitHub
uvx --from git+https://github.com/slamer59/mcp-python-refactoring.git python-refactor server
```

### Add to Claude Code (One Command)

```bash
# Add to Claude Code MCP configuration
claude-code mcp add mcp-python-refactoring uvx --from git+https://github.com/slamer59/mcp-python-refactoring.git python-refactor server
```

After running this command, restart Claude Desktop and the Python refactoring tools will be available in your Claude conversations!

### Development Installation

```bash
# Clone and setup for development
git clone https://github.com/slamer59/mcp-python-refactoring.git
cd mcp-python-refactoring
uv sync

# Run MCP server locally
python -m mcp_refactoring_assistant server

# Or use the entry point after installation
pip install -e .
python-refactor server
```

## Available MCP Tools

### Unified Server

**Single Server**: Both guide-only and apply-changes modes in one server

**Connection Options**:
- **stdin/stdout**: `python-refactor server` (default)
- **Module execution**: `python -m mcp_refactoring_assistant server`

### Tools

#### 1. `analyze_python_code`
Comprehensive analysis with optional automatic refactoring.

**Parameters:**
- `content` (required): Python file content as string
- `mode` (optional): "guide_only" (default) or "apply_changes"
- `file_path` (optional): Path to the file for context
- `line_threshold` (optional): Minimum lines for long functions (default: 20)

**Mode: guide_only** - Returns instructions only
**Mode: apply_changes** - Returns modified code

#### 2. `extract_function`
Extract specific functions with guide or apply mode.

**Parameters:**
- `content` (required): Python file content
- `mode` (optional): "guide_only" or "apply_changes" 
- `function_name` (optional): Specific function to target
- `start_line`, `end_line` (for apply_changes): Exact extraction range
- `new_function_name` (for apply_changes): Name for extracted function

#### 3. `quick_analyze`
Fast analysis for immediate refactoring opportunities.

**Parameters:**
- `content` (required): Python file content

**Returns:** Quick summary of long functions and parameter issues

#### 4. `check_types_with_pyrefly`
Advanced type checking and quality analysis using pyrefly.

**Parameters:**
- `content` (required): Python code content to type check

**Returns:** Detailed type errors, quality issues, and improvement suggestions

#### 5. `get_server_capabilities` (Internal)
Returns server capabilities and available analysis tools.

**Returns:** List of available tools: rope, radon, vulture, jedi, libcst, pyrefly, mccabe, complexipy

## Analysis Capabilities

**Code Quality Issues Detected:**
- Functions over 20 lines (extract method opportunities)
- High cyclomatic complexity (>10) using McCabe analysis
- High cognitive complexity (>15) using Complexipy analysis
- Functions with too many parameters (>5)
- Dead/unused code (consolidated suggestions) via Vulture
- Low maintainability index (<20) using Radon metrics
- Type annotation problems detected by Pyrefly
- Large files (>500 lines) with module splitting recommendations
- Files with too many imports (>20) suggesting restructuring

**Additional Analysis Tools:**
- **Security Analysis**: Vulnerability detection and security best practices
- **Performance Analysis**: Bottleneck identification and optimization suggestions
- **Type Hints**: Missing type annotation detection
- **Documentation**: Docstring coverage and quality assessment

**Professional Tools Used:**
- **[Rope](https://github.com/python-rope/rope)**: Professional refactoring analysis and extract method detection
- **[Radon](https://github.com/rubik/radon)**: Code complexity metrics (cyclomatic, maintainability index)
- **[Vulture](https://github.com/jendrikseipp/vulture)**: Dead code detection and unused import analysis
- **[Jedi](https://github.com/davidhalter/jedi)**: Semantic code analysis and variable tracking
- **[LibCST](https://github.com/Instagram/LibCST)**: Syntax tree manipulation for precise code analysis
- **[Pyrefly](https://github.com/Khronos16/pyrefly)**: Advanced type checking and quality analysis
- **[McCabe](https://github.com/PyCQA/mccabe)**: Cyclomatic complexity measurement
- **[Complexipy](https://github.com/rohaquinlop/complexipy)**: Advanced complexity analysis and cognitive complexity
- **Built-in File Analysis**: File size analysis and module splitting recommendations

## Testing and Debugging

### Test with MCP Inspector

```bash
# Launch MCP Inspector
bunx @modelcontextprotocol/inspector

# In the web interface:
# Command: python
# Args: -m mcp_refactoring_assistant server
# Working Directory: /path/to/your/project
```

**Test Both Modes in Inspector:**

**Guide Mode Test:**
```json
{
  "content": "def long_function():\n    print('line1')\n    # ... 20+ lines",
  "mode": "guide_only"
}
```

**Apply Mode Test:**
```json
{
  "content": "def long_function():\n    print('line1')\n    # ... 20+ lines", 
  "mode": "apply_changes"
}
```

### Test with Bun (Fastest)

```bash
# Install Bun if not available
curl -fsSL https://bun.sh/install | bash

# Install MCP SDK
bun install -g @modelcontextprotocol/sdk

# Run tests
export PATH=.venv/bin:$PATH && bun run test_unified.js
```

### Test Standalone (No MCP)

```bash
# Simple Python test
python test_tool.py

# Test with example file
python -m mcp_refactoring_assistant --help
```

### Debug Server Issues

```bash
# Check dependencies
uv sync

# Verify MCP imports
python -c "import mcp; print('MCP available')"

# Test individual tools
python -c "
from src.mcp_refactoring_assistant.server import EnhancedRefactoringAnalyzer
analyzer = EnhancedRefactoringAnalyzer()
print('Analyzer working')
"
```

## Example Usage

### Educational Workflow
1. AI assistant calls `analyze_python_code` with `guide_only` mode
2. Tool returns structured suggestions with precise steps
3. Developer follows step-by-step instructions
4. Developer learns refactoring patterns through practice

### Productivity Workflow  
1. AI assistant calls `analyze_python_code` with `apply_changes` mode
2. Tool returns modified code with applied refactorings
3. Developer reviews changes and applies as needed
4. Faster refactoring for experienced developers

### Sample MCP Response (Guide Mode)

```json
{
  "analysis_summary": {
    "total_issues_found": 2,
    "medium_priority": 1,
    "low_priority": 1
  },
  "refactoring_guidance": [
    {
      "issue_type": "extract_function",
      "location": "Function 'process_data' lines 45-78",
      "description": "Long function (34 lines) with extractable blocks",
      "precise_steps": [
        "SELECT lines 45-52 (validation block)",
        "CREATE function: validate_input(data)",
        "REPLACE with: is_valid = validate_input(data)"
      ]
    },
    {
      "issue_type": "dead_code", 
      "location": "Multiple locations (6 items)",
      "description": "6 unused items found",
      "precise_steps": [
        "Review all unused items listed below:",
        "• Line 11: Unused import 're'",
        "• Line 12: Unused import 'Optional'",
        "Verify each item is truly unused",
        "Remove confirmed unused code"
      ]
    }
  ]
}
```

## Integration with Coding Assistants

### Claude Code/CLI
Add to your MCP configuration:

```json
{
  "servers": {
    "python-refactoring": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/slamer59/mcp-python-refactoring.git", "python-refactor", "server"]
    }
  }
}
```

Or for local installation:

```json
{
  "servers": {
    "python-refactoring": {
      "command": "python",
      "args": ["-m", "mcp_refactoring_assistant", "server"]
    }
  }
}
```

### Claude Desktop
Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "python-refactoring": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/slamer59/mcp-python-refactoring.git", "python-refactor", "server"]
    }
  }
}
```

Or for local installation:

```json
{
  "mcpServers": {
    "python-refactoring": {
      "command": "python",
      "args": ["-m", "mcp_refactoring_assistant", "server"]
    }
  }
}
```

### Cline (VSCode Extension)
In VSCode settings or `.vscode/settings.json`:

```json
{
  "cline.mcpServers": {
    "python-refactoring": {
      "command": "python",
      "args": ["-m", "mcp_refactoring_assistant", "server"]
    }
  }
}
```

### Cursor
Add to Cursor's MCP configuration:

```json
{
  "mcpServers": {
    "python-refactoring": {
      "command": "python",
      "args": ["-m", "mcp_refactoring_assistant", "server"]
    }
  }
}
```

### Continue (VSCode Extension)
In `~/.continue/config.json`:

```json
{
  "mcpServers": [
    {
      "name": "python-refactoring",
      "command": "python",
      "args": ["-m", "mcp_refactoring_assistant", "server"]
    }
  ]
}
```

### Windsurf
Add to Windsurf MCP configuration:

```json
{
  "servers": {
    "python-refactoring": {
      "command": "python",
      "args": ["-m", "mcp_refactoring_assistant", "server"]
    }
  }
}
```

### Aider
Use with MCP bridge or direct integration:

```bash
aider --mcp-server "python -m mcp_refactoring_assistant server"
```

### OpenHands (formerly OpenDevin)
In OpenHands configuration:

```yaml
mcp_servers:
  python-refactoring:
    command: python
    args: ["-m", "mcp_refactoring_assistant", "server"]
```

### Roo-Code
Add to Roo-Code's MCP settings:

```json
{
  "mcpServers": {
    "python-refactoring": {
      "command": "python",
      "args": ["-m", "mcp_refactoring_assistant", "server"]
    }
  }
}
```

### Codex CLI
Add to `~/.codex/config.toml`:

```toml
[mcp_servers.python-refactoring]
command = "python"
args = ["-m", "mcp_refactoring_assistant", "server"]
```

### Terminal-based clients
For most terminal-based MCP clients:

```bash
# With uvx
client-name --mcp-server "uvx --from git+https://github.com/slamer59/mcp-python-refactoring.git python-refactor server"

# With local installation  
client-name --mcp-server "python -m mcp_refactoring_assistant server"
```

### SSE Mode (Web-based clients)
For web-based clients that support SSE connections:

1. Start the server in SSE mode:
```bash
# SSE mode is not currently supported
# Use stdin/stdout mode instead
python-refactor server
```

2. Use stdin/stdout connection instead of SSE

### Using with mcpo (ChatGPT and others)
For clients without native MCP support:

```bash
# Install mcpo
pip install mcpo

# Bridge MCP to OpenAI-compatible API
mcpo --mcp-server "python -m mcp_refactoring_assistant server" --port 8080
```

Then configure your client to use `http://localhost:8080` as API endpoint.

### Notes

- Use `python -m mcp_refactoring_assistant server` for local installations
- For uvx installation, use the full uvx command instead of local paths
- Some clients may require additional configuration or have different syntax
- Always use absolute paths when specifying python executable
- Test the connection with the client's MCP debugging tools if available

## How It Works

1. **Analysis**: Server analyzes Python code using multiple professional tools
2. **Detection**: Identifies specific refactoring opportunities with metrics
3. **Guidance**: Provides precise line numbers and step-by-step instructions
4. **Integration**: AI assistant interprets results and guides developer
5. **Control**: Developer maintains full control over all code changes

## User Feedback

Users report significant improvements in code quality understanding and refactoring skills when using this tool with AI assistants. The guided approach helps developers learn refactoring patterns while maintaining control over code changes.

*"Finally, a tool that teaches me refactoring instead of doing it for me"*  
*"The precise line numbers make it easy to follow the suggestions"*  
*"Game changer for working with legacy code"*

## Troubleshooting

**MCP Connection Issues:**
- Ensure all dependencies installed: `uv sync`
- Check Python path: `which python`
- Verify MCP import: `python -c "import mcp"`

**Analysis Not Working:**
- Test analyzer directly: `python test_tool.py`
- Check file permissions
- Verify example file exists: `ls examples/`

**Tool Responses Empty:**
- Check if code has functions to analyze (minimum complexity threshold)
- Increase line threshold for testing: `"line_threshold": 10`
- Verify file syntax is valid Python
- Ensure virtual environment is activated

**SSE Connection Issues:**
- Verify port is not in use: `netstat -an | grep 3001`
- Check firewall settings for local connections
- Ensure FastAPI and Uvicorn are installed: `uv add fastapi uvicorn`

**Performance Issues:**
- For large codebases (>100 files), consider using file-specific analysis
- Increase timeout settings in MCP client configuration
- Use `quick_analyze` for immediate feedback on specific functions

### Community Registries

Submit to awesome lists and community catalogs:
- [MCPServers.org](https://mcp.so/) - Create GitHub issue
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers) - Submit PR
- [Wong2's Awesome List](https://github.com/wong2/awesome-mcp-servers) - Submit PR

## License

MIT License - Free for personal and commercial use.
