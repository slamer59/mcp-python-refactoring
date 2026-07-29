---
name: python-refactoring
description: Analyze Python code for refactoring opportunities, complexity, dead code, security issues, modernization, test coverage gaps, and package-level structure — before proposing or making refactoring changes to Python code.
---

# Python Refactoring Assistant

This project ships `python-refactor-cli`, a CLI that wraps rope, radon, vulture,
pyrefly, mccabe, complexipy, bandit, pip-audit, and refurb into one set of
refactoring-analysis commands. Use it whenever you are about to refactor,
review, or assess the health of Python code in this repository.

## Primary usage: CLI

Prefer running the CLI directly via subprocess (e.g. the Bash tool) over
starting the MCP server for one-off analysis — it's faster and cheaper:

```bash
uv run python-refactor-cli <command> --format json ...
```

Every analysis command supports `--format json` for machine-parseable output.
Run `uv run python-refactor-cli <command> --help` for full option details.

## Command reference

| Command | Target | Use it to... |
|---|---|---|
| `analyze <file>` | file | Full refactoring analysis of a single file |
| `find-long-functions <file> [-t N]` | file | Find functions at/over N lines (candidates for extraction) |
| `extraction-guidance <file> [-fn NAME]` | file | Get step-by-step guidance for extracting a specific function |
| `test-coverage <source> [-t tests/]` | file/dir | Find files/functions missing test coverage |
| `tdd-guidance <file> [-fn NAME]` | file | Get Red-Green-Refactor guidance for a function |
| `security-scan <file>` | file | Scan for security vulnerabilities, vulnerable deps, and outdated patterns |
| `analyze-package <path>` | package/dir | Full structural analysis of a package |
| `package-metrics <path>` | package/dir | Complexity, cohesion, coupling, health score |
| `package-issues <path>` | package/dir | Structural issues (god package, circular deps, etc.) |
| `package-dependencies <path>` | package/dir | Dependency graph and circular-dependency detection |

Example:

```bash
uv run python-refactor-cli find-long-functions src/app.py --line-threshold 30 --format json
```

```json
{
  "total_functions_analyzed": 12,
  "long_functions_found": 2,
  "line_threshold": 30,
  "functions": [
    {"name": "process_order", "start_line": 40, "end_line": 95, "length": 56, "location": "lines 40-95"}
  ]
}
```

## Secondary/fallback: MCP server

If this environment is already running the tool as an MCP server
(`uv run python-refactor-cli server`), the same underlying analysis is
available as MCP tool calls instead of CLI subprocess calls:

| CLI command | MCP tool |
|---|---|
| `analyze` | `analyze_python_file` |
| `find-long-functions` | `find_long_functions` |
| `extraction-guidance` | `get_extraction_guidance` |
| `test-coverage` | `analyze_test_coverage` |
| `tdd-guidance` | `tdd_refactoring_guidance` |
| `security-scan` | `analyze_security_and_patterns` |
| `analyze-package` | `analyze_python_package` |
| `package-metrics` | `get_package_metrics` |
| `package-issues` | `find_package_issues` |

Only fall back to MCP tool calls when the CLI isn't reachable (e.g. no shell
access) — otherwise use the CLI.

## Workflow recipes

**Find and fix long functions:**
```bash
uv run python-refactor-cli find-long-functions src/app.py --format json
uv run python-refactor-cli extraction-guidance src/app.py --function-name process_order
```

**Pre-commit security check:**
```bash
uv run python-refactor-cli security-scan src/app.py --format table
```

**Assess a package before a larger refactor:**
```bash
uv run python-refactor-cli package-metrics src/mypackage --format json
uv run python-refactor-cli package-issues src/mypackage --format json
```
