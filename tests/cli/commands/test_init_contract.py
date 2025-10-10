"""Contract tests for the init command.

These tests validate CLI signature parity with Sqitch, not full functionality.
Tests ensure:
- CC-INIT-001: Optional project name
- CC-INIT-002: With project name
- GC-001: Help flag support
- GC-002: Global options recognition
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


@pytest.fixture
def runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


class TestInitHelp:
    """Test CC-INIT help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Init command must support --help flag."""
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["init", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the init command."""
        result = runner.invoke(main, ["init", "--help"])
        assert "init" in result.output.lower()


class TestInitOptionalProjectName:
    """Test CC-INIT-001: Optional project name."""

    def test_init_without_project_name_accepted(self, runner):
        """Init without project name must be accepted (uses directory name)."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init"])
            # Should accept (not a parsing error)
            # May exit 0 (success), 1 (not implemented), or fail validation
            assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestInitWithProjectName:
    """Test CC-INIT-002: With project name."""

    def test_init_with_project_name_accepted(self, runner):
        """Init with project name must be accepted."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "myproject"])
            # Should accept (not a parsing error)
            assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_init_with_engine_option(self, runner):
        """Init with --engine option must be accepted."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "myproject", "--engine", "sqlite"])
            # Should accept (not a parsing error)
            assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestInitGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Init must accept --quiet global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "--quiet"])
            # Should not fail with "no such option" error
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Init must accept --verbose global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "--verbose"])
            # Should not fail with "no such option" error
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Init must accept --chdir global option."""
        result = runner.invoke(main, ["init", "--chdir", "/tmp", "test"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Init must accept --no-pager global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "--no-pager"])
            # Should not fail with "no such option" error
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestInitErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Init must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["init", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
