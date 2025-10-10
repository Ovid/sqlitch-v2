"""Cross-command regression tests for help format consistency.

These tests verify that all SQLitch commands provide consistent help output
structure as specified in GC-001 (Help Flag Support).
"""

from __future__ import annotations

from click.testing import CliRunner

from sqlitch.cli.main import main

# All 19 Sqitch commands
COMMANDS = [
    "add",
    "bundle",
    "checkout",
    "config",
    "deploy",
    "engine",
    "help",
    "init",
    "log",
    "plan",
    "rebase",
    "revert",
    "rework",
    "show",
    "status",
    "tag",
    "target",
    "upgrade",
    "verify",
]


def test_gc_001_all_commands_support_help_flag():
    """GC-001: All commands support --help flag with consistent structure."""
    runner = CliRunner()

    for cmd in COMMANDS:
        result = runner.invoke(main, [cmd, "--help"])

        assert (
            result.exit_code == 0
        ), f"Command '{cmd} --help' should exit with code 0, got {result.exit_code}"

        # Verify help output structure
        output_lower = result.output.lower()
        assert cmd in output_lower, f"Help for '{cmd}' should mention command name"

        # Should have usage/synopsis or options section
        assert any(
            keyword in output_lower for keyword in ["usage", "options", "synopsis"]
        ), f"Help for '{cmd}' should have usage/options section"


def test_help_output_includes_description():
    """Verify help output includes description for each command."""
    runner = CliRunner()

    for cmd in COMMANDS:
        result = runner.invoke(main, [cmd, "--help"])

        # Help output should be non-trivial (more than just command name)
        assert len(result.output) > 50, f"Help for '{cmd}' should provide substantial information"


def test_help_does_not_execute_command_logic():
    """GC-001: --help should not execute the command's main logic."""
    runner = CliRunner()

    # Commands that typically require arguments or would fail without them
    for cmd in ["add", "checkout", "rework"]:
        result = runner.invoke(main, [cmd, "--help"])

        # Should succeed with --help even though arguments are missing
        assert (
            result.exit_code == 0
        ), f"Command '{cmd} --help' should succeed despite missing arguments"

        # Should not show "missing argument" errors
        assert (
            "missing" not in result.output.lower() or "usage" in result.output.lower()
        ), f"Help for '{cmd}' should show usage, not missing argument errors"
