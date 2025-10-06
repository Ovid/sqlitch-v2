"""Contract tests for the 'checkout' command.

These tests verify the CLI signature, help output, argument validation,
and error handling for the 'sqlitch checkout' command without testing the
full implementation behavior.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/checkout.pm
- POD: sqitch/lib/sqitch-checkout.pod
- Tests: sqitch/t/checkout.t
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestCheckoutCommandContract:
    """Contract tests for 'sqlitch checkout' command signature and behavior."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # CC-CHECKOUT-001: No required arguments (uses --target option)
    def test_checkout_accepts_no_arguments(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' can be invoked without arguments.

        Contract: CC-CHECKOUT-001
        Perl behavior: checkout has no required arguments (target comes from config)
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["checkout"])

            # Should not be parsing error (exit 2)
            # May exit 1 for missing target/project, but not 2
            assert result.exit_code != 2, (
                f"Should not fail with parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )


class TestCheckoutGlobalContracts:
    """Test global contracts for 'checkout' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # GC-001: Help flag support
    def test_checkout_help_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout --help' displays help and exits 0."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["checkout", "--help"])
            assert result.exit_code == 0
            assert "checkout" in result.output.lower()
            assert "usage" in result.output.lower()

    # GC-002: Global options recognition
    def test_checkout_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --quiet global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["checkout", "--quiet"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_checkout_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --verbose global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["checkout", "--verbose"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_checkout_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --chdir global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["checkout", "--chdir", "/tmp"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_checkout_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --no-pager global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["checkout", "--no-pager"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    # GC-005: Unknown option rejection
    def test_checkout_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' rejects unknown options with exit code 2."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["checkout", "--nonexistent"])
            assert result.exit_code == 2
            assert "no such option" in result.output.lower()
