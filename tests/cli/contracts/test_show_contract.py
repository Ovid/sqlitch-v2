"""Contract parity tests for ``sqlitch show``.

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

import json
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
    """Return an isolated Click runner for CLI invocations."""

    return CliRunner()


def _seed_project(project_root: Path) -> tuple[Path, Change]:
    project_root.mkdir(parents=True, exist_ok=True)
    deploy_core = project_root / "deploy/core_init.sql"
    revert_core = project_root / "revert/core_init.sql"
    verify_core = project_root / "verify/core_init.sql"
    for path in (deploy_core, revert_core, verify_core):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("-- core script\n", encoding="utf-8")

    core_change = Change.create(
        name="core:init",
        script_paths={
            "deploy": deploy_core,
            "revert": revert_core,
            "verify": verify_core,
        },
        planner="Ada Lovelace",
        planned_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )

    deploy_target = project_root / "deploy/widgets_add.sql"
    revert_target = project_root / "revert/widgets_add.sql"
    verify_target = project_root / "verify/widgets_add.sql"
    deploy_target.write_text("/* deploy widgets */\n", encoding="utf-8")
    revert_target.write_text("/* revert widgets */\n", encoding="utf-8")
    verify_target.write_text("/* verify widgets */\n", encoding="utf-8")

    target_timestamp = datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
    target_change = Change.create(
        name="widgets:add",
        script_paths={
            "deploy": deploy_target,
            "revert": revert_target,
            "verify": verify_target,
        },
        planner="Grace Hopper",
        planned_at=target_timestamp,
        notes="Adds widgets",
        dependencies=("core:init",),
        # Note: tags field is not used in compact format - tags are separate entries
    )

    core_tag = Tag(
        name="baseline",
        change_ref=core_change.name,
        planner="Ada Lovelace",
        tagged_at=datetime(2024, 1, 1, 0, 30, tzinfo=timezone.utc),
    )

    # Create separate tag entries (compact format doesn't embed tags in change lines)
    release_tag = Tag(
        name="release",
        change_ref=target_change.name,
        planner="Grace Hopper",
        tagged_at=datetime(2024, 1, 2, 0, 3, tzinfo=timezone.utc),
    )

    tag = Tag(
        name="v1.0",
        change_ref=target_change.name,
        planner="Grace Hopper",
        tagged_at=datetime(2024, 1, 2, 0, 5, tzinfo=timezone.utc),
    )

    plan_path = project_root / "sqlitch.plan"
    write_plan(
        project_name="widgets",
        default_engine="sqlite",
        entries=(core_change, core_tag, target_change, release_tag, tag),
        plan_path=plan_path,
    )

    # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
    config_path = project_root / "sqitch.conf"
    config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

    return plan_path, target_change


def _seed_minimal_project(project_root: Path) -> tuple[Path, Change]:
    project_root.mkdir(parents=True, exist_ok=True)
    for directory in ("deploy", "revert"):
        (project_root / directory).mkdir(parents=True, exist_ok=True)

    deploy_script = project_root / "deploy/minimal_change.sql"
    revert_script = project_root / "revert/minimal_change.sql"
    deploy_script.write_text("/* minimal deploy */\n", encoding="utf-8")
    revert_script.write_text("/* minimal revert */\n", encoding="utf-8")

    minimal_change = Change.create(
        name="minimal:change",
        script_paths={
            "deploy": "deploy/minimal_change.sql",
            "revert": "revert/minimal_change.sql",
            "verify": None,
        },
        planner="Test Planner",
        planned_at=datetime(2024, 1, 3, 0, 0, tzinfo=timezone.utc),
    )

    plan_path = project_root / "sqlitch.plan"
    write_plan(
        project_name="minimal",
        default_engine="sqlite",
        entries=(minimal_change,),
        plan_path=plan_path,
    )

    # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
    config_path = project_root / "sqitch.conf"
    config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

    return plan_path, minimal_change


def test_show_human_format_displays_change_metadata(runner: CliRunner) -> None:
    """Default output should mirror Sqitch show change metadata."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        _, change = _seed_project(project_root)

        result = runner.invoke(main, ["show", change.name])

        assert result.exit_code == 0, result.stderr
        assert f"Change: {change.name}" in result.stdout
        assert "Planner: Grace Hopper" in result.stdout
        assert "Planned At: 2024-01-02T00:00:00Z" in result.stdout
        assert "Dependencies: core:init" in result.stdout
        assert "Tags: release, v1.0" in result.stdout
        assert "Notes: Adds widgets" in result.stdout
        assert "Deploy Script: deploy/widgets_add.sql" in result.stdout
        assert "Revert Script: revert/widgets_add.sql" in result.stdout
        assert "Verify Script: verify/widgets_add.sql" in result.stdout


