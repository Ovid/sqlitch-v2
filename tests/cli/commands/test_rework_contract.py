"""Contract tests for the rework command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-REWORK-001: Required change name
- CC-REWORK-002: Valid change name
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


class TestReworkHelp:
    """Test CC-REWORK help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Rework command must support --help flag."""
        result = runner.invoke(main, ["rework", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["rework", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the rework command."""
        result = runner.invoke(main, ["rework", "--help"])
        assert "rework" in result.output.lower()


class TestReworkRequiredChangeName:
    """Test CC-REWORK-001: Required change name."""

    def test_rework_without_change_name_fails(self, runner):
        """Rework without change name must fail with exit code 2."""
        result = runner.invoke(main, ["rework"])
        assert result.exit_code == 2, f"Expected exit 2 for missing argument, got {result.exit_code}"
        # Error should mention missing argument
        assert "missing" in result.output.lower() or "required" in result.output.lower()


class TestReworkValidChangeName:
    """Test CC-REWORK-002: Valid change name."""

    def test_rework_with_change_name_accepted(self, runner):
        """Rework with change name must be accepted."""
        result = runner.invoke(main, ["rework", "my_change"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_rework_with_note_option(self, runner):
        """Rework with --note option must be accepted."""
        result = runner.invoke(main, ["rework", "my_change", "--note", "Reworking for improvements"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_rework_with_requires_option(self, runner):
        """Rework with --requires option must be accepted."""
        result = runner.invoke(main, ["rework", "my_change", "--requires", "other_change"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestReworkGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Rework must accept --quiet global option."""
        result = runner.invoke(main, ["rework", "--quiet", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Rework must accept --verbose global option."""
        result = runner.invoke(main, ["rework", "--verbose", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Rework must accept --chdir global option."""
        result = runner.invoke(main, ["rework", "--chdir", "/tmp", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Rework must accept --no-pager global option."""
        result = runner.invoke(main, ["rework", "--no-pager", "my_change"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestReworkErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Rework must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["rework", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
