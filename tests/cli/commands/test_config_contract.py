"""Contract tests for the 'config' command.

These tests verify the CLI signature, help output, argument validation,
and error handling for the 'sqlitch config' command without testing the
full implementation behavior.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/config.pm
- POD: sqitch/lib/sqitch-config.pod
- Tests: sqitch/t/config.t
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestConfigCommandContract:
    """Contract tests for 'sqlitch config' command signature and behavior."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # CC-CONFIG-001: Action without name (--list)
    def test_config_accepts_list_action(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config --list' works without additional arguments.

        Contract: CC-CONFIG-001
        Perl behavior: --list action requires no name argument
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "--list"])

            # Should not be parsing error
            assert result.exit_code != 2, (
                f"Should accept --list without name argument. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    # CC-CONFIG-002: Get with name
    def test_config_accepts_get_with_name(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config' accepts name argument for getting values.

        Contract: CC-CONFIG-002
        Perl behavior: config uses positional NAME argument for getting values
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "user.name"])

            # Should accept the name argument (exit 0 or 1, not 2)
            assert result.exit_code != 2, (
                f"Should accept name argument. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )


class TestConfigGlobalContracts:
    """Test global contracts for 'config' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # GC-001: Help flag support
    def test_config_help_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config --help' displays help and exits 0."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "--help"])
            assert result.exit_code == 0
            assert "config" in result.output.lower()
            assert "usage" in result.output.lower()

    # GC-002: Global options recognition
    def test_config_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config' accepts --quiet global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "--quiet", "--list"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_config_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config' accepts --verbose global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "--verbose", "--list"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_config_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config' accepts --chdir global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "--chdir", "/tmp", "--list"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_config_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config' accepts --no-pager global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "--no-pager", "--list"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    # GC-005: Unknown option rejection
    def test_config_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch config' rejects unknown options with exit code 2."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["config", "--nonexistent"])
            assert result.exit_code == 2
            assert "no such option" in result.output.lower()
