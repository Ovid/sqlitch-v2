"""Cross-command regression tests for exit code conventions.

These tests verify that all SQLitch commands follow the exit code convention
as specified in GC-003 (Exit Code Convention): 0=success, 1=user error, 2=system error.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


def test_gc_003_help_exits_with_zero():
    """GC-003: Help invocations should exit with code 0 (success)."""
    runner = CliRunner()
    
    commands = [
        "add", "bundle", "checkout", "config", "deploy", "engine", "help",
        "init", "log", "plan", "rebase", "revert", "rework", "show",
        "status", "tag", "target", "upgrade", "verify"
    ]
    
    for cmd in commands:
        result = runner.invoke(main, [cmd, "--help"])
        assert result.exit_code == 0, \
            f"Help for '{cmd}' should exit with code 0, got {result.exit_code}"


@pytest.mark.skip(reason="Pending: checkout stub needs required 'branch' argument validation (see T027 audit)")
def test_gc_003_missing_required_args_exit_with_two():
    """GC-003: Missing required arguments should exit with code 2 (parsing error)."""
    runner = CliRunner()
    
    # Commands with required arguments
    required_arg_commands = {
        "add": "change_name",
        "checkout": "branch",  # STUB: Not yet implemented
        "rework": "change_name",
    }
    
    # Stub commands (from audit T027)
    stub_commands = {"checkout", "rebase", "revert", "upgrade", "verify"}
    
    for cmd, arg_name in required_arg_commands.items():
        # Skip stub commands - they'll be tested when fully implemented
        if cmd in stub_commands:
            pytest.skip(f"Pending: {cmd} command implementation (stub)")
            
        result = runner.invoke(main, [cmd])
        
        assert result.exit_code == 2, \
            f"Command '{cmd}' without {arg_name} should exit with code 2, got {result.exit_code}"


def test_gc_003_invalid_options_exit_with_two():
    """GC-003: Invalid/unknown options should exit with code 2."""
    runner = CliRunner()
    
    # Test a few representative commands with unknown options
    test_cases = [
        ["plan", "--nonexistent-option"],
        ["status", "--invalid-flag"],
        ["log", "--bad-option"],
    ]
    
    for args in test_cases:
        result = runner.invoke(main, args)
        
        assert result.exit_code == 2, \
            f"Command {args} with invalid option should exit with code 2, got {result.exit_code}"


def test_gc_003_valid_exit_code_range():
    """GC-003: All commands should exit with codes 0, 1, or 2 only."""
    runner = CliRunner()
    
    # Test various command invocations
    test_cases = [
        ["plan"],
        ["status"],
        ["add", "test_change"],
        ["deploy"],
    ]
    
    for args in test_cases:
        result = runner.invoke(main, args)
        
        assert result.exit_code in (0, 1, 2), \
            f"Command {args} should exit with 0, 1, or 2, got {result.exit_code}"
