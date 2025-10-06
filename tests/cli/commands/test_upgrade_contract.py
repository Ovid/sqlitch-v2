"""Contract tests for the upgrade command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-UPGRADE-001: Optional target
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


class TestUpgradeHelp:
    """Test CC-UPGRADE help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Upgrade command must support --help flag."""
        result = runner.invoke(main, ["upgrade", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["upgrade", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the upgrade command."""
        result = runner.invoke(main, ["upgrade", "--help"])
        assert "upgrade" in result.output.lower()


class TestUpgradeOptionalTarget:
    """Test CC-UPGRADE-001: Optional target."""

    def test_upgrade_without_target_accepted(self, runner):
        """Upgrade without target must be accepted (uses default)."""
        result = runner.invoke(main, ["upgrade"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_upgrade_with_positional_target(self, runner):
        """Upgrade with positional target must be accepted."""
        result = runner.invoke(main, ["upgrade", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_upgrade_with_target_option(self, runner):
        """Upgrade with --target option must be accepted."""
        result = runner.invoke(main, ["upgrade", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestUpgradeGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Upgrade must accept --quiet global option."""
        result = runner.invoke(main, ["upgrade", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Upgrade must accept --verbose global option."""
        result = runner.invoke(main, ["upgrade", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Upgrade must accept --chdir global option."""
        result = runner.invoke(main, ["upgrade", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Upgrade must accept --no-pager global option."""
        result = runner.invoke(main, ["upgrade", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestUpgradeErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Upgrade must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["upgrade", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