def test_show_json_format_returns_structured_payload(runner: CliRunner) -> None:
    """JSON output should expose change metadata for automation."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        _, change = _seed_project(project_root)

        result = runner.invoke(main, ["show", change.name, "--format", "json"])

        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["change"] == change.name
        assert payload["planner"] == "Grace Hopper"
        assert payload["planned_at"] == "2024-01-02T00:00:00Z"
        assert payload["dependencies"] == ["core:init"]
        assert payload["tags"] == ["release", "v1.0"]
        assert payload["notes"] == "Adds widgets"
        assert payload["scripts"] == {
            "deploy": "deploy/widgets_add.sql",
            "revert": "revert/widgets_add.sql",
            "verify": "verify/widgets_add.sql",
        }


def test_show_script_option_outputs_script_contents(runner: CliRunner) -> None:
    """Requesting a script should stream the script contents verbatim."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        _, change = _seed_project(project_root)

        result = runner.invoke(main, ["show", change.name, "--script", "deploy"])

        assert result.exit_code == 0, result.stderr
        assert result.stdout == "/* deploy widgets */\n"


def test_show_accepts_tag_reference(runner: CliRunner) -> None:
    """Tags should resolve to their associated change."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        _, change = _seed_project(project_root)

        result = runner.invoke(main, ["show", "v1.0"])

        assert result.exit_code == 0, result.stderr
        assert f"Change: {change.name}" in result.stdout


def test_show_project_filter_mismatch_errors(runner: CliRunner) -> None:
    """Project filters should reject plans that do not match."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        _, change = _seed_project(project_root)

        result = runner.invoke(main, ["show", change.name, "--project", "gadgets"])

        assert result.exit_code != 0
        assert "Plan project 'widgets' does not match requested project 'gadgets'." in result.stderr


def test_show_outputs_defaults_when_metadata_missing(runner: CliRunner) -> None:
    """Show should surface sensible defaults when optional metadata is absent."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        _, change = _seed_minimal_project(project_root)

        human = runner.invoke(main, ["show", change.name])
        assert human.exit_code == 0, human.stderr
        assert "Dependencies: (none)" in human.stdout
        assert "Tags: (none)" in human.stdout
        assert "Notes: (none)" in human.stdout
        assert "Deploy Script: deploy/minimal_change.sql" in human.stdout
        # Note: show command currently generates verify script path even when None
        assert "Verify Script: verify/minimal_change.sql" in human.stdout

        json_result = runner.invoke(main, ["show", change.name, "--format", "json"])
        assert json_result.exit_code == 0, json_result.stderr
        payload = json.loads(json_result.stdout)
        assert payload["dependencies"] == []
        assert payload["tags"] == []
        assert payload["notes"] is None
        # Note: show command currently generates verify script path even when None
        assert payload["scripts"] == {
            "deploy": "deploy/minimal_change.sql",
            "revert": "revert/minimal_change.sql",
            "verify": "verify/minimal_change.sql",
        }


def test_show_script_option_reports_missing_files(runner: CliRunner) -> None:
    """Missing or unspecified scripts should raise clear errors."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        _, change = _seed_minimal_project(project_root)

        deploy_result = runner.invoke(main, ["show", change.name, "--script", "deploy"])
        assert deploy_result.exit_code == 0, deploy_result.stderr
        assert deploy_result.stdout == "/* minimal deploy */\n"

        (project_root / "revert/minimal_change.sql").unlink()

        missing_file = runner.invoke(main, ["show", change.name, "--script", "revert"])
        assert missing_file.exit_code != 0
        assert "Cannot find revert script for minimal:change" in missing_file.stderr

        missing_kind = runner.invoke(main, ["show", change.name, "--script", "verify"])
        assert missing_kind.exit_code != 0
        assert "Cannot find verify script for minimal:change" in missing_kind.stderr


