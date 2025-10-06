"""Contract tests for the show command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-SHOW-001: Optional change name
- CC-SHOW-002: With change name
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


class TestShowHelp:
    """Test CC-SHOW help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Show command must support --help flag."""
        result = runner.invoke(main, ["show", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["show", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the show command."""
        result = runner.invoke(main, ["show", "--help"])
        assert "show" in result.output.lower()


class TestShowOptionalChangeName:
    """Test CC-SHOW-001: Optional change name."""

    def test_show_without_change_name_accepted(self, runner):
        """Show without change name must be accepted (shows all changes)."""
        result = runner.invoke(main, ["show"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented/no plan), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestShowWithChangeName:
    """Test CC-SHOW-002: With change name."""

    def test_show_with_change_name_accepted(self, runner):
        """Show with change name must be accepted."""
        result = runner.invoke(main, ["show", "my_change"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_show_with_tag_name(self, runner):
        """Show with tag name must be accepted."""
        result = runner.invoke(main, ["show", "@v1.0"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_show_with_target_option(self, runner):
        """Show with --target option must be accepted."""
        result = runner.invoke(main, ["show", "my_change", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestShowGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Show must accept --quiet global option."""
        result = runner.invoke(main, ["show", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Show must accept --verbose global option."""
        result = runner.invoke(main, ["show", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Show must accept --chdir global option."""
        result = runner.invoke(main, ["show", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Show must accept --no-pager global option."""
        result = runner.invoke(main, ["show", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestShowErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Show must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["show", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
