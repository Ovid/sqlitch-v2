"""Contract tests for the 'deploy' command.

These tests verify the CLI signature, help output, argument validation,
and error handling for the 'sqlitch deploy' command without testing the
full implementation behavior.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/deploy.pm
- POD: sqitch/lib/sqitch-deploy.pod
- Tests: sqitch/t/deploy.t
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestDeployCommandContract:
    """Contract tests for 'sqlitch deploy' command signature and behavior."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # CC-DEPLOY-001: Optional target
    def test_deploy_accepts_no_arguments(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' works without arguments.

        Contract: CC-DEPLOY-001
        Perl behavior: target argument is optional (uses default from config)
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy"])

            # Should not be parsing error
            assert result.exit_code != 2, (
                f"Should accept command without arguments. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    # CC-DEPLOY-002: Positional target
    def test_deploy_accepts_positional_target(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' accepts positional target argument.

        Contract: CC-DEPLOY-002
        Perl behavior: target can be specified as positional argument
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "db:sqlite:test.db"])

            # Should not be parsing error
            assert result.exit_code != 2, (
                f"Should accept positional target. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    # CC-DEPLOY-003: Target option
    def test_deploy_accepts_target_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' accepts --target option.

        Contract: CC-DEPLOY-003
        Perl behavior: target can be specified via --target option
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "--target", "db:sqlite:test.db"])

            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --target option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )


class TestDeployGlobalContracts:
    """Test global contracts for 'deploy' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # GC-001: Help flag support
    def test_deploy_help_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy --help' displays help and exits 0."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "--help"])
            assert result.exit_code == 0
            assert "deploy" in result.output.lower()
            assert "usage" in result.output.lower()

    # GC-002: Global options recognition
    def test_deploy_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' accepts --quiet global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "--quiet"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_deploy_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' accepts --verbose global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "--verbose"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_deploy_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' accepts --chdir global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "--chdir", "/tmp"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_deploy_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' accepts --no-pager global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "--no-pager"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    # GC-005: Unknown option rejection
    def test_deploy_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch deploy' rejects unknown options with exit code 2."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["deploy", "--nonexistent"])
            assert result.exit_code == 2
            assert "no such option" in result.output.lower()
