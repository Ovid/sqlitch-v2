"""Contract parity tests for ``sqlitch checkout``.

Perl Reference:
- Source: sqitch/lib/App/Sqitch/Command/checkout.pm
- POD: sqitch/lib/sqitch-checkout.pod
- Tests: sqitch/t/checkout.t

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for isolation."""

    return CliRunner()


def _seed_plan(plan_path: Path) -> None:
    change = Change.create(
        name="widgets:init",
        script_paths={
            "deploy": Path("deploy") / "widgets_init.sql",
            "revert": Path("revert") / "widgets_init.sql",
            "verify": Path("verify") / "widgets_init.sql",
        },
        planner="Ada Lovelace",
        planned_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        notes="Initialises widgets schema",
    )

    write_plan(
        project_name="widgets",
        default_engine="sqlite",
        entries=(change,),
        plan_path=plan_path,
    )


def test_checkout_requires_vcs_configuration(runner: CliRunner) -> None:
    """Checkout should fail when no VCS command is configured."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "checkout",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
            ],
        )

        assert result.exit_code != 0
        assert "No VCS configured" in result.output


def test_checkout_log_only_reports_pipeline(runner: CliRunner) -> None:
    """Log-only mode should describe the checkout pipeline and exit successfully."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "checkout",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
                "--mode",
                "tag:v1.0",
            ],
            env={"SQLITCH_VCS_COMMAND": "git checkout feature/login"},
        )

        assert result.exit_code == 0, result.output
        assert "Would revert target 'db:sqlite:deploy.db' using mode 'tag:v1.0'" in result.output
        assert "Would run VCS command: git checkout feature/login" in result.output
        assert "Would deploy pending changes to target 'db:sqlite:deploy.db'" in result.output
        assert "Log-only run; no database changes were applied." in result.output


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_checkout_contract.py)
# =============================================================================


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
        with isolated_test_context(runner) as (runner, temp_dir):
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
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["checkout", "--help"])
            assert result.exit_code == 0
            assert "checkout" in result.output.lower()
            assert "usage" in result.output.lower()

    # GC-002: Global options recognition
    def test_checkout_accepts_quiet_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --quiet global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["checkout", "--quiet"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_checkout_accepts_verbose_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --verbose global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["checkout", "--verbose"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_checkout_accepts_chdir_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --chdir global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["checkout", "--chdir", "/tmp"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    def test_checkout_accepts_no_pager_flag(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' accepts --no-pager global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["checkout", "--no-pager"])
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2

    # GC-005: Unknown option rejection
    def test_checkout_rejects_unknown_option(self, runner: CliRunner) -> None:
        """Test that 'sqlitch checkout' rejects unknown options with exit code 2."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["checkout", "--nonexistent"])
            assert result.exit_code == 2
            assert "no such option" in result.output.lower()
