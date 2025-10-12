"""Contract parity tests for ``sqlitch rebase``.

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change, Tag
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for isolation."""

    return CliRunner()


def _seed_plan(plan_path: Path) -> tuple[Change, Change, Tag]:
    change_one = Change.create(
        name="core:init",
        script_paths={
            "deploy": Path("deploy") / "core_init.sql",
            "revert": Path("revert") / "core_init.sql",
            "verify": Path("verify") / "core_init.sql",
        },
        planner="Ada Lovelace",
        planned_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        notes="Initialises core schema",
    )

    change_two = Change.create(
        name="widgets:add",
        script_paths={
            "deploy": Path("deploy") / "widgets_add.sql",
            "revert": Path("revert") / "widgets_add.sql",
            "verify": Path("verify") / "widgets_add.sql",
        },
        planner="Ada Lovelace",
        planned_at=datetime(2025, 1, 2, 0, 0, tzinfo=timezone.utc),
        notes="Adds widgets table",
        dependencies=("core:init",),
        tags=("v1.0",),
    )

    tag = Tag(
        name="v1.0",
        change_ref=change_two.name,
        planner="Ada Lovelace",
        tagged_at=datetime(2025, 1, 2, 0, 5, tzinfo=timezone.utc),
    )

    write_plan(
        project_name="widgets",
        default_engine="sqlite",
        entries=(change_one, change_two, tag),
        plan_path=plan_path,
    )

    # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
    config_path = plan_path.parent / "sqitch.conf"
    config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

    return change_one, change_two, tag


def test_rebase_requires_target(runner: CliRunner) -> None:
    """Rebase should require a target to be provided explicitly or via config."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["rebase", "--log-only"])

        assert result.exit_code != 0
        assert "A deployment target must be provided" in result.output


def test_rebase_log_only_shows_revert_and_deploy_sequences(runner: CliRunner) -> None:
    """Log-only runs should outline both the revert and deploy stages."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
            ],
        )

        assert result.exit_code == 0, result.output
        assert (
            "Rebasing plan 'widgets' on target 'db:sqlite:rebase.db' (log-only)." in result.output
        )
        first_revert = result.output.index(f"Would revert change {change_two.name}")
        second_revert = result.output.index(f"Would revert change {change_one.name}")
        assert first_revert < second_revert
        first_deploy = result.output.index(f"Would deploy change {change_one.name}")
        second_deploy = result.output.index(f"Would deploy change {change_two.name}")
        assert first_deploy < second_deploy
        assert "Log-only run; no database changes were applied." in result.output


def test_rebase_from_option_limits_redeploy_scope(runner: CliRunner) -> None:
    """Providing --from should restrict the redeployment set."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
                "--from",
                change_two.name,
            ],
        )

        assert result.exit_code == 0, result.output
        assert f"Would deploy change {change_two.name}" in result.output
        assert f"Would deploy change {change_one.name}" not in result.output


def test_rebase_onto_option_limits_revert_scope(runner: CliRunner) -> None:
    """Providing --onto should keep earlier changes deployed."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_one, change_two, tag = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
                "--onto",
                tag.name,
            ],
        )

        assert result.exit_code == 0, result.output
        assert f"Would revert change {change_two.name}" in result.output
        assert f"Would revert change {change_one.name}" not in result.output


def test_rebase_unknown_reference_fails(runner: CliRunner) -> None:
    """Unknown change or tag references should surface helpful errors."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "rebase",
                "--log-only",
                "--target",
                "db:sqlite:rebase.db",
                "--from",
                "missing:change",
            ],
        )

        assert result.exit_code != 0
        assert "Plan does not contain change 'missing:change'" in result.output


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_rebase_contract.py)
# =============================================================================


class TestRebaseHelp:
    """Test CC-REBASE help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Rebase command must support --help flag."""
        result = runner.invoke(main, ["rebase", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["rebase", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the rebase command."""
        result = runner.invoke(main, ["rebase", "--help"])
        assert "rebase" in result.output.lower()


class TestRebaseOptionalTarget:
    """Test CC-REBASE-001: Optional target."""

    def test_rebase_without_target_accepted(self, runner):
        """Rebase without target must be accepted (uses default)."""
        result = runner.invoke(main, ["rebase"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_rebase_with_positional_target(self, runner):
        """Rebase with positional target must be accepted."""
        result = runner.invoke(main, ["rebase", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_rebase_with_target_option(self, runner):
        """Rebase with --target option must be accepted."""
        result = runner.invoke(main, ["rebase", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestRebaseGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Rebase must accept --quiet global option."""
        result = runner.invoke(main, ["rebase", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Rebase must accept --verbose global option."""
        result = runner.invoke(main, ["rebase", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Rebase must accept --chdir global option."""
        result = runner.invoke(main, ["rebase", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Rebase must accept --no-pager global option."""
        result = runner.invoke(main, ["rebase", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestRebaseErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Rebase must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["rebase", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
