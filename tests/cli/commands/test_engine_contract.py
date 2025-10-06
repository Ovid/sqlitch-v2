"""Contract tests for the engine command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-ENGINE-001: Action handling (list as default or required)
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


class TestEngineHelp:
    """Test CC-ENGINE help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Engine command must support --help flag."""
        result = runner.invoke(main, ["engine", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["engine", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the engine command."""
        result = runner.invoke(main, ["engine", "--help"])
        assert "engine" in result.output.lower()


class TestEngineAction:
    """Test CC-ENGINE-001: Action handling."""

    def test_no_action_lists_engines_or_succeeds(self, runner):
        """Engine without action should list engines or succeed with default action."""
        result = runner.invoke(main, ["engine"])
        # Should either:
        # - Exit 0 and list engines (implemented behavior)
        # - Exit 1 with "not implemented" (stub behavior)
        # - Exit 2 only if there's a parsing error (not expected)
        assert result.exit_code in (0, 1), (
            f"Expected exit 0 (success/list) or 1 (not implemented), got {result.exit_code}"
        )
        # Should not be a parsing error
        if result.exit_code == 2:
            pytest.fail(f"Unexpected parsing error: {result.output}")

    def test_list_action_accepted(self, runner):
        """Engine command must accept 'list' action."""
        result = runner.invoke(main, ["engine", "list"])
        # Should accept the action (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_add_action_accepted(self, runner):
        """Engine command must accept 'add' action."""
        result = runner.invoke(main, ["engine", "add", "test_engine", "db:sqlite:test.db"])
        # Should accept the action structure (not a parsing error)
        # May fail with exit 1 for validation or not implemented
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestEngineGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Engine must accept --quiet global option."""
        result = runner.invoke(main, ["engine", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Engine must accept --verbose global option."""
        result = runner.invoke(main, ["engine", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Engine must accept --chdir global option."""
        result = runner.invoke(main, ["engine", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Engine must accept --no-pager global option."""
        result = runner.invoke(main, ["engine", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestEngineErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Engine must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["engine", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
