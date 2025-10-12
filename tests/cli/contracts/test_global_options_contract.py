"""Contract tests covering SQLitch global verbosity and output options."""

from __future__ import annotations

import importlib
from typing import Iterator
from uuid import UUID

import click
import pytest
from click.testing import CliRunner

cli_main = importlib.import_module("sqlitch.cli.main")


@pytest.fixture(autouse=True)
def restore_main_commands() -> Iterator[None]:
    """Reset registered commands on the CLI group after each test."""

    original_commands = dict(cli_main.main.commands)
    try:
        yield
    finally:
        cli_main.main.commands = original_commands


def _invoke_with_capture(args: list[str], *, env: dict[str, str] | None = None):
    runner = CliRunner()
    captured: dict[str, object] = {}

    @click.command("introspect")
    @click.pass_context
    def introspect(ctx: click.Context) -> None:
        captured["ctx"] = ctx.obj
        click.echo("ok")

    cli_main.main.add_command(introspect)
    result = runner.invoke(cli_main.main, [*args, "introspect"], env=env)
    assert result.exit_code == 0, result.output
    return captured["ctx"], result


def test_verbose_flags_adjust_log_configuration() -> None:
    ctx, result = _invoke_with_capture(["-vv"])

    assert "ok" in result.output
    assert ctx.verbosity == 2
    assert ctx.log_config.verbosity == 2
    assert ctx.log_config.quiet is False
    assert ctx.log_config.level in {"DEBUG", "TRACE"}


def test_quiet_flag_supersedes_verbosity() -> None:
    ctx, _ = _invoke_with_capture(["--quiet"])

    assert ctx.quiet is True
    assert ctx.verbosity == 0
    assert ctx.log_config.quiet is True
    assert ctx.log_config.level == "ERROR"


def test_json_flag_enables_structured_output() -> None:
    ctx, _ = _invoke_with_capture(["--json"])

    assert ctx.json_mode is True
    assert ctx.log_config.json_mode is True
    assert ctx.log_config.level == "INFO"


def test_run_identifier_uses_environment_override() -> None:
    ctx, _ = _invoke_with_capture([], env={"SQLITCH_RUN_ID": "run-identifier"})

    assert ctx.run_identifier == "run-identifier"
    assert ctx.log_config.run_identifier == "run-identifier"


def test_run_identifier_defaults_to_uuid() -> None:
    ctx, _ = _invoke_with_capture([])

    UUID(ctx.run_identifier)


# ==============================================================================
# Cross-Command Global Options Tests (from regression tests)
# ==============================================================================


# All 19 Sqitch commands for cross-command testing
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


def test_gc_001_all_commands_support_help_flag() -> None:
    """GC-001: All commands support --help flag with consistent structure."""
    runner = CliRunner()

    for cmd in COMMANDS:
        result = runner.invoke(cli_main.main, [cmd, "--help"])

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


def test_gc_002_all_commands_accept_quiet() -> None:
    """GC-002: All commands accept --quiet global option."""
    from tests.support.test_helpers import isolated_test_context

    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            # Provide required arguments for commands that need them
            args = [cmd, "--quiet"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(cli_main.main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --quiet option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --quiet, got: {result.output}"


def test_gc_002_all_commands_accept_verbose() -> None:
    """GC-002: All commands accept --verbose global option."""
    from tests.support.test_helpers import isolated_test_context

    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            args = [cmd, "--verbose"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(cli_main.main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --verbose option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --verbose"


def test_gc_002_all_commands_accept_no_pager() -> None:
    """GC-002: All commands accept --no-pager global option."""
    from tests.support.test_helpers import isolated_test_context

    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            args = [cmd, "--no-pager"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(cli_main.main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --no-pager option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --no-pager"


def test_gc_002_all_commands_accept_chdir() -> None:
    """GC-002: All commands accept --chdir global option."""
    from tests.support.test_helpers import isolated_test_context

    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for cmd in COMMANDS:
            args = [cmd, "--chdir", "/tmp"]
            if cmd in ["add", "rework"]:
                args.append("dummy_change")
            elif cmd == "checkout":
                args.append("main")

            result = runner.invoke(cli_main.main, args)

            assert (
                result.exit_code != 2 or "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should accept --chdir option"

            assert (
                "no such option" not in result.output.lower()
            ), f"Command '{cmd}' should recognize --chdir"


def test_gc_003_help_exits_with_zero() -> None:
    """GC-003: Help invocations should exit with code 0 (success)."""
    runner = CliRunner()

    for cmd in COMMANDS:
        result = runner.invoke(cli_main.main, [cmd, "--help"])
        assert (
            result.exit_code == 0
        ), f"Help for '{cmd}' should exit with code 0, got {result.exit_code}"


def test_gc_003_invalid_options_exit_with_two() -> None:
    """GC-003: Invalid/unknown options should exit with code 2."""
    runner = CliRunner()

    # Test a few representative commands with unknown options
    test_cases = [
        ["plan", "--nonexistent-option"],
        ["status", "--invalid-flag"],
        ["log", "--bad-option"],
    ]

    for args in test_cases:
        result = runner.invoke(cli_main.main, args)

        assert (
            result.exit_code == 2
        ), f"Command {args} with invalid option should exit with code 2, got {result.exit_code}"


def test_gc_004_errors_include_descriptive_messages() -> None:
    """GC-004: Error messages should be descriptive."""
    runner = CliRunner()

    # Test missing required argument
    result = runner.invoke(cli_main.main, ["add"])

    assert result.exit_code != 0, "Command should fail"
    assert len(result.output) > 20, "Error message should be descriptive (more than just a code)"

    # Should mention what's missing or wrong
    output_lower = result.output.lower()
    assert any(
        keyword in output_lower for keyword in ["missing", "required", "argument", "error"]
    ), "Error should describe the problem"


def test_gc_004_help_output_goes_to_stdout() -> None:
    """GC-004: Help output (non-error) should go to stdout."""
    runner = CliRunner()

    # Help is not an error, so with mix_stderr=True (default) it goes to stdout
    result = runner.invoke(cli_main.main, ["plan", "--help"])

    assert result.exit_code == 0, "Help should succeed"
    assert len(result.output) > 0, "Help output should exist"
    assert "plan" in result.output.lower(), "Help should describe the command"


def test_gc_005_all_commands_reject_unknown_options() -> None:
    """GC-005: All commands should reject unknown options with exit code 2."""
    runner = CliRunner()

    for cmd in COMMANDS:
        args = [cmd, "--nonexistent-option"]

        # Add required arguments for commands that need them
        if cmd in ["add", "rework"]:
            args.append("dummy_change")
        elif cmd == "checkout":
            args.append("main")

        result = runner.invoke(cli_main.main, args)

        assert (
            result.exit_code == 2
        ), f"Command '{cmd}' should reject unknown options with exit code 2, got {result.exit_code}"

        # Should mention the unknown option in error output
        assert any(
            keyword in result.output.lower()
            for keyword in ["no such option", "unrecognized", "invalid"]
        ), f"Command '{cmd}' should mention the unknown option in error"
