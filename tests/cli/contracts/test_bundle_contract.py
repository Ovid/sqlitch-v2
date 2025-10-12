"""Contract parity tests for ``sqlitch bundle``.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/bundle.pm
- POD: sqitch/lib/sqitch-bundle.pod
- Tests: sqitch/t/bundle.t

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


def _seed_project() -> None:
    plan_path = Path("sqitch.plan")
    plan_path.write_text("%project=widgets\n%default_engine=sqlite\n", encoding="utf-8")

    for directory in ("deploy", "revert", "verify"):
        dir_path = Path(directory)
        dir_path.mkdir(parents=True)
        (dir_path / "widgets.sql").write_text(f"-- {directory} script\n", encoding="utf-8")


def test_bundle_creates_default_bundle_directory() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        _seed_project()

        result = runner.invoke(main, ["bundle"])

        assert result.exit_code == 0, result.output
        assert "Bundled project to bundle" in result.output

        bundle_root = Path("bundle")
        assert (
            (bundle_root / "sqitch.plan").read_text(encoding="utf-8").startswith("%project=widgets")
        )
        for directory in ("deploy", "revert", "verify"):
            copied = bundle_root / directory / "widgets.sql"
            assert copied.read_text(encoding="utf-8") == f"-- {directory} script\n"


def test_bundle_honours_dest_option() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        _seed_project()

        result = runner.invoke(main, ["bundle", "--dest", "dist/bundles"])

        assert result.exit_code == 0, result.output
        assert "Bundled project to dist/bundles" in result.output

        bundle_root = Path("dist/bundles")
        assert (bundle_root / "deploy" / "widgets.sql").exists()


def test_bundle_errors_when_plan_missing() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["bundle"])

        assert result.exit_code != 0
        assert "Cannot read plan file" in result.output


def test_bundle_no_plan_flag_skips_plan_copy() -> None:
    runner = CliRunner()

    with isolated_test_context(runner) as (runner, temp_dir):
        for directory in ("deploy", "revert", "verify"):
            dir_path = Path(directory)
            dir_path.mkdir(parents=True)
            (dir_path / "widgets.sql").write_text(f"-- {directory} script\n", encoding="utf-8")

        result = runner.invoke(main, ["bundle", "--no-plan", "--dest", "output"])

        assert result.exit_code == 0, result.output
        bundle_root = Path("output")
        assert not (bundle_root / "sqitch.plan").exists()
        assert (bundle_root / "deploy" / "widgets.sql").exists()


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_bundle_contract.py)
# =============================================================================

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
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["bundle"])

            # Should not be exit code 2 (parsing/argument error)
            assert result.exit_code != 2, (
                f"Should accept command without arguments. "
                f"Exit code: {result.exit_code}, Output: {result.output}"
            )

            # Exit code might be 0 (success) or 1 (not implemented/project error)
            assert result.exit_code in [
                0,
                1,
            ], f"Expected exit code 0 or 1, got {result.exit_code}. Output: {result.output}"

    # CC-BUNDLE-002: Optional destination
    def test_bundle_accepts_destination_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --dest option.

        Contract: CC-BUNDLE-002
        Perl behavior: --dest specifies bundle destination directory
        """
        with isolated_test_context(runner) as (runner, temp_dir):
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
        with isolated_test_context(runner) as (runner, temp_dir):
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
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["bundle", "--quiet"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_bundle_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --verbose global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["bundle", "--verbose"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_bundle_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --chdir global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["bundle", "--chdir", "/tmp"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_bundle_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' accepts --no-pager global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["bundle", "--no-pager"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    # GC-005: Unknown option rejection
    def test_bundle_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch bundle' rejects unknown options with exit code 2."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["bundle", "--nonexistent"])
            assert result.exit_code == 2
            assert "no such option" in result.output.lower()
