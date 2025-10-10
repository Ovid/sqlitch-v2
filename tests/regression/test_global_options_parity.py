"""Cross-command regression tests for global options acceptance.

These tests verify that all SQLitch commands accept global options
as specified in GC-002 (Global Options Recognition).
"""

from __future__ import annotations

from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


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

# Global options that must be supported by all commands
GLOBAL_OPTIONS = ["--quiet", "--verbose", "--no-pager"]


def test_gc_002_all_commands_accept_quiet():
    """GC-002: All commands accept --quiet global option."""
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            # Provide required arguments for commands that need them
            args = [cmd, "--quiet"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --quiet option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --quiet, got: {result.output}"


def test_gc_002_all_commands_accept_verbose():
    """GC-002: All commands accept --verbose global option."""
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            args = [cmd, "--verbose"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --verbose option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --verbose"


def test_gc_002_all_commands_accept_no_pager():
    """GC-002: All commands accept --no-pager global option."""
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            args = [cmd, "--no-pager"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --no-pager option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --no-pager"


def test_gc_002_all_commands_accept_chdir():
    """GC-002: All commands accept --chdir global option."""
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            args = [cmd, "--chdir", "/tmp"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --chdir option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --chdir"


def test_global_options_do_not_cause_parsing_errors():
    """GC-002: Global options should not cause option parsing errors."""
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        # Test a representative sample with multiple global options
        test_cases = [
            (["plan", "--quiet", "--verbose"]),
            (["status", "--no-pager"]),
            (["log", "--chdir", "/tmp"]),
        ]

        for args in test_cases:
            result = runner.invoke(main, args)

            # Should not be a parsing error (exit code 2)
            # May be user error (1) or success (0) depending on implementation
            error_msg = f"Command {args} should not have parsing errors"
            assert "no such option" not in result.output.lower(), error_msg
