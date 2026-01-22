# RefactorOps Development Plan (Option 1: In-Repo Package)

This plan captures the agreed path to implement RefactorOps inside the existing
`mcp_refactoring_assistant` package. It is client-neutral (OpenCode/Codex/CI)
and excludes Claude Code plugin packaging for now.

## Scope

- Build RefactorOps core + MCP server + CLI/CI gate.
- Use deterministic static metrics only (ruff, jscpd, dead code, complexity).
- No auto clone removal or LSP integration.
- Claude Code plugin files are deferred.

## Target Layout

- Core: `src/mcp_refactoring_assistant/refactorops/`
- MCP server: `src/mcp_refactoring_assistant/refactorops/mcp_server.py`
- CLI runner: `src/mcp_refactoring_assistant/refactorops/cli.py`
- Tests: `tests/unit/refactorops/` and `tests/functional/refactorops/`
- Fixtures: `tests/fixtures/refactorops/`, `tests/fixtures/sample_repo/`

## Phases

### Phase 1: Standard Schema + Determinism

- Implement Pydantic schema models:
  - `Run`, `Scope`, `Budgets`, `Metrics`, `Finding`, `Hotspot`, `Summary`, `RepoQualityResult`
- Implement deterministic sort and dedup logic:
  - Dedup key: `(category, file, start.line, rule_id)` then message hash fallback
  - Merge evidence for overlapping findings as specified
- Tests:
  - Schema serialize/deserialize
  - Dedup key precedence and merge behavior

### Phase 2: Scope Resolution

- Implement `repo|changed|paths` scope resolution
- Changed scope uses `git diff --name-only base...head`
- Exclusions: `venv`, `node_modules`, `dist`, `build`, `__pycache__`, generated/binary
- Empty changed scope does not auto-expand to repo
- Tests for git parsing and exclusions (mock subprocess)

### Phase 3: Safe Command Execution Layer

- Allowlist commands: `ruff`, `git`, `python`, `jscpd`, `npx`
- Force `cwd=repo_root` and timeout
- Return structured failures (no uncaught exceptions across MCP)
- Tests for allowlist/timeout/exit codes (mock subprocess)

### Phase 4: Ruff Adapter

- `run_ruff_check` -> findings + `metrics.ruff`
- `run_ruff_fix_safe` -> patch/diff by default, optional apply
- Missing ruff -> structured `dependency_missing`
- Tests with fixture JSON mapping and safe-fix behavior

### Phase 5: jscpd Adapter

- Detect `jscpd` then optional `npx jscpd`
- Missing dep -> structured `dependency_missing`
- Parse JSON -> `metrics.duplication` + clone findings
- Fragment inclusion size-limited or optional
- Tests with fixture JSON mapping + missing dep

### Phase 6: Dead Code + Complexity

- Dead code: vulture scan across scoped files
- Complexity: radon cyclomatic + AST long function; complexipy if available
- Produce metrics + findings with stable thresholds
- Tests for thresholds and mappings

### Phase 7: Orchestrator (analyze_repo_quality)

- Resolve scope -> run modes
- Run ruff/dead/complexity in parallel; jscpd separately
- Enforce budgets (timeout, max_findings)
- Dedup findings, compute hotspots (dup 0.5, ruff 0.3, complexity 0.2)
- Summary status + gate reasons (baseline delta in CLI/CI)
- Snapshot test with `tests/fixtures/sample_repo/`

### Phase 8: MCP Server + CLI + CI Gate

- MCP server exposes:
  - `analyze_repo_quality`, `run_ruff_check`, `run_ruff_fix_safe`, `run_jscpd`, `dead_code_scan`
- CLI provides:
  - `refactorops analyze` (JSON output)
  - `refactorops gate` (baseline delta gate, exit code)
- CI workflow uploads JSON artifact and applies gate

## Definition of Done

- `analyze_repo_quality` returns ruff, duplication, dead code, complexity, hotspots
- Missing deps do not crash (clear `dependency_missing` output)
- Snapshot integration test passes
- ruff check/format pass
- Single doc covers install/use/CI (plugin docs excluded)

## Notes

- Keep existing MCP tools intact; RefactorOps tools are separate.
- Output schema is client-neutral and deterministic.
- Claude Code plugin packaging is intentionally deferred.
