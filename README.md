# Python Refactoring Assistant MCP Server

**A Model Context Protocol (MCP) server that analyzes Python code and provides guided refactoring suggestions without automatically modifying your code.**

This tool integrates with AI coding assistants (Claude, ChatGPT, Cursor, etc.) to provide intelligent refactoring guidance. Instead of making automatic code changes, it gives you precise instructions on how to improve your Python code, acting as your refactoring mentor.

## 🎯 What This Tool Does

**For AI Coding Assistants:**
- Provides structured JSON responses with refactoring opportunities
- Identifies long functions, high complexity code, and dead code
- Gives precise line numbers for extract method refactoring
- Uses professional tools (Rope, Radon, Vulture) for analysis

**For Developers:**
- Get step-by-step refactoring instructions
- Maintain full control over code changes
- Learn refactoring patterns through guided practice
- Improve code quality systematically

## 🚀 Installation

### Quick Start with uvx (Recommended)

```bash
# Install and run directly from GitHub
uvx --from git+https://github.com/slamer59/mcp-refactoring-assistant.git mcp-refactoring-assistant
```

### Development Installation

```bash
# Clone and setup for development
git clone https://github.com/slamer59/mcp-refactoring-assistant.git
cd mcp-refactoring-assistant
uv sync
```

### Manual Installation

```bash
# With uv
uv add rope radon vulture jedi libcst mccabe mcp fastapi uvicorn

# With pip
pip install rope radon vulture jedi libcst mccabe mcp fastapi uvicorn
```

## 🔧 Available MCP Tools

### 🎯 Unified Server

**Single Server** (`mcp_server.py`): Both guide-only and apply-changes modes in one server

**Connection Options**:
- **stdin/stdout**: `python mcp_server.py` (default)
- **SSE (Server-Sent Events)**: `python mcp_server.py --sse [port]` (web-based)

### Available Tools

### 1. `analyze_python_code`
Comprehensive analysis with optional automatic refactoring.

**Parameters:**
- `content` (required): Python file content as string
- `mode` (optional): "guide_only" (default) or "apply_changes"
- `file_path` (optional): Path to the file for context
- `line_threshold` (optional): Minimum lines for long functions (default: 20)

**Mode: guide_only** - Returns instructions only
**Mode: apply_changes** - Returns modified code

### 2. `extract_function_hybrid`
Extract specific functions with guide or apply mode.

**Parameters:**
- `content` (required): Python file content
- `mode` (optional): "guide_only" or "apply_changes" 
- `function_name` (optional): Specific function to target
- `start_line`, `end_line` (for apply_changes): Exact extraction range
- `new_function_name` (for apply_changes): Name for extracted function

### 3. `quick_analyze`
Fast analysis for immediate refactoring opportunities.

**Parameters:**
- `content` (required): Python file content

**Returns:** Quick summary of long functions and parameter issues

## 🧪 Testing and Debugging

### Test with MCP Inspector

```bash
# Launch MCP Inspector
bunx @modelcontextprotocol/inspector

# In the web interface:
# Command: python
# Args: mcp_server.py
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
python mcp_server.py examples/example_code.py
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

## 📊 Example Usage

### With AI Coding Assistants

1. **AI asks:** "Find long functions in this code"
2. **MCP responds:** JSON with precise function locations
3. **AI guides:** "Cut lines 15-23, create function `validate_input()`, replace with call"
4. **Developer follows:** Exact cut/paste instructions
5. **Result:** Code refactored without automatic changes

### Sample MCP Response

```json
{
  "analysis_summary": {
    "total_issues_found": 3,
    "medium_priority": 2,
    "low_priority": 1
  },
  "refactoring_guidance": [
    {
      "issue_type": "extract_function",
      "location": "Function 'process_data' lines 45-78",
      "description": "Long function (34 lines) with extractable blocks",
      "precise_steps": [
        "📋 EXTRACTION PLAN:",
        "✂️ SELECT lines 45-52 (validation block)",
        "📝 CREATE function: validate_input(data)",
        "🔄 REPLACE with: is_valid = validate_input(data)"
      ]
    }
  ]
}
```

## 🔌 Integration with Coding Assistants

### Claude Desktop/CLI
Add to your MCP configuration:

```json
{
  "servers": {
    "python-refactoring": {
      "command": "python",
      "args": ["path/to/mcp_server.py"]
    }
  }
}
```

### Cursor/VSCode
Use with MCP-compatible extensions that support custom servers.

### Direct Integration
The server works with any MCP-compatible client via stdin/stdout.

## 🛠️ Analysis Capabilities

**Code Quality Issues Detected:**
- Functions over 20 lines (extract method opportunities)
- High cyclomatic complexity (>10)
- Functions with too many parameters (>5)
- Dead/unused code
- Low maintainability index (<20)

**Professional Tools Used:**
- **Rope**: Professional refactoring analysis
- **Radon**: Code complexity metrics
- **Vulture**: Dead code detection
- **Jedi**: Semantic code analysis
- **LibCST**: Syntax tree manipulation

## 🤝 How It Works

1. **Analysis**: Server analyzes Python code using multiple professional tools
2. **Detection**: Identifies specific refactoring opportunities with metrics
3. **Guidance**: Provides precise line numbers and step-by-step instructions
4. **Integration**: AI assistant interprets results and guides developer
5. **Control**: Developer maintains full control over all code changes

## 📝 Example Sessions

### 📋 Guide Mode (Default - Recommended)

```bash
# AI calls with guide mode
{
  "tool": "analyze_python_code",
  "arguments": {"content": "...", "mode": "guide_only"}
}

# MCP responds with instructions
{
  "mode": "guide_only",
  "analysis_summary": {"total_issues_found": 2},
  "refactoring_guidance": [
    {
      "issue_type": "extract_function",
      "location": "Function 'process_data' lines 15-45",
      "precise_steps": [
        "✂️ SELECT lines 15-23 (validation block)",
        "📝 CREATE function: validate_input(data)",
        "🔄 REPLACE with: is_valid = validate_input(data)"
      ]
    }
  ]
}

# AI guides developer step-by-step
"Cut lines 15-23, create validate_input() function, replace with function call."
```

### ⚡ Apply Mode (Auto-Refactoring)

```bash
# AI calls with apply mode
{
  "tool": "analyze_python_code", 
  "arguments": {"content": "...", "mode": "apply_changes"}
}

# MCP responds with modified code
{
  "mode": "apply_changes",
  "changes_applied": 1,
  "new_code": "def validate_input(data):\n    # extracted code\n\ndef process_data(data):\n    is_valid = validate_input(data)\n    # rest of function",
  "applied_extractions": [
    {
      "function_name": "validate_input",
      "location": "lines 15-23",
      "summary": "Extracted validation logic"
    }
  ]
}

# AI shows result to developer
"I've automatically extracted validation logic into validate_input(). Here's the refactored code."
```

## 🐛 Troubleshooting

**MCP Connection Issues:**
- Ensure all dependencies installed: `uv sync`
- Check Python path: `which python`
- Verify MCP import: `python -c "import mcp"`

**Analysis Not Working:**
- Test analyzer directly: `python test_tool.py`
- Check file permissions
- Verify example file exists: `ls examples/`

**Tool Responses Empty:**
- Increase line threshold for testing
- Check code has actual functions to analyze
- Verify file syntax is valid Python

## 📄 License

MIT License - Free for personal and commercial use.

---

**Ready to improve your Python code quality with AI-guided refactoring!** 🚀