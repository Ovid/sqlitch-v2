"""Contract parity tests for ``sqlitch status``.

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.engine.sqlite import derive_sqlite_registry_uri, resolve_sqlite_filesystem_path
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change, PlanEntry, Tag
from tests.support.test_helpers import isolated_test_context

GOLDEN_REGISTRY_ROOT = (
    Path(__file__).resolve().parents[2] / "support" / "golden" / "registry" / "sqlite"
)

PLANNER = "Marge N. O’Vera"
PLANNER_EMAIL = "marge@example.com"
PROJECT = "flipr"


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for SQLitch parity tests."""

    return CliRunner()


@dataclass(frozen=True)
class RegistryFixtureRow:
    """Represents a registry entry used to seed sqlite fixtures."""

    change_id: str
    change_name: str
    deployed_at: str
    deployer_name: str
    deployer_email: str
    tag: str | None = None


def _read_golden(name: str) -> str:
    path = GOLDEN_REGISTRY_ROOT / name
    return path.read_text(encoding="utf-8")


def _write_plan(plan_path: Path, entries: Sequence[PlanEntry]) -> None:
    write_plan(
        project_name=PROJECT,
        default_engine="sqlite",
        entries=entries,
        plan_path=plan_path,
    )

    # Create minimal config so commands can find engine (Sqitch stores engine in config, not plan)
    config_path = plan_path.parent / "sqitch.conf"
    config_path.write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")


def _prepare_workspace(workspace_db: Path) -> Path:
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch(exist_ok=True)
    workspace_uri = f"db:sqlite:{workspace_db.resolve().as_posix()}"
    registry_uri = derive_sqlite_registry_uri(
        workspace_uri=workspace_uri,
        project_root=Path.cwd(),
    )
    registry_path = resolve_sqlite_filesystem_path(registry_uri)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    return registry_path


def _change(
    name: str,
    *,
    planned_at: datetime,
    notes: str,
    dependencies: Sequence[str] = (),
    tags: Sequence[str] = (),
) -> Change:
    safe_name = name.replace(":", "_")
    timestamp = planned_at.strftime("%Y%m%d%H%M%S")
    script_base = f"{timestamp}_{safe_name}"
    return Change.create(
        name=name,
        script_paths={
            "deploy": Path("deploy") / f"{script_base}_deploy.sql",
            "revert": Path("revert") / f"{script_base}_revert.sql",
        },
        planner=PLANNER,
        planned_at=planned_at,
        notes=notes,
        dependencies=tuple(dependencies),
        tags=tuple(tags),
    )


def _tag(name: str, *, change_ref: str, tagged_at: datetime) -> Tag:
    return Tag(
        name=name,
        change_ref=change_ref,
        planner=PLANNER,
        tagged_at=tagged_at,
    )


