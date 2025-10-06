"""Contract tests for the target command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-TARGET-001: Action required (or default list)
- GC-001: Help flag support
- GC-002: Global options recognition
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


@pytest.fixture
def runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestTargetHelp:
    """Test CC-TARGET help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Target command must support --help flag."""
        result = runner.invoke(main, ["target", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["target", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the target command."""
        result = runner.invoke(main, ["target", "--help"])
        assert "target" in result.output.lower()


class TestTargetAction:
    """Test CC-TARGET-001: Action handling."""

    def test_no_action_lists_targets_or_succeeds(self, runner):
        """Target without action should list targets or succeed with default action."""
        result = runner.invoke(main, ["target"])
        # Should either:
        # - Exit 0 and list targets (implemented behavior)
        # - Exit 1 with "not implemented" (stub behavior)
        # - Exit 2 only if there's a parsing error (not expected)
        assert result.exit_code in (0, 1), (
            f"Expected exit 0 (success/list) or 1 (not implemented), got {result.exit_code}"
        )

    def test_list_action_accepted(self, runner):
        """Target command must accept 'list' action."""
        result = runner.invoke(main, ["target", "list"])
        # Should accept the action (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_add_action_accepted(self, runner):
        """Target command must accept 'add' action."""
        result = runner.invoke(main, ["target", "add", "test_target", "db:sqlite:test.db"])
        # Should accept the action structure (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_remove_action_accepted(self, runner):
        """Target command must accept 'remove' action."""
        result = runner.invoke(main, ["target", "remove", "test_target"])
        # Should accept the action structure (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestTargetGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Target must accept --quiet global option."""
        result = runner.invoke(main, ["target", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Target must accept --verbose global option."""
        result = runner.invoke(main, ["target", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Target must accept --chdir global option."""
        result = runner.invoke(main, ["target", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Target must accept --no-pager global option."""
        result = runner.invoke(main, ["target", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestTargetErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Target must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["target", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
