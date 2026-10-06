"""Tests for the grouped click CLI and the `skills` command"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from mcp_refactoring_assistant.cli import COMMAND_EXAMPLES, GROUPED_COMMANDS, cli

SAMPLE_FILE = str(Path(__file__).parent / "fixtures" / "sample_code" / "complex_function.py")
LEGACY_NAMES = [legacy for *_, legacy in GROUPED_COMMANDS]


@pytest.fixture
def runner():
    return CliRunner()


def _skills_json(runner):
    result = runner.invoke(cli, ["skills", "--format", "json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_help_lists_groups_not_legacy_aliases(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    commands_section = result.output.split("Commands:")[1]
    listed = {line.split()[0] for line in commands_section.strip().splitlines()}
    assert {"file", "test", "security", "package", "repo", "server", "skill", "skills"} <= listed
    assert not listed & {"find-long-functions", "security-scan", "package-metrics", "analyze"}


def test_skills_markdown_includes_skill_and_commands(runner):
    result = runner.invoke(cli, ["skills"])
    assert result.exit_code == 0
    assert "name: python-refactoring" in result.output
    assert "## Available commands" in result.output
    for path in COMMAND_EXAMPLES:
        assert f"### `{path}`" in result.output
    for legacy in ("find-long-functions", "security-scan", "package-metrics"):
        assert f"### `{legacy}`" not in result.output


def test_skills_json_has_examples_for_every_command(runner):
    data = _skills_json(runner)
    assert "name: python-refactoring" in data["skill"]
    assert data["commands"]
    for entry in data["commands"]:
        assert entry["examples"], f"missing examples for {entry['command']}"
        assert entry["usage"].startswith(f"python-refactor-cli {entry['command']}")


def test_examples_registry_matches_real_commands(runner):
    listed = {entry["command"] for entry in _skills_json(runner)["commands"]}
    assert set(COMMAND_EXAMPLES) == listed


def test_examples_appear_in_command_help(runner):
    result = runner.invoke(cli, ["file", "long-functions", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output
    assert "python-refactor-cli file long-functions" in result.output


def test_grouped_command_and_legacy_alias_match(runner):
    grouped = runner.invoke(cli, ["file", "long-functions", SAMPLE_FILE, "-f", "json"])
    legacy = runner.invoke(cli, ["find-long-functions", SAMPLE_FILE, "-f", "json"])
    assert grouped.exit_code == 0, grouped.output
    assert legacy.exit_code == 0, legacy.output
    assert json.loads(grouped.output) == json.loads(legacy.output)


@pytest.mark.parametrize("legacy", LEGACY_NAMES)
def test_legacy_aliases_resolve(runner, legacy):
    result = runner.invoke(cli, [legacy, "--help"])
    assert result.exit_code == 0, result.output
