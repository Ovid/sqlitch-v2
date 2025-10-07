"""Contract parity tests for ``sqlitch plan``."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main
from sqlitch.plan.formatter import format_plan, write_plan
from sqlitch.plan.model import Change, Tag


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

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan"])

        assert result.exit_code == 0, result.output
        expected = plan_path.read_text(encoding="utf-8")
        assert result.stdout == expected


def test_plan_supports_change_filter_and_no_header(runner: CliRunner) -> None:
    """Change filtering and header suppression should mirror Sqitch ergonomics."""

    with runner.isolated_filesystem():
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

    with runner.isolated_filesystem():
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
        # Note: compact format doesn't embed tags in change entries
        assert second["tags"] == []
        assert third["type"] == "tag"
        assert third["name"] == "v1.0"
        assert third["change"] == change_two.name


def test_plan_reports_missing_plan_file(runner: CliRunner) -> None:
    """Invoking sqlitch plan without a plan file should raise a command error."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["plan"])

        assert result.exit_code != 0
    assert "No plan file found" in result.stderr


def test_plan_tag_filter_outputs_tag_entry(runner: CliRunner) -> None:
    """Selecting a tag should limit the output to matching tag entries."""

    with runner.isolated_filesystem():
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

    with runner.isolated_filesystem():
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

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--change", "missing"])

        assert result.exit_code != 0
    assert "Change filter matched no entries: missing" in result.stderr


def test_plan_reports_missing_tag_filter(runner: CliRunner) -> None:
    """A missing tag filter should produce a descriptive error."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--tag", "v9.9"])

        assert result.exit_code != 0
    assert "Tag filter matched no entries: v9.9" in result.stderr


def test_plan_project_mismatch_errors(runner: CliRunner) -> None:
    """Filtering by project should enforce matching plan metadata."""

    with runner.isolated_filesystem():
        plan_path = Path("sqlitch.plan")
        _seed_plan(plan_path)

        result = runner.invoke(main, ["plan", "--project", "other"])

        assert result.exit_code != 0
    assert "does not match requested project 'other'" in result.stderr


def test_plan_warns_for_forward_dependencies(runner: CliRunner) -> None:
    """Forward-referenced dependencies should emit warnings without failing."""

    with runner.isolated_filesystem():
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