def _seed_registry(db_path: Path, rows: Iterable[RegistryFixtureRow]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE projects (
                project         TEXT PRIMARY KEY,
                uri             TEXT,
                created_at      TEXT NOT NULL,
                creator_name    TEXT NOT NULL,
                creator_email   TEXT NOT NULL
            );

            CREATE TABLE changes (
                change_id       TEXT PRIMARY KEY,
                script_hash     TEXT,
                "change"        TEXT NOT NULL,
                project         TEXT NOT NULL,
                note            TEXT NOT NULL,
                committed_at    TEXT NOT NULL,
                committer_name  TEXT NOT NULL,
                committer_email TEXT NOT NULL,
                planned_at      TEXT NOT NULL,
                planner_name    TEXT NOT NULL,
                planner_email   TEXT NOT NULL
            );

            CREATE TABLE tags (
                tag_id          TEXT PRIMARY KEY,
                tag             TEXT NOT NULL,
                project         TEXT NOT NULL,
                change_id       TEXT NOT NULL,
                note            TEXT NOT NULL,
                committed_at    TEXT NOT NULL,
                committer_name  TEXT NOT NULL,
                committer_email TEXT NOT NULL,
                planned_at      TEXT NOT NULL,
                planner_name    TEXT NOT NULL,
                planner_email   TEXT NOT NULL
            );
            """
        )

        cursor.execute(
            """
            INSERT INTO projects (project, uri, created_at, creator_name, creator_email)
            VALUES (?, NULL, ?, ?, ?)
            """,
            (PROJECT, "2013-12-31 00:00:00Z", PLANNER, PLANNER_EMAIL),
        )

        tag_index = 0
        for row in rows:
            cursor.execute(
                """
                INSERT INTO changes (
                    change_id,
                    script_hash,
                    "change",
                    project,
                    note,
                    committed_at,
                    committer_name,
                    committer_email,
                    planned_at,
                    planner_name,
                    planner_email
                ) VALUES (?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.change_id,
                    row.change_id,
                    row.change_name,
                    PROJECT,
                    row.deployed_at,
                    row.deployer_name,
                    row.deployer_email,
                    row.deployed_at,
                    PLANNER,
                    PLANNER_EMAIL,
                ),
            )

            if row.tag is not None:
                tag_index += 1
                cursor.execute(
                    """
                    INSERT INTO tags (
                        tag_id,
                        tag,
                        project,
                        change_id,
                        note,
                        committed_at,
                        committer_name,
                        committer_email,
                        planned_at,
                        planner_name,
                        planner_email
                    ) VALUES (?, ?, ?, ?, '', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"tag-{tag_index}",
                        row.tag,
                        PROJECT,
                        row.change_id,
                        row.deployed_at,
                        row.deployer_name,
                        row.deployer_email,
                        row.deployed_at,
                        PLANNER,
                        PLANNER_EMAIL,
                    ),
                )

        connection.commit()
    finally:
        connection.close()


def test_status_outputs_in_sync_snapshot(runner: CliRunner) -> None:
    """Human output should match Sqitch when the database is fully deployed."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        change_time = datetime(2013, 12, 31, 18, 26, 59, tzinfo=timezone.utc)
        users_change = _change(
            "users",
            planned_at=change_time,
            notes="Creates table to track our users.",
        )
        _write_plan(plan_path, (users_change,))

        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_registry(
            registry_path,
            [
                RegistryFixtureRow(
                    change_id="f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    change_name="users",
                    deployed_at="2013-12-31 10:26:59 -0800",
                    deployer_name=PLANNER,
                    deployer_email=PLANNER_EMAIL,
                )
            ],
        )

        result = runner.invoke(main, ["status", "--target", "db:sqlite:flipr_test.db"])

        assert result.exit_code == 0, result.output
        lines = result.stdout.splitlines()
        assert lines[0] == "# On database db:sqlite:flipr_test.db"
        assert lines[-1] == "Nothing to deploy (up-to-date)"


def test_status_reports_undeployed_changes(runner: CliRunner) -> None:
    """When the database lags the plan, status should report pending deploys."""

    expected = _read_golden("status_after_revert_flips.txt")

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        users_time = datetime(2013, 12, 31, 18, 57, 55, tzinfo=timezone.utc)
        flips_time = datetime(2013, 12, 31, 19, 5, 44, tzinfo=timezone.utc)

        users_change = _change(
            "users",
            planned_at=users_time,
            notes="Creates table to track our users.",
        )
        flips_change = _change(
            "flips",
            planned_at=flips_time,
            notes="Adds table for storing flips.",
            dependencies=("users",),
        )
        _write_plan(plan_path, (users_change, flips_change))

        workspace_db = Path("flipr_test")
        registry_path = _prepare_workspace(workspace_db)
        _seed_registry(
            registry_path,
            [
                RegistryFixtureRow(
                    change_id="f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    change_name="users",
                    deployed_at="2013-12-31 10:57:55 -0800",
                    deployer_name=PLANNER,
                    deployer_email=PLANNER_EMAIL,
                )
            ],
        )

        result = runner.invoke(
            main,
            ["status", "--target", "flipr_test", "--project", PROJECT],
        )

        assert result.exit_code == 0, result.output
        assert result.stdout == expected
        lines = result.stdout.splitlines()
        assert lines[0] == "# On database flipr_test"
        assert lines[-2:] == ["Undeployed change:", "  * flips"]


def test_status_json_format_matches_fixture(runner: CliRunner) -> None:
    """The JSON format should serialize structured status information."""

    golden_text = _read_golden("status_dev_tagged.txt")

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqlitch.plan")
        users_time = datetime(2013, 12, 31, 18, 26, 59, tzinfo=timezone.utc)
        flips_time = datetime(2013, 12, 31, 19, 5, 44, tzinfo=timezone.utc)
        userflips_time = datetime(2013, 12, 31, 19, 19, 15, tzinfo=timezone.utc)

        users_change = _change(
            "users",
            planned_at=users_time,
            notes="Creates table to track our users.",
        )
        flips_change = _change(
            "flips",
            planned_at=flips_time,
            notes="Adds table for storing flips.",
            dependencies=("users",),
        )
        userflips_change = _change(
            "userflips",
            planned_at=userflips_time,
            notes="Creates the userflips view.",
            dependencies=("users", "flips"),
            tags=("@v1.0.0-dev1",),
        )
        tag_entry = _tag("@v1.0.0-dev1", change_ref="userflips", tagged_at=userflips_time)
        _write_plan(plan_path, (users_change, flips_change, userflips_change, tag_entry))

        workspace_db = Path("dev/flipr_dev.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_registry(
            registry_path,
            [
                RegistryFixtureRow(
                    change_id="f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    change_name="users",
                    deployed_at="2013-12-31 10:26:59 -0800",
                    deployer_name=PLANNER,
                    deployer_email=PLANNER_EMAIL,
                ),
                RegistryFixtureRow(
                    change_id="4195ecddf3ce6a09bca7bc1800891e06ebe32273",
                    change_name="flips",
                    deployed_at="2013-12-31 11:05:53 -0800",
                    deployer_name=PLANNER,
                    deployer_email=PLANNER_EMAIL,
                ),
                RegistryFixtureRow(
                    change_id="60ee3aba0445bf3287f9dc1dd97b1877523fa139",
                    change_name="userflips",
                    deployed_at="2013-12-31 11:19:15 -0800",
                    deployer_name=PLANNER,
                    deployer_email=PLANNER_EMAIL,
                    tag="@v1.0.0-dev1",
                ),
            ],
        )

        result = runner.invoke(
            main,
            [
                "status",
                "--target",
                "db:sqlite:dev/flipr_dev.db",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["project"] == PROJECT
        assert payload["target"] == "db:sqlite:dev/flipr_dev.db"
        assert payload["status"] == "in_sync"
        assert "change" in payload
        assert payload["change"]["name"] == "userflips"
        assert payload["change"]["deploy_id"] == "60ee3aba0445bf3287f9dc1dd97b1877523fa139"
        assert payload["change"]["tag"] == "@v1.0.0-dev1"
        assert payload["pending_changes"] == []
        assert golden_text.splitlines()[1].split()[2] == payload["project"]


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_status_contract.py)
# =============================================================================


class TestStatusHelp:
    """Test CC-STATUS help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Status command must support --help flag."""
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["status", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the status command."""
        result = runner.invoke(main, ["status", "--help"])
        assert "status" in result.output.lower()


class TestStatusOptionalTarget:
    """Test CC-STATUS-001: Optional target."""

    def test_status_without_target_accepted(self, runner):
        """Status without target must be accepted (uses default)."""
        result = runner.invoke(main, ["status"])
        # Should accept (not a parsing error)
        # May exit 0 (success), 1 (not implemented/no target), or fail validation
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestStatusPositionalTarget:
    """Test CC-STATUS-002: Positional target."""

    def test_status_with_positional_target(self, runner):
        """Status with positional target must be accepted."""
        result = runner.invoke(main, ["status", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_status_with_target_option(self, runner):
        """Status with --target option must be accepted."""
        result = runner.invoke(main, ["status", "--target", "db:sqlite:test.db"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_status_with_show_tags_option(self, runner):
        """Status with --show-tags option must be accepted."""
        result = runner.invoke(main, ["status", "--show-tags"])
        # Should accept (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestStatusGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Status must accept --quiet global option."""
        result = runner.invoke(main, ["status", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Status must accept --verbose global option."""
        result = runner.invoke(main, ["status", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Status must accept --chdir global option."""
        result = runner.invoke(main, ["status", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Status must accept --no-pager global option."""
        result = runner.invoke(main, ["status", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestStatusErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Status must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["status", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
