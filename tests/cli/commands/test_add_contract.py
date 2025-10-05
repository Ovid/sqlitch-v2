"""Contract tests for the 'add' command.

These tests verify the CLI signature, help output, argument validation,
and error handling for the 'sqlitch add' command without testing the
full implementation behavior.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/add.pm
- POD: sqitch/lib/sqitch-add.pod
- Tests: sqitch/t/add.t
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


class TestAddCommandContract:
    """Contract tests for 'sqlitch add' command signature and behavior."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # CC-ADD-001: Required change name enforcement
    def test_add_requires_change_name(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' without arguments exits with code 2.

        Contract: CC-ADD-001
        Perl behavior: Missing required argument should exit 2
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add"])
            
            assert result.exit_code == 2, (
                f"Expected exit code 2 for missing change_name, got {result.exit_code}. "
                f"Output: {result.output}"
            )
            assert "change_name" in result.output.lower() or "missing" in result.output.lower(), (
                f"Error message should mention missing change_name. Got: {result.output}"
            )

    # CC-ADD-002: Valid change name acceptance
    def test_add_accepts_valid_change_name(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add my_change' accepts the change name.

        Contract: CC-ADD-002
        Perl behavior: Should accept valid change name without parsing error
        """
        with runner.isolated_filesystem():
            # Note: This will fail if not in a SQLitch project, but should NOT
            # fail with a parsing/argument error (exit code 2)
            result = runner.invoke(main, ["add", "my_test_change"])
            
            # Should not be exit code 2 (parsing/argument error)
            assert result.exit_code != 2, (
                f"Should accept change name without argument parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )
            
            # Exit code might be 0 (success) or 1 (implementation error like "not in project")
            # but NOT 2 (argument parsing error)
            assert result.exit_code in [0, 1], (
                f"Expected exit code 0 or 1, got {result.exit_code}. Output: {result.output}"
            )

    # CC-ADD-003: Optional note parameter
    def test_add_accepts_note_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --note option.

        Contract: CC-ADD-003
        Perl behavior: --note is an optional parameter that should be accepted
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "my_change", "--note", "Test note"])
            
            # Should not fail with "no such option" error (exit code 2)
            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --note option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )

    def test_add_accepts_requires_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --requires option.

        Perl behavior: --requires specifies dependencies
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "my_change", "--requires", "other_change"])
            
            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --requires option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )

    def test_add_accepts_conflicts_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --conflicts option.

        Perl behavior: --conflicts specifies conflicting changes
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "my_change", "--conflicts", "other_change"])
            
            assert result.exit_code != 2 or "no such option" not in result.output.lower(), (
                f"Should accept --conflicts option. Exit code: {result.exit_code}, "
                f"Output: {result.output}"
            )


class TestAddGlobalContracts:
    """Test global contracts (GC-001, GC-002) for 'add' command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Provide a Click test runner."""
        return CliRunner()

    # GC-001: Help flag support
    def test_add_help_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add --help' displays help and exits 0.

        Contract: GC-001
        Global contract: All commands must support --help
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "--help"])
            
            assert result.exit_code == 0, (
                f"Expected exit code 0 for --help, got {result.exit_code}. "
                f"Output: {result.output}"
            )
            
            # Help output should contain key elements
            assert "add" in result.output.lower(), "Help should mention 'add' command"
            assert "usage" in result.output.lower() or "synopsis" in result.output.lower(), (
                "Help should include usage/synopsis section"
            )
            
            # Should mention the change_name argument
            assert "change" in result.output.lower(), (
                "Help should describe the change_name argument"
            )

    # GC-002: Global options recognition
    def test_add_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --quiet global option.

        Contract: GC-002
        Global contract: All commands must accept global options
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "--quiet", "my_change"])
            
            # Should not fail with "no such option" error
            assert "no such option" not in result.output.lower(), (
                f"Should accept --quiet option. Output: {result.output}"
            )
            
            # Exit code should not be 2 (option parsing error)
            assert result.exit_code != 2, (
                f"Should accept --quiet without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    def test_add_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --verbose global option.

        Contract: GC-002
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "--verbose", "my_change"])
            
            assert "no such option" not in result.output.lower(), (
                f"Should accept --verbose option. Output: {result.output}"
            )
            assert result.exit_code != 2, (
                f"Should accept --verbose without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    def test_add_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --chdir global option.

        Contract: GC-002
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "--chdir", "/tmp", "my_change"])
            
            assert "no such option" not in result.output.lower(), (
                f"Should accept --chdir option. Output: {result.output}"
            )
            assert result.exit_code != 2, (
                f"Should accept --chdir without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    def test_add_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' accepts --no-pager global option.

        Contract: GC-002
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "--no-pager", "my_change"])
            
            assert "no such option" not in result.output.lower(), (
                f"Should accept --no-pager option. Output: {result.output}"
            )
            assert result.exit_code != 2, (
                f"Should accept --no-pager without parsing error. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

    # GC-005: Unknown option rejection
    def test_add_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch add' rejects unknown options with exit code 2.

        Contract: GC-005
        Global contract: Unknown options must be rejected
        """
        with runner.isolated_filesystem():
            result = runner.invoke(main, ["add", "--nonexistent-option", "my_change"])
            
            assert result.exit_code == 2, (
                f"Expected exit code 2 for unknown option, got {result.exit_code}. "
                f"Output: {result.output}"
            )
            
            assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower(), (
                f"Error message should mention unknown option. Got: {result.output}"
            )
