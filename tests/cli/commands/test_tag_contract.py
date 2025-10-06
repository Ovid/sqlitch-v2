"""Contract tests for the tag command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-TAG-001: Optional tag name (list tags)
- CC-TAG-002: With tag name
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


class TestTagHelp:
    """Test CC-TAG help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Tag command must support --help flag."""
        result = runner.invoke(main, ["tag", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["tag", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the tag command."""
        result = runner.invoke(main, ["tag", "--help"])
        assert "tag" in result.output.lower()


class TestTagOptionalName:
    """Test CC-TAG-001: Optional tag name (list tags)."""

    def test_tag_without_name_accepted(self, runner):
        """Tag without name must be accepted (lists tags)."""
        result = runner.invoke(main, ["tag"])
        # Should accept (not a parsing error)
        # May exit 0 (success/list), 1 (not implemented), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestTagWithName:
    """Test CC-TAG-002: With tag name."""

    def test_tag_with_name_accepted(self, runner):
        """Tag with name must be accepted."""
        result = runner.invoke(main, ["tag", "v1.0"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_tag_with_note_option(self, runner):
        """Tag with --note option must be accepted."""
        result = runner.invoke(main, ["tag", "v1.0", "--note", "Release version 1.0"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_tag_with_change_option(self, runner):
        """Tag with --change option must be accepted."""
        result = runner.invoke(main, ["tag", "v1.0", "--change", "my_change"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestTagGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Tag must accept --quiet global option."""
        result = runner.invoke(main, ["tag", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Tag must accept --verbose global option."""
        result = runner.invoke(main, ["tag", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Tag must accept --chdir global option."""
        result = runner.invoke(main, ["tag", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Tag must accept --no-pager global option."""
        result = runner.invoke(main, ["tag", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestTagErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Tag must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["tag", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
