"""Contract parity tests for ``sqlitch help``."""

from __future__ import annotations

from click.testing import CliRunner

from sqlitch.cli.main import main


def _runner() -> CliRunner:
    return CliRunner()


def test_help_lists_available_commands() -> None:
    """Invoking help without a topic should list top-level commands."""

    runner = _runner()
    result = runner.invoke(main, ["help"])

    assert result.exit_code == 0, result.stderr
    assert "Usage: sqlitch" in result.stdout
    for command in ("add", "config", "engine", "status"):
        assert command in result.stdout


def test_help_topic_outputs_command_help() -> None:
    """Asking for help on a command should mirror the command's help text."""

    runner = _runner()
    result = runner.invoke(main, ["help", "config"])

    assert result.exit_code == 0, result.stderr
    assert "Usage: sqlitch config" in result.stdout
    assert "--list" in result.stdout


def test_help_usage_flag_outputs_single_line_summary() -> None:
    """--usage should limit the output to the usage summary line."""

    runner = _runner()
    result = runner.invoke(main, ["help", "--usage", "config"])

    assert result.exit_code == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("Usage: sqlitch config")


def test_help_unknown_topic_errors() -> None:
    """Unknown topics should return a parity error message."""

    runner = _runner()
    result = runner.invoke(main, ["help", "unknown"], catch_exceptions=False)

    assert result.exit_code != 0
    assert 'No help for "unknown"' in result.stderr
