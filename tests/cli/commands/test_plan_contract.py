"""Contract tests for the plan command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-PLAN-001: Optional target
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


class TestPlanHelp:
    """Test CC-PLAN help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Plan command must support --help flag."""
        result = runner.invoke(main, ["plan", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["plan", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the plan command."""
        result = runner.invoke(main, ["plan", "--help"])
        assert "plan" in result.output.lower()


class TestPlanOptionalTarget:
    """Test CC-PLAN-001: Optional target."""

    def test_plan_without_target_accepted(self, runner):
        """Plan without target must be accepted (shows project plan)."""
        result = runner.invoke(main, ["plan"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (no plan file), or show plan
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_plan_with_positional_target(self, runner):
        """Plan with positional target must be accepted."""
        result = runner.invoke(main, ["plan", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_plan_with_target_option(self, runner):
        """Plan with --target option must be accepted."""
        result = runner.invoke(main, ["plan", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestPlanGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Plan must accept --quiet global option."""
        result = runner.invoke(main, ["plan", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Plan must accept --verbose global option."""
        result = runner.invoke(main, ["plan", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Plan must accept --chdir global option."""
        result = runner.invoke(main, ["plan", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Plan must accept --no-pager global option."""
        result = runner.invoke(main, ["plan", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestPlanErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Plan must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["plan", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
