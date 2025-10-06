"""Contract tests for the help command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-HELP-001: No arguments (general help)
- CC-HELP-002: Command name argument
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


class TestHelpNoArgs:
    """Test CC-HELP-001: No arguments shows general help."""

    def test_help_without_args_exits_zero(self, runner):
        """Help command without args must exit with code 0."""
        result = runner.invoke(main, ["help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_commands_list(self, runner):
        """Help without args must list available commands."""
        result = runner.invoke(main, ["help"])
        # Should show some common commands
        assert "deploy" in result.output.lower() or "init" in result.output.lower()

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["help"])
        assert "usage:" in result.output.lower() or "commands:" in result.output.lower()


class TestHelpWithCommand:
    """Test CC-HELP-002: Command name argument."""

    def test_help_deploy_exits_zero(self, runner):
        """Help for specific command must exit with code 0."""
        result = runner.invoke(main, ["help", "deploy"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_deploy_shows_deploy_info(self, runner):
        """Help for deploy must show deploy-specific information."""
        result = runner.invoke(main, ["help", "deploy"])
        assert "deploy" in result.output.lower()

    def test_help_add_shows_add_info(self, runner):
        """Help for add must show add-specific information."""
        result = runner.invoke(main, ["help", "add"])
        assert "add" in result.output.lower()


class TestHelpOwnHelp:
    """Test GC-001: Help command's own help flag."""

    def test_help_help_flag_exits_zero(self, runner):
        """Help command must support --help flag."""
        result = runner.invoke(main, ["help", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_help_shows_usage(self, runner):
        """Help command's help must show usage."""
        result = runner.invoke(main, ["help", "--help"])
        assert "usage:" in result.output.lower()


class TestHelpGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Help must accept --quiet global option."""
        result = runner.invoke(main, ["help", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Help must accept --verbose global option."""
        result = runner.invoke(main, ["help", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Help must accept --chdir global option."""
        result = runner.invoke(main, ["help", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Help must accept --no-pager global option."""
        result = runner.invoke(main, ["help", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestHelpErrorHandling:
    """Test GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Help must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["help", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