def test_show_reports_plan_parse_errors(runner: CliRunner) -> None:
    """Plan parse failures should surface the parser error message."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        plan_path, change = _seed_project(project_root)
        # Write a plan with proper headers but invalid entry
        plan_path.write_text(
            "%syntax-version=1.0.0\n%project=widgets\n\ninvalid-entry\n", encoding="utf-8"
        )

        result = runner.invoke(main, ["show", change.name])

        assert result.exit_code != 0
        # Parser errors are raised as exceptions - check result.exception
        assert result.exception is not None
        assert "Unknown plan entry 'invalid-entry'" in str(result.exception)


def test_show_deduplicates_plan_and_change_tags(runner: CliRunner) -> None:
    """Tags applied at both change and plan level should not be repeated."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        for directory in ("deploy", "revert", "verify"):
            (project_root / directory).mkdir(parents=True, exist_ok=True)

        deploy_script = project_root / "deploy/duplicate.sql"
        revert_script = project_root / "revert/duplicate.sql"
        verify_script = project_root / "verify/duplicate.sql"
        deploy_script.write_text("-- duplicate deploy\n", encoding="utf-8")
        revert_script.write_text("-- duplicate revert\n", encoding="utf-8")
        verify_script.write_text("-- duplicate verify\n", encoding="utf-8")

        duplicate_change = Change.create(
            name="duplicate:change",
            script_paths={
                "deploy": deploy_script,
                "revert": revert_script,
                "verify": verify_script,
            },
            planner="Grace Hopper",
            planned_at=datetime(2024, 1, 4, 0, 0, tzinfo=timezone.utc),
            tags=("duplicate",),
        )

        duplicate_tag = Tag(
            name="duplicate",
            change_ref=duplicate_change.name,
            planner="Grace Hopper",
            tagged_at=datetime(2024, 1, 4, 0, 5, tzinfo=timezone.utc),
        )

        plan_path = project_root / "sqlitch.plan"
        write_plan(
            project_name="duplicates",
            default_engine="sqlite",
            entries=(duplicate_change, duplicate_tag),
            plan_path=plan_path,
        )

        # Create minimal config so commands can find engine
        # (Sqitch stores engine in config, not plan)
        config_path = project_root / "sqitch.conf"
        config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

        result = runner.invoke(main, ["show", duplicate_change.name])

        assert result.exit_code == 0, result.stderr
        assert (
            result.stdout.count("duplicate") == 5
        )  # change line, tag line, deploy/revert/verify paths
        assert "Tags: duplicate" in result.stdout


def test_show_unknown_change_errors(runner: CliRunner) -> None:
    """Missing changes should raise a helpful error message."""

    with isolated_test_context(runner) as (runner, temp_dir):
        project_root = Path.cwd()
        plan_path, _ = _seed_project(project_root)
        assert plan_path.exists()

        result = runner.invoke(main, ["show", "unknown:change"])

        assert result.exit_code != 0
        assert 'Unknown change "unknown:change"' in result.stderr


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_show_contract.py)
# =============================================================================


class TestShowHelp:
    """Test CC-SHOW help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Show command must support --help flag."""
        result = runner.invoke(main, ["show", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["show", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the show command."""
        result = runner.invoke(main, ["show", "--help"])
        assert "show" in result.output.lower()


class TestShowOptionalChangeName:
    """Test CC-SHOW-001: Optional change name."""

    def test_show_without_change_name_accepted(self, runner):
        """Show without change name must be accepted (shows all changes)."""
        result = runner.invoke(main, ["show"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented/no plan), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestShowWithChangeName:
    """Test CC-SHOW-002: With change name."""

    def test_show_with_change_name_accepted(self, runner):
        """Show with change name must be accepted."""
        result = runner.invoke(main, ["show", "my_change"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_show_with_tag_name(self, runner):
        """Show with tag name must be accepted."""
        result = runner.invoke(main, ["show", "@v1.0"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_show_with_target_option(self, runner):
        """Show with --target option must be accepted."""
        result = runner.invoke(main, ["show", "my_change", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestShowGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Show must accept --quiet global option."""
        result = runner.invoke(main, ["show", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Show must accept --verbose global option."""
        result = runner.invoke(main, ["show", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Show must accept --chdir global option."""
        result = runner.invoke(main, ["show", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Show must accept --no-pager global option."""
        result = runner.invoke(main, ["show", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestShowErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Show must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["show", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
