"""Contract parity tests for ``sqlitch tag``."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_tag_adds_to_plan(runner: CliRunner) -> None:
    """sqlitch tag adds a tag entry to the plan file."""

    with isolated_test_context(runner) as (runner, temp_dir):
        # Initialize project
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        # Add a change
        result = runner.invoke(main, ["add", "users_table", "--note", "Create users table"])
        assert result.exit_code == 0

        # Tag the change
        result = runner.invoke(main, ["tag", "v1.0", "users_table"])
        assert result.exit_code == 0
        assert "Tagged users_table with @v1.0" in result.output

        # Verify plan file
        plan_content = (temp_dir / "sqitch.plan").read_text(encoding="utf-8")
        # Compact format: @v1.0 <timestamp> <planner>
        assert "@v1.0" in plan_content
        assert "users_table" in plan_content


def test_tag_lists_tags(runner: CliRunner) -> None:
    """sqlitch tag --list displays plan tags."""

    with isolated_test_context(runner) as (runner, temp_dir):
        # Initialize project with tags
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["add", "change1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tag", "tag1", "change1"])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tag", "--list"])
        assert result.exit_code == 0
        assert "@tag1" in result.output


def test_tag_requires_name(runner: CliRunner) -> None:
    """Tag command without name lists tags (or errors if no plan)."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["tag"])

    # Should error because there's no plan file, not because name is missing
    assert result.exit_code != 0
    assert "No plan file found" in result.output


def test_tag_list_rejects_additional_arguments(runner: CliRunner) -> None:
    """--list should not accept additional parameters."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["tag", "--list", "extra"])

    assert result.exit_code != 0
    assert "--list cannot be combined" in result.output


def test_tag_duplicate_error(runner: CliRunner) -> None:
    """Duplicate tags are rejected."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["add", "change1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tag", "dup", "change1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tag", "dup", "change1"])
        assert result.exit_code != 0
        assert 'Tag "dup" already exists' in result.output


def test_tag_unknown_change_error(runner: CliRunner) -> None:
    """Tagging unknown changes fails."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tag", "tag1", "nonexistent"])
        assert result.exit_code != 0
        assert 'Unknown change "nonexistent"' in result.output


def test_tag_defaults_to_latest_change_when_change_missing(runner: CliRunner) -> None:
    """Tagging without a change name should select the most recent change."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["add", "change1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["add", "change2"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tag", "release"])
        assert result.exit_code == 0
        assert "Tagged change2 with @release" in result.output

        plan_content = (temp_dir / "sqitch.plan").read_text(encoding="utf-8")
        # Compact format: @release <timestamp> <planner>
        # Tag should appear after change2 in the plan
        assert "@release" in plan_content
        assert "change2" in plan_content


def test_tag_reports_error_when_no_changes_exist(runner: CliRunner) -> None:
    """Tagging without any changes should yield a helpful error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tag", "release"])

    assert result.exit_code != 0
    assert "No changes found in plan to tag" in result.output
