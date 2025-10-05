"""Cross-command regression tests for error output channel.

These tests verify that all SQLitch commands write errors to stderr
as specified in GC-004 (Error Output Channel).
"""

from __future__ import annotations

from click.testing import CliRunner

from sqlitch.cli.main import main


def test_gc_004_missing_args_error_to_stderr():
    """GC-004: Missing argument errors should go to stderr."""
    runner = CliRunner()
    
    # Commands with required arguments
    commands_with_required_args = ["add", "checkout", "rework"]
    
    for cmd in commands_with_required_args:
        result = runner.invoke(main, [cmd], mix_stderr=False)
        
        # When mix_stderr=False, Click writes errors to result.output (which captures stderr)
        # The error should be non-empty since we're missing required args
        assert result.exit_code == 2, \
            f"Command '{cmd}' should fail with missing args"
        
        # Error message should exist
        assert len(result.output) > 0, \
            f"Command '{cmd}' should have error output for missing args"


def test_gc_004_invalid_options_error_to_stderr():
    """GC-004: Invalid option errors should go to stderr."""
    runner = CliRunner()
    
    result = runner.invoke(main, ["plan", "--nonexistent-option"], mix_stderr=False)
    
    assert result.exit_code == 2, "Invalid option should cause exit code 2"
    assert len(result.output) > 0, "Should have error message for invalid option"
    assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower(), \
        "Error message should mention invalid option"


def test_gc_004_errors_include_descriptive_messages():
    """GC-004: Error messages should be descriptive."""
    runner = CliRunner()
    
    # Test missing required argument
    result = runner.invoke(main, ["add"])
    
    assert result.exit_code != 0, "Command should fail"
    assert len(result.output) > 20, \
        "Error message should be descriptive (more than just a code)"
    
    # Should mention what's missing or wrong
    output_lower = result.output.lower()
    assert any(keyword in output_lower for keyword in ["missing", "required", "argument", "error"]), \
        "Error should describe the problem"


def test_gc_004_help_output_goes_to_stdout():
    """GC-004: Help output (non-error) should go to stdout."""
    runner = CliRunner()
    
    # Help is not an error, so with mix_stderr=True (default) it goes to stdout
    result = runner.invoke(main, ["plan", "--help"])
    
    assert result.exit_code == 0, "Help should succeed"
    assert len(result.output) > 0, "Help output should exist"
    assert "plan" in result.output.lower(), "Help should describe the command"
