"""Contract tests for the 'bundle' command.

These tests verify the CLI signature, help output, argument validation,
and error handling for the 'sqlitch bundle' command without testing the
full implementation behavior.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/bundle.pm
- POD: sqitch/lib/sqitch-bundle.pod
- Tests: sqitch/t/bundle.t
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestBundleCommandContract:
    """Contract tests for 'sqlitch bundle' command signature and behavior."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # CC-BUNDLE-001: No required arguments
    def test_bundle_accepts_no_arguments(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' works without arguments.

        Contract: CC-BUNDLE-001
        Perl behavior: bundle command has no required arguments
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle"])
            
            # Should not be exit code 2 (parsing/argument error)
            assert result.exit_code != 2, (
                f"Should accept command without arguments. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )
            
            # Exit code might be 0 (success) or 1 (not implemented/project error)
            assert result.exit_code in [0, 1], (
                f"Expected exit code 0 or 1, got {result.exit_code}. Output: {result.output}"
            )

    # CC-BUNDLE-002: Optional destination
    def test_bundle_accepts_destination_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --dest option.

        Contract: CC-BUNDLE-002
        Perl behavior: --dest specifies bundle destination directory
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle", "--dest", "/tmp/bundle"])
            
            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --dest option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )


class TestBundleGlobalContracts:
    """Test global contracts for 'bundle' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # GC-001: Help flag support
    def test_bundle_help_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle --help' displays help and exits 0.

        Contract: GC-001
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle", "--help"])
            
            assert result.exit_code == 0, (
                f"Expected exit code 0 for --help, got {result.exit_code}. "
                f"Output: {result.output}"
            )
            assert "bundle" in result.output.lower(), "Help should mention 'bundle' command"
            assert "usage" in result.output.lower(), "Help should include usage section"

    # GC-002: Global options recognition
    def test_bundle_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --quiet global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle", "--quiet"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_bundle_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --verbose global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle", "--verbose"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_bundle_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --chdir global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle", "--chdir", "/tmp"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_bundle_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --no-pager global option."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle", "--no-pager"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    # GC-005: Unknown option rejection
    def test_bundle_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' rejects unknown options with exit code 2."""
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["bundle", "--nonexistent"])
            assert result.exit_code == 2
            assert "no such option" in result.output.lower()
