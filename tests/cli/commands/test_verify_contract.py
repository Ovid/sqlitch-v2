"""Contract tests for the 'verify' command.

These tests verify the CLI signature, help output, argument validation,
and error handling for the 'sqlitch verify' command without testing the
full implementation behavior.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/verify.pm
- POD: sqitch/lib/sqitch-verify.pod
- Tests: sqitch/t/verify.t
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestVerifyCommandContract:
    """Contract tests for 'sqlitch verify' command signature and behavior."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # CC-VERIFY-001: Optional target
    def test_verify_accepts_no_arguments(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify' works without arguments.

        Contract: CC-VERIFY-001
        Perl behavior: target argument is optional (uses default from config)
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify"])
            
            # Should not be parsing error
            assert result.exit_code != 2, (
                f"Should accept command without arguments. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    # CC-VERIFY-002: Positional target (recently fixed)
    def test_verify_accepts_positional_target(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify' accepts positional target argument.

        Contract: CC-VERIFY-002
        Perl behavior: target can be specified as positional argument
        Note: This was recently fixed in verify.py
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", "db:sqlite:test.db"])
            
            # Should not be parsing error
            assert result.exit_code != 2, (
                f"Should accept positional target. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )


class TestVerifyGlobalContracts:
    """Test global contracts for 'verify' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # GC-001: Help flag support
    def test_verify_help_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify --help' displays help and exits 0."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", "--help"])
            assert result.exit_code == 0
            assert "verify" in result.output.lower()
            assert "usage" in result.output.lower()

    # GC-002: Global options recognition
    def test_verify_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify' accepts --quiet global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", "--quiet"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_verify_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify' accepts --verbose global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", "--verbose"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_verify_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify' accepts --chdir global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", "--chdir", "/tmp"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_verify_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify' accepts --no-pager global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", "--no-pager"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    # GC-005: Unknown option rejection
    def test_verify_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch verify' rejects unknown options with exit code 2."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["verify", "--nonexistent"])
            assert result.exit_code == 2
            assert "no such option" in result.output.lower()
