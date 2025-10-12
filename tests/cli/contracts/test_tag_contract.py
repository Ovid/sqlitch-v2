"""Contract parity tests for ``sqlitch tag``.

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

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


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_tag_contract.py)
# =============================================================================

class TestTagHelp:
    """Test CC-TAG help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Tag command must support --help flag."""
        result = runner.invoke(main, ["tag", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["tag", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the tag command."""
        result = runner.invoke(main, ["tag", "--help"])
        assert "tag" in result.output.lower()

class TestTagOptionalName:
    """Test CC-TAG-001: Optional tag name (list tags)."""

    def test_tag_without_name_accepted(self, runner):
        """Tag without name must be accepted (lists tags)."""
        result = runner.invoke(main, ["tag"])
        # Should accept (not a parsing error)
        # May exit 0 (success/list), 1 (not implemented), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

class TestTagWithName:
    """Test CC-TAG-002: With tag name."""

    def test_tag_with_name_accepted(self, runner):
        """Tag with name must be accepted."""
        result = runner.invoke(main, ["tag", "v1.0"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_tag_with_note_option(self, runner):
        """Tag with --note option must be accepted."""
        result = runner.invoke(main, ["tag", "v1.0", "--note", "Release version 1.0"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_tag_with_change_option(self, runner):
        """Tag with --change option must be accepted."""
        result = runner.invoke(main, ["tag", "v1.0", "--change", "my_change"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

class TestTagGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Tag must accept --quiet global option."""
        result = runner.invoke(main, ["tag", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Tag must accept --verbose global option."""
        result = runner.invoke(main, ["tag", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Tag must accept --chdir global option."""
        result = runner.invoke(main, ["tag", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Tag must accept --no-pager global option."""
        result = runner.invoke(main, ["tag", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

class TestTagErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Tag must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["tag", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
