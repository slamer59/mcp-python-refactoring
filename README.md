# Python Refactoring Assistant MCP Tool

A Model Context Protocol (MCP) tool that analyzes Python code and provides **guided refactoring suggestions** without automatically changing your code. This tool acts as your refactoring mentor, providing precise step-by-step instructions for improving code quality.

## <¯ Key Features

- **= No Automatic Changes**: Analyzes and guides, never modifies your code
- **=Í Precise Line Numbers**: Exact instructions on which lines to cut/paste  
- **>à Multiple Analysis Tools**: Uses Rope, Radon, Vulture, Jedi, and LibCST
- ** Extract Method Guidance**: Detailed steps like VSCode's "Extract Method"
- **=Ê Complexity Analysis**: Identifies high-complexity functions needing refactoring
- **=Ñ Dead Code Detection**: Finds unused functions and variables
- **=Ë Step-by-Step Instructions**: Clear, actionable guidance for each refactoring

## =€ Installation

Initialize with uv (recommended):

```bash
# Clone or create project directory
mkdir mcp-refactoring-assistant
cd mcp-refactoring-assistant

# Initialize with uv
uv init .
uv add rope radon vulture jedi libcst mccabe mcp
```

Or with pip:

```bash
pip install rope radon vulture jedi libcst mccabe mcp
```

## =à MCP Tools Available

### 1. `analyze_python_file`
Comprehensive analysis of Python files for refactoring opportunities.

**Input:**
- `content` (required): Python file content as string
- `file_path` (optional): Path to the file for context

**Output:**
```json
{
  "analysis_summary": {
    "total_issues_found": 5,
    "critical_issues": 0,
    "high_priority": 2, 
    "medium_priority": 2,
    "low_priority": 1
  },
  "refactoring_guidance": [...],
  "tools_used": {
    "rope": true,
    "radon": true,
    "vulture": true
  }
}
```

### 2. `find_long_functions`
Identifies functions that exceed length thresholds and are candidates for extraction.

**Input:**
- `content` (required): Python file content
- `line_threshold` (optional): Minimum lines to consider long (default: 20)

**Output:**
```json
{
  "total_functions_analyzed": 8,
  "long_functions_found": 2,
  "functions": [
    {
      "name": "process_user_registration", 
      "start_line": 12,
      "end_line": 67,
      "length": 56,
      "location": "lines 12-67"
    }
  ]
}
```

### 3. `get_extraction_guidance`
Provides detailed step-by-step extraction guidance for specific functions.

**Input:**
- `content` (required): Python file content
- `function_name` (optional): Specific function to analyze

**Output:**
```json
{
  "extraction_opportunities": 1,
  "guidance": [
    {
      "issue_type": "extract_function",
      "severity": "medium", 
      "location": "Function 'process_user_registration' lines 12-67",
      "description": "Long function (56 lines) with extractable blocks",
      "precise_steps": ["=Ë PRECISION EXTRACTION PLAN:", "..."],
      "extractable_blocks": [...]
    }
  ]
}
```

## =¡ Example Usage

### LLM + MCP Tool Workflow

1. **LLM asks MCP**: "Find long functions in this code"
2. **MCP responds**: Here's what I found with precise locations
3. **LLM guides user**: "Cut lines 15-23, create function `validate_user_input()`, replace with function call"

### Sample Interaction

```python
# LLM calls: find_long_functions
{
  "total_functions_found": 1,
  "functions": [{
    "name": "process_user_registration",
    "lines": "12-67", 
    "length": 56,
    "recommended_extractions": 4
  }]
}

# LLM calls: get_extraction_guidance  
{
  "extractable_blocks": [
    {
      "block_id": 1,
      "location": "lines 15-23",
      "suggested_name": "validate_user_input",
      "parameters": ["user_data", "email", "password", "confirm_password"],
      "return_variables": ["validation_result"],
      "precise_steps": [
        " SELECT lines 15-23 (inclusive)",
        " CUT the selected lines (Ctrl+X)",
        "=Ý CREATE function above original: def validate_user_input(user_data, email, password, confirm_password):",
        "=Ý PASTE the cut code (Ctrl+V)",
        "=Ý ADD return: return validation_result",
        "= REPLACE cut location with: validation_result = validate_user_input(user_data, email, password, confirm_password)"
      ]
    }
  ]
}
```

## =' Refactoring Types Detected

| Type | Description | Severity | Guidance Provided |
|------|-------------|----------|------------------|
| **Extract Function** | Functions >20 lines | Medium | Precise line numbers, parameters, return values |
| **High Complexity** | Cyclomatic complexity >10 | High | Specific decision points to extract |
| **Too Many Parameters** | Functions with >5 parameters | Medium | Parameter grouping suggestions |
| **Dead Code** | Unused functions/variables | Low | Safe removal instructions |
| **Low Maintainability** | Maintainability index <20 | Medium | Specific improvement steps |

