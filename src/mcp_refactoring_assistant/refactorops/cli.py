#!/usr/bin/env python3
"""RefactorOps CLI entrypoints."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .tools import analyze_repo_quality


@dataclass
class GateResult:
    status: Literal["pass", "warn", "fail"]
    reasons: List[str]
    metrics: Dict[str, Any]


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="refactorops")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Run RefactorOps analysis")
    analyze_parser.add_argument("--repo-root", default=".")
    analyze_parser.add_argument("--scope-type", choices=["repo", "changed", "paths"], default="repo")
    analyze_parser.add_argument("--paths", nargs="*", default=[])
    analyze_parser.add_argument("--base", default="origin/main")
    analyze_parser.add_argument("--head", default="HEAD")
    analyze_parser.add_argument("--modes", default="")
    analyze_parser.add_argument("--timeout-sec", type=int, default=120)
    analyze_parser.add_argument("--max-findings", type=int, default=2000)
    analyze_parser.add_argument("--out", default="")

    analyze_parser.add_argument("--ruff-select", default="")
    analyze_parser.add_argument("--ruff-ignore", default="")

    analyze_parser.add_argument("--jscpd-min-lines", type=int, default=10)
    analyze_parser.add_argument("--jscpd-min-tokens", type=int, default=50)
    analyze_parser.add_argument("--jscpd-ignore", default="")
    analyze_parser.add_argument("--jscpd-use-npx", action="store_true")
    analyze_parser.add_argument("--jscpd-no-gitignore", action="store_true")
    analyze_parser.add_argument("--jscpd-follow-symlinks", action="store_true")
    analyze_parser.add_argument("--jscpd-include-fragments", action="store_true")
    analyze_parser.add_argument("--jscpd-max-fragment-chars", type=int, default=2000)

    analyze_parser.add_argument("--dead-code-min-confidence", type=int, default=80)
    analyze_parser.add_argument("--dead-code-include-low", action="store_true")

    analyze_parser.add_argument("--max-cyclomatic", type=int, default=10)
    analyze_parser.add_argument("--max-cognitive", type=int, default=15)
    analyze_parser.add_argument("--max-function-lines", type=int, default=30)

    gate_parser = subparsers.add_parser("gate", help="Evaluate RefactorOps gate")
    gate_parser.add_argument("--baseline", default="refactorops-baseline.json")
    gate_parser.add_argument("--current", required=True)
    gate_parser.add_argument("--duplication-delta", type=float, default=0.2)
    gate_parser.add_argument("--strict", action="store_true")
    gate_parser.add_argument("--max-cyclomatic", type=int, default=10)
    gate_parser.add_argument("--max-cognitive", type=int, default=15)
    gate_parser.add_argument("--max-function-lines", type=int, default=30)
    gate_parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    if args.command == "analyze":
        _run_analyze(args)
        return
    if args.command == "gate":
        _run_gate(args)
        return


def _run_analyze(args: argparse.Namespace) -> None:
    scope = {
        "type": args.scope_type,
        "paths": args.paths,
    }
    if args.scope_type == "changed":
        scope["git"] = {"base": args.base, "head": args.head}

    modes = _split_csv(args.modes)
    options: Dict[str, Any] = {
        "ruff": {
            "select": _split_csv(args.ruff_select),
            "ignore": _split_csv(args.ruff_ignore),
        },
        "jscpd": {
            "min_lines": args.jscpd_min_lines,
            "min_tokens": args.jscpd_min_tokens,
            "ignore": _split_csv(args.jscpd_ignore),
            "use_npx": args.jscpd_use_npx,
            "gitignore": not args.jscpd_no_gitignore,
            "no_symlinks": not args.jscpd_follow_symlinks,
            "include_fragments": args.jscpd_include_fragments,
            "max_fragment_chars": args.jscpd_max_fragment_chars,
        },
        "dead_code": {
            "vulture_min_confidence": args.dead_code_min_confidence,
            "include_low_confidence": args.dead_code_include_low,
        },
        "complexity": {
            "max_cyclomatic": args.max_cyclomatic,
            "max_cognitive": args.max_cognitive,
            "max_function_lines": args.max_function_lines,
        },
    }

    payload = {
        "repo_root": args.repo_root,
        "scope": scope,
        "modes": modes,
        "options": options,
        "budgets": {
            "timeout_sec": args.timeout_sec,
            "max_findings": args.max_findings,
        },
    }

    result = analyze_repo_quality(payload)
    result_dict = result.to_dict()
    output = json.dumps(result_dict, indent=2, ensure_ascii=True)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        return

    print(output)


def _run_gate(args: argparse.Namespace) -> None:
    baseline = _load_json(args.baseline)
    current = _load_json(args.current)
    if current is None:
        print(f"error: current report not found: {args.current}")
        raise SystemExit(1)
    gate_result = evaluate_gate(
        baseline,
        current,
        duplication_delta=args.duplication_delta,
        max_cyclomatic=args.max_cyclomatic,
        max_cognitive=args.max_cognitive,
        max_function_lines=args.max_function_lines,
        strict=args.strict,
    )

    if args.format == "json":
        payload = {
            "status": gate_result.status,
            "reasons": gate_result.reasons,
            "metrics": gate_result.metrics,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(f"status: {gate_result.status}")
        if gate_result.reasons:
            print("reasons:")
            for reason in gate_result.reasons:
                print(f"- {reason}")
        if gate_result.metrics:
            print("metrics:")
            for key, value in gate_result.metrics.items():
                print(f"- {key}: {value}")

    if gate_result.status == "fail":
        raise SystemExit(1)


def evaluate_gate(
    baseline: Optional[Dict[str, Any]],
    current: Dict[str, Any],
    duplication_delta: float,
    max_cyclomatic: int,
    max_cognitive: int,
    max_function_lines: int,
    strict: bool,
) -> GateResult:
    reasons_fail: List[str] = []
    reasons_warn: List[str] = []
    metrics: Dict[str, Any] = {}

    current_ruff_errors = _get_metric(current, ["metrics", "ruff", "errors"], 0)
    metrics["ruff_errors"] = current_ruff_errors
    if current_ruff_errors > 0:
        reasons_fail.append("ruff_errors")

    baseline_available = baseline is not None
    if not baseline_available:
        reasons_warn.append("baseline_missing")
    else:
        baseline_dup = _get_metric(baseline, ["metrics", "duplication", "percentage"], 0.0)
        current_dup = _get_metric(current, ["metrics", "duplication", "percentage"], 0.0)
        dup_delta = current_dup - baseline_dup
        metrics["duplication_delta"] = round(dup_delta, 4)
        if dup_delta > duplication_delta:
            reasons_fail.append("duplication_delta")

        baseline_dead = _get_metric(baseline, ["metrics", "dead_code", "high_confidence"], 0)
        current_dead = _get_metric(current, ["metrics", "dead_code", "high_confidence"], 0)
        dead_delta = current_dead - baseline_dead
        metrics["dead_code_delta"] = dead_delta
        if dead_delta > 0:
            reasons_fail.append("dead_code_increase")

    max_cyclomatic_seen = _get_metric(current, ["metrics", "complexity", "max_cyclomatic"], 0)
    max_cognitive_seen = _get_metric(current, ["metrics", "complexity", "max_cognitive"], 0)
    long_functions = _get_metric(current, ["metrics", "complexity", "long_functions"], 0)
    if max_cyclomatic_seen > max_cyclomatic:
        reasons_warn.append("complexity_cyclomatic")
    if max_cognitive_seen > max_cognitive:
        reasons_warn.append("complexity_cognitive")
    if max_function_lines > 0 and long_functions > 0:
        reasons_warn.append("long_functions")

    if reasons_fail:
        status: Literal["pass", "warn", "fail"] = "fail"
    elif reasons_warn:
        status = "warn"
    else:
        status = "pass"

    if strict and status == "warn":
        status = "fail"
        reasons_fail.extend(reasons_warn)
        reasons_warn = []

    reasons = sorted(set(reasons_fail + reasons_warn))
    return GateResult(status=status, reasons=reasons, metrics=metrics)


def _get_metric(data: Optional[Dict[str, Any]], path: List[str], default: Any) -> Any:
    if not data:
        return default
    cursor: Any = data
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return default
        cursor = cursor[key]
    return cursor


def _split_csv(value: str) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
