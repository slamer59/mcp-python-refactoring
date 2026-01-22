#!/usr/bin/env python3
"""Unit tests for RefactorOps CLI gate evaluation."""

from mcp_refactoring_assistant.refactorops import cli as cli_module


def test_gate_fails_on_ruff_errors():
    baseline = {
        "metrics": {
            "ruff": {"errors": 0},
            "duplication": {"percentage": 1.0},
            "dead_code": {"high_confidence": 0},
            "complexity": {"max_cyclomatic": 5, "max_cognitive": 5, "long_functions": 0},
        }
    }
    current = {
        "metrics": {
            "ruff": {"errors": 2},
            "duplication": {"percentage": 1.0},
            "dead_code": {"high_confidence": 0},
            "complexity": {"max_cyclomatic": 5, "max_cognitive": 5, "long_functions": 0},
        }
    }

    result = cli_module.evaluate_gate(
        baseline,
        current,
        duplication_delta=0.2,
        max_cyclomatic=10,
        max_cognitive=15,
        max_function_lines=30,
        strict=False,
    )

    assert result.status == "fail"
    assert "ruff_errors" in result.reasons


def test_gate_warns_on_complexity_without_strict():
    baseline = {
        "metrics": {
            "ruff": {"errors": 0},
            "duplication": {"percentage": 1.0},
            "dead_code": {"high_confidence": 0},
            "complexity": {"max_cyclomatic": 5, "max_cognitive": 5, "long_functions": 0},
        }
    }
    current = {
        "metrics": {
            "ruff": {"errors": 0},
            "duplication": {"percentage": 1.0},
            "dead_code": {"high_confidence": 0},
            "complexity": {"max_cyclomatic": 20, "max_cognitive": 5, "long_functions": 1},
        }
    }

    result = cli_module.evaluate_gate(
        baseline,
        current,
        duplication_delta=0.2,
        max_cyclomatic=10,
        max_cognitive=15,
        max_function_lines=30,
        strict=False,
    )

    assert result.status == "warn"
    assert "complexity_cyclomatic" in result.reasons


def test_gate_strict_promotes_warn_to_fail():
    baseline = {
        "metrics": {
            "ruff": {"errors": 0},
            "duplication": {"percentage": 1.0},
            "dead_code": {"high_confidence": 0},
            "complexity": {"max_cyclomatic": 5, "max_cognitive": 5, "long_functions": 0},
        }
    }
    current = {
        "metrics": {
            "ruff": {"errors": 0},
            "duplication": {"percentage": 1.0},
            "dead_code": {"high_confidence": 0},
            "complexity": {"max_cyclomatic": 20, "max_cognitive": 5, "long_functions": 1},
        }
    }

    result = cli_module.evaluate_gate(
        baseline,
        current,
        duplication_delta=0.2,
        max_cyclomatic=10,
        max_cognitive=15,
        max_function_lines=30,
        strict=True,
    )

    assert result.status == "fail"
    assert "complexity_cyclomatic" in result.reasons
