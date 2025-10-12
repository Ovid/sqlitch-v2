"""Contract parity tests for ``sqlitch revert``.

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


def test_revert_requires_target(runner: CliRunner) -> None:
    """Revert should require a target to be provided explicitly or via config."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["revert", "--log-only"])

        assert result.exit_code != 0
        assert "A deployment target must be provided" in result.output


def test_revert_log_only_outputs_changes_in_reverse(runner: CliRunner) -> None:
    """Log-only mode should list changes in reverse deployment order."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "revert",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
            ],
        )

        assert result.exit_code == 0, result.output
        first_index = result.output.index(f"Would revert change {change_two.name}")
        second_index = result.output.index(f"Would revert change {change_one.name}")
        assert first_index < second_index
        assert "Log-only run; no database changes were applied." in result.output


def test_revert_conflicting_filters_error(runner: CliRunner) -> None:
    """Providing both --to-change and --to-tag should raise an error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_one, _, tag = _seed_plan(plan_path)

        result = runner.invoke(
            main,
            [
                "revert",
                "--log-only",
                "--target",
                "db:sqlite:deploy.db",
                "--to-change",
                change_one.name,
                "--to-tag",
                tag.name,
            ],
        )

        assert result.exit_code != 0
        assert "Cannot combine --to-change and --to-tag" in result.output


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_revert_contract.py)
# =============================================================================

class TestRevertHelp:
    """Test CC-REVERT help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Revert command must support --help flag."""
        result = runner.invoke(main, ["revert", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["revert", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the revert command."""
        result = runner.invoke(main, ["revert", "--help"])
        assert "revert" in result.output.lower()

class TestRevertOptionalTarget:
    """Test CC-REVERT-001: Optional target."""

    def test_revert_without_target_accepted(self, runner):
        """Revert without target must be accepted (uses default)."""
        result = runner.invoke(main, ["revert"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented/no target), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

class TestRevertPositionalTarget:
    """Test CC-REVERT-002: Positional target."""

    def test_revert_with_positional_target(self, runner):
        """Revert with positional target must be accepted."""
        result = runner.invoke(main, ["revert", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_revert_with_target_option(self, runner):
        """Revert with --target option must be accepted."""
        result = runner.invoke(main, ["revert", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_revert_with_change_and_target(self, runner):
        """Revert with change and target must be accepted."""
        result = runner.invoke(main, ["revert", "my_change", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

class TestRevertGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Revert must accept --quiet global option."""
        result = runner.invoke(main, ["revert", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Revert must accept --verbose global option."""
        result = runner.invoke(main, ["revert", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Revert must accept --chdir global option."""
        result = runner.invoke(main, ["revert", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Revert must accept --no-pager global option."""
        result = runner.invoke(main, ["revert", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

class TestRevertErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Revert must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["revert", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
