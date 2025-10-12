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


class TestHelpUsageFlag:
    """Tests for --usage flag functionality."""

    def test_help_usage_flag_shows_only_usage_line(self, runner):
        """Verify --usage flag shows only the usage line, not full help."""
        result = runner.invoke(main, ["help", "--usage"])
        assert result.exit_code == 0
        # Usage output should be shorter than full help
        assert len(result.output) < 500
        # Should contain usage pattern
        assert "sqlitch" in result.output.lower() or "usage:" in result.output.lower()

    def test_help_usage_with_topic_shows_command_usage(self, runner):
        """Verify --usage with topic shows command-specific usage."""
        result = runner.invoke(main, ["help", "--usage", "deploy"])
        assert result.exit_code == 0
        assert "deploy" in result.output.lower()

    def test_help_usage_and_man_flags_conflict(self, runner):
        """Verify --usage and --man cannot be combined."""
        result = runner.invoke(main, ["help", "--usage", "--man"])
        assert result.exit_code != 0
        assert "--man and --usage cannot be combined" in result.output


class TestHelpManFlag:
    """Tests for --man flag functionality."""

    def test_help_man_flag_accepted(self, runner):
        """Verify --man flag is accepted (fallback to stdout)."""
        result = runner.invoke(main, ["help", "--man"])
        # Should succeed (fallback to stdout until pager is implemented)
        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_help_man_with_topic(self, runner):
        """Verify --man flag works with a specific topic."""
        result = runner.invoke(main, ["help", "--man", "init"])
        assert result.exit_code == 0
        assert "init" in result.output.lower()


class TestHelpInvalidTopics:
    """Tests for invalid topic handling."""

    def test_help_nonexistent_topic_errors(self, runner):
        """Verify help for nonexistent topic returns an error."""
        result = runner.invoke(main, ["help", "nonexistent_command_xyz"])
        assert result.exit_code != 0
        assert 'No help for "nonexistent_command_xyz"' in result.output


class TestHelpQuietMode:
    """Tests for quiet mode interaction."""

    def test_help_quiet_mode_still_shows_output(self, runner):
        """Verify --quiet doesn't suppress help output (help is informational)."""
        result = runner.invoke(main, ["help", "--quiet"])
        # Help is informational, so quiet mode doesn't suppress it
        assert result.exit_code == 0
        # Output should still be present
        assert len(result.output.strip()) > 0
        assert "usage:" in result.output.lower() or "commands:" in result.output.lower()

    def test_help_topic_quiet_mode_still_shows_output(self, runner):
        """Verify --quiet doesn't suppress help output for specific topics."""
        result = runner.invoke(main, ["help", "--quiet", "deploy"])
        assert result.exit_code == 0
        # Help output should still be present
        assert len(result.output.strip()) > 0
        assert "deploy" in result.output.lower()