## <¯ Integration Examples

### VSCode Integration
The tool provides the same analysis as VSCode's "Extract Method" but as structured data:

```python
# What you get is equivalent to:
# 1. Select lines 15-23 in VSCode
# 2. Right-click ’ "Extract Method" (Ctrl+Shift+R)
# 3. VSCode suggests function name and parameters
# But as precise JSON data for LLMs to guide users
```

### Integration with Refactoring Tools

The MCP provides data that refactoring tools can use:
- **Rope** (Python): `rope.refactor.extract.ExtractMethod`
- **VSCode Python**: Language Server Protocol commands  
- **PyCharm**: Refactoring API calls
- **Custom Scripts**: Direct AST manipulation

## =Ê Analysis Capabilities

### Third-Party Libraries Used

| Library | Purpose | Capabilities |
|---------|---------|-------------|
| **Rope** | Professional refactoring | Extract Method, variable analysis, scope detection |
| **Radon** | Code metrics | Cyclomatic complexity, maintainability index |  
| **Vulture** | Dead code detection | Unused functions, variables, imports |
| **Jedi** | Semantic analysis | Code completion, definition analysis |
| **LibCST** | Syntax tree manipulation | Pattern matching, safe transformations |

### Quality Metrics

- **Cyclomatic Complexity**: Identifies complex functions (>10 = refactor needed)
- **Maintainability Index**: Scores code maintainability (0-100, <20 = needs work)
- **Function Length**: Flags long functions (>20 lines = extraction candidate)
- **Parameter Count**: Detects functions with too many parameters (>5 = simplify)

## =, Example Analysis

For the provided `examples/example_code.py`:

```bash
python src/mcp_refactoring_assistant/server.py examples/example_code.py
```

**Expected output:**
```
=== REFACTORING ANALYSIS ===

1. EXTRACT_FUNCTION [medium]
   Location: Function 'process_user_registration' lines 8-72
   Description: Long function (65 lines) with extractable blocks
   Steps:
     =Ë PRECISION EXTRACTION PLAN:
     <¯ BLOCK 1: Handle validation logic (7 statements)
     =Í EXACT LOCATION: Lines 11-25
      SELECT lines 11-25 (inclusive)
     =Ý CREATE function: validate_user_input(user_data, email, password, confirm_password)
     ... and 12 more steps

2. HIGH_COMPLEXITY [high]  
   Location: Function 'calculate_complex_score' at line 75
   Description: Function has high cyclomatic complexity: 12
   Steps:
     1. Identify decision points (if, for, while, except)
     2. Look for logical groupings of conditions
     ... and 3 more steps

3. DEAD_CODE [low]
   Location: Line 98
   Description: Unused function: unused_function  
   Steps:
     1. Verify 'unused_function' is truly unused
     2. Check if it's part of a public API
     ... and 2 more steps
```

## > How LLMs Use This Tool

The MCP tool is designed to work seamlessly with LLMs:

1. **Detection Phase**: LLM asks "What needs refactoring?"
2. **Analysis Phase**: MCP provides detailed analysis with metrics  
3. **Guidance Phase**: LLM interprets results and guides user step-by-step
4. **Execution Phase**: User follows precise cut/paste instructions
5. **Validation Phase**: User tests to ensure behavior is unchanged

### Benefits for LLMs

- **Structured Data**: JSON responses easy for LLMs to parse and explain
- **Precise Instructions**: Exact line numbers eliminate ambiguity  
- **Educational Focus**: Helps users learn refactoring patterns
- **Safe Guidance**: No automatic code changes, user maintains control
- **Professional Quality**: Uses same tools as popular IDEs

## >ê Testing

Test the tool with the provided example:

```bash
# Standalone mode (without MCP)
python src/mcp_refactoring_assistant/server.py examples/example_code.py

# MCP mode (requires MCP client)  
# Configure your MCP client to use this server
```

## =Ý Configuration

MCP server configuration in `mcp_server_config.json`:

```json
{
  "name": "python-refactoring-assistant",
  "version": "1.0.0", 
  "description": "MCP server for Python code refactoring guidance",
  "main": "src/mcp_refactoring_assistant/server.py",
  "mcp": {
    "capabilities": {
      "tools": ["analyze_python_file", "get_extraction_guidance", "find_long_functions"]
    }
  }
}
```

## > Contributing

This tool provides professional-grade refactoring analysis without modifying code. It's designed to:

- **Guide** developers through refactoring decisions
- **Educate** about code quality principles  
- **Provide** precise, actionable instructions
- **Integrate** with existing development workflows

Perfect for LLMs that need to help users improve code quality while maintaining full control over changes!

## =Ä License

MIT License - see LICENSE file for details.