"""Cross-command regression tests for unknown option rejection.

These tests verify that all SQLitch commands properly reject unknown options
as specified in GC-005 (Unknown Option Rejection).
"""

from __future__ import annotations

from click.testing import CliRunner

from sqlitch.cli.main import main


# All 19 Sqitch commands
COMMANDS = [
    "add", "bundle", "checkout", "config", "deploy", "engine", "help",
    "init", "log", "plan", "rebase", "revert", "rework", "show",
    "status", "tag", "target", "upgrade", "verify"
]


def test_gc_005_all_commands_reject_unknown_options():
    """GC-005: All commands should reject unknown options with exit code 2."""
    runner = CliRunner()
    
    for cmd in COMMANDS:
        args = [cmd, "--nonexistent-option"]
        
        # Add required arguments for commands that need them
        if cmd in ["add", "rework"]:
            args.append("dummy_change")
        elif cmd == "checkout":
            args.append("main")
        
        result = runner.invoke(main, args)
        
        # Should exit with code 2 (option parsing error)
        assert result.exit_code == 2, \
            f"Command '{cmd}' with unknown option should exit with code 2, got {result.exit_code}"
        
        # Error message should mention the unknown option
        output_lower = result.output.lower()
        assert "no such option" in output_lower or "unrecognized" in output_lower or "unknown" in output_lower, \
            f"Command '{cmd}' should report unknown option in error message"


def test_gc_005_unknown_option_prevents_execution():
    """GC-005: Unknown options should prevent command execution."""
    runner = CliRunner()
    
    # Test commands that would normally succeed or proceed
    test_cases = [
        ["plan", "--fake-option"],
        ["help", "--invalid-flag"],
        ["status", "--bogus-option"],
    ]
    
    for args in test_cases:
        result = runner.invoke(main, args)
        
        assert result.exit_code == 2, \
            f"Command {args} should fail at option parsing"
        
        # Should not execute main logic - error should be about the option
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower(), \
            f"Command {args} should report option error, not execution error"


def test_gc_005_multiple_unknown_options():
    """GC-005: Multiple unknown options should still cause rejection."""
    runner = CliRunner()
    
    result = runner.invoke(main, ["plan", "--fake1", "--fake2"])
    
    assert result.exit_code == 2, \
        "Multiple unknown options should cause exit code 2"
    
    # Should mention at least one unknown option
    output_lower = result.output.lower()
    assert "no such option" in output_lower or "unrecognized" in output_lower, \
        "Should report unknown option error"


def test_gc_005_unknown_short_options():
    """GC-005: Unknown short options should also be rejected."""
    runner = CliRunner()
    
    # Test with a short option that doesn't exist
    result = runner.invoke(main, ["plan", "-z"])
    
    assert result.exit_code == 2, \
        "Unknown short option should cause exit code 2"


def test_gc_005_typo_in_known_option():
    """GC-005: Typos in known options should be rejected (no fuzzy matching)."""
    runner = CliRunner()
    
    # Typo: --verbos instead of --verbose
    result = runner.invoke(main, ["plan", "--verbos"])
    
    assert result.exit_code == 2, \
        "Typo in option name should cause exit code 2"
    
    assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower(), \
        "Should report unknown option, not auto-correct"
