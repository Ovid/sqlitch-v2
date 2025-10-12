"""Contract parity tests for ``sqlitch plan``.

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.plan.formatter import format_plan, write_plan
from sqlitch.plan.model import Change, Tag
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for filesystem isolation."""

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
        # Note: tags field is not used in compact format - tags are separate entries
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


def test_plan_outputs_plan_file_by_default(runner: CliRunner) -> None:
    """sqlitch plan should emit the plan file verbatim when no filters apply."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan"])

        assert result.exit_code == 0, result.output
        expected = plan_path.read_text(encoding="utf-8")
        assert result.stdout == expected


def test_plan_supports_change_filter_and_no_header(runner: CliRunner) -> None:
    """Change filtering and header suppression should mirror Sqitch ergonomics."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_one, change_two, tag = _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--change", change_two.name, "--no-header"])

        assert result.exit_code == 0, result.output

        rendered = format_plan(
            project_name="widgets",
            default_engine="sqlite",
            entries=(change_two, tag),
            base_path=plan_path.parent,
        )
        expected_lines = [line for line in rendered.splitlines() if not line.startswith("%")]
        expected = "\n".join(expected_lines) + "\n"
        assert result.stdout == expected


def test_plan_supports_json_format(runner: CliRunner) -> None:
    """The JSON format should expose structured plan metadata."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_one, change_two, _ = _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--format", "json"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["project"] == "widgets"
        assert payload["default_engine"] == "sqlite"
        assert payload["plan_path"].endswith("sqlitch.plan")
        assert payload["missing_dependencies"] == []

        entries = payload["entries"]
        assert len(entries) == 3

        first, second, third = entries
        assert first["name"] == change_one.name
        assert first["type"] == "change"
        assert first["scripts"]["deploy"].endswith("core_init.sql")
        assert second["dependencies"] == ["core:init"]
        # Tags recorded on separate entries are surfaced in JSON metadata.
        assert second["tags"] == ["v1.0"]
        assert third["type"] == "tag"
        assert third["name"] == "v1.0"
        assert third["change"] == change_two.name


def test_plan_reports_missing_plan_file(runner: CliRunner) -> None:
    """Invoking sqlitch plan without a plan file should raise a command error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["plan"])

        assert result.exit_code != 0
    assert "No plan file found" in result.stderr


def test_plan_tag_filter_outputs_tag_entry(runner: CliRunner) -> None:
    """Selecting a tag should limit the output to matching tag entries."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _, change_two, tag = _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--tag", tag.name])

        assert result.exit_code == 0, result.output

        rendered = format_plan(
            project_name="widgets",
            default_engine="sqlite",
            entries=(tag,),
            base_path=plan_path.parent,
        )
        assert result.stdout == rendered


def test_plan_short_option_strips_notes_metadata(runner: CliRunner) -> None:
    """The --short flag should omit notes metadata from human output."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--short"])

        assert result.exit_code == 0, result.output
        stdout = result.stdout
        assert "notes=" not in stdout
        assert "widgets" in stdout
        assert "Adds widgets table" not in stdout


def test_plan_reports_missing_change_filter(runner: CliRunner) -> None:
    """A missing change filter should produce a descriptive error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--change", "missing"])

        assert result.exit_code != 0
    assert "Change filter matched no entries: missing" in result.stderr


def test_plan_reports_missing_tag_filter(runner: CliRunner) -> None:
    """A missing tag filter should produce a descriptive error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--tag", "v9.9"])

        assert result.exit_code != 0
    assert "Tag filter matched no entries: v9.9" in result.stderr


def test_plan_project_mismatch_errors(runner: CliRunner) -> None:
    """Filtering by project should enforce matching plan metadata."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--project", "other"])

        assert result.exit_code != 0
    assert "does not match requested project 'other'" in result.stderr


def test_plan_warns_for_forward_dependencies(runner: CliRunner) -> None:
    """Forward-referenced dependencies should emit warnings without failing."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change = Change.create(
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
        )

        write_plan(
            project_name="widgets",
            default_engine="sqlite",
            entries=(change,),
            plan_path=plan_path,
        )

        # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
        config_path = plan_path.parent / "sqitch.conf"
        config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

        result = runner.invoke(main, ["plan"])

        assert result.exit_code == 0, result.output
    assert "widgets:add" in result.output
    assert "Warning" in result.stderr
    assert "core:init" in result.stderr


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_plan_contract.py)
# =============================================================================


class TestPlanHelp:
    """Test CC-PLAN help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Plan command must support --help flag."""
        result = runner.invoke(main, ["plan", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["plan", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the plan command."""
        result = runner.invoke(main, ["plan", "--help"])
        assert "plan" in result.output.lower()


class TestPlanOptionalTarget:
    """Test CC-PLAN-001: Optional target."""

    def test_plan_without_target_accepted(self, runner):
        """Plan without target must be accepted (shows project plan)."""
        result = runner.invoke(main, ["plan"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (no plan file), or show plan
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_plan_with_positional_target(self, runner):
        """Plan with positional target must be accepted."""
        result = runner.invoke(main, ["plan", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_plan_with_target_option(self, runner):
        """Plan with --target option must be accepted."""
        result = runner.invoke(main, ["plan", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestPlanGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Plan must accept --quiet global option."""
        result = runner.invoke(main, ["plan", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Plan must accept --verbose global option."""
        result = runner.invoke(main, ["plan", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Plan must accept --chdir global option."""
        result = runner.invoke(main, ["plan", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Plan must accept --no-pager global option."""
        result = runner.invoke(main, ["plan", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestPlanErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Plan must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["plan", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
