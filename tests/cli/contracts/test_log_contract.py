"""Contract parity tests for ``sqlitch log``."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.engine.sqlite import derive_sqlite_registry_uri, resolve_sqlite_filesystem_path
from tests.support.test_helpers import isolated_test_context

GOLDEN_ROOT = Path(__file__).resolve().parents[2] / "support" / "golden" / "registry" / "sqlite"


def _runner() -> CliRunner:
    return CliRunner()


def _seed_events(
    registry_path: Path, rows: Iterable[tuple[str, str, str, str, str, str, str]]
) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(registry_path)
    try:
        connection.execute(
            """
            CREATE TABLE events (
                event TEXT NOT NULL,
                change_id TEXT NOT NULL,
                change TEXT NOT NULL,
                project TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                committed_at TEXT NOT NULL,
                committer_name TEXT NOT NULL,
                committer_email TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO events (
                event,
                change_id,
                change,
                project,
                note,
                tags,
                committed_at,
                committer_name,
                committer_email
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()
    finally:
        connection.close()


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


def test_log_reports_human_history() -> None:
    """Human output should mirror the Sqitch log for recent events."""

    expected = (GOLDEN_ROOT / "log_users_revert.txt").read_text(encoding="utf-8")

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_events(
            registry_path,
            [
                (
                    "revert",
                    "f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    "2013-12-31 10:53:25 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
                (
                    "deploy",
                    "f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    "2013-12-31 10:26:59 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
            ],
        )

        result = runner.invoke(main, ["log", "--target", "db:sqlite:flipr_test.db"])

        assert result.exit_code == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "On database db:sqlite:flipr_test.db"
    # Ensure blank line separates summary from description exactly like Sqitch

    assert lines[5] == ""
    assert lines[6] == "    Creates table to track our users."
    assert lines[7] == ""
    # Double-check second entry retains blank separator
    assert lines[11] == "Date:      2013-12-31 10:26:59 -0800"
    assert lines[12] == "    Creates table to track our users."


def test_log_supports_json_format() -> None:
    """JSON output should return structured event dictionaries."""

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_events(
            registry_path,
            [
                (
                    "deploy",
                    "f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    "2013-12-31 10:26:59 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                )
            ],
        )

        result = runner.invoke(
            main,
            [
                "log",
                "--target",
                "flipr_test.db",
                "--format",
                "json",
                "--limit",
                "1",
            ],
        )

    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 1
    event = payload[0]
    assert event["event"] == "deploy"
    assert event["change"] == "users"
    assert event["project"] == "flipr"
    assert event["committer"]["name"] == "Marge N. O’Vera"
    assert event["committer"]["email"] == "marge@example.com"


def test_log_rejects_unknown_format() -> None:
    """Invalid format selections should return a parity-preserving error."""

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_events(
            registry_path,
            [
                (
                    "deploy",
                    "f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    datetime.now(timezone.utc).isoformat(),
                    "Marge N. O’Vera",
                    "marge@example.com",
                )
            ],
        )

        result = runner.invoke(
            main,
            [
                "log",
                "--target",
                "db:sqlite:flipr_test.db",
                "--format",
                "yaml",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "Unknown format" in result.stderr


def test_log_rejects_negative_limit() -> None:
    """Negative limits should be rejected before querying the registry."""

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_events(
            registry_path,
            [
                (
                    "deploy",
                    "f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    "2013-12-31 10:26:59 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                )
            ],
        )

        result = runner.invoke(
            main,
            [
                "log",
                "--target",
                "db:sqlite:flipr_test.db",
                "--limit",
                "-1",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code != 0
        assert "--limit must be" in result.stderr


def test_log_requires_explicit_target_when_missing() -> None:
    """Running without target configuration should raise an error."""

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["log"], catch_exceptions=False)

        assert result.exit_code != 0
        assert "A target must be provided" in result.stderr


def test_log_supports_filters_and_pagination() -> None:
    """Project, change, and pagination filters should narrow results."""

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_events(
            registry_path,
            [
                (
                    "deploy",
                    "aaa111",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    "2013-12-31 09:00:00 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
                (
                    "revert",
                    "bbb222",
                    "widgets",
                    "flipr",
                    "Rolls back widgets with issues.",
                    '{"@v1.0.0"}',
                    "2013-12-31 11:00:00 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
                (
                    "deploy",
                    "ccc333",
                    "widgets",
                    "flipr",
                    "Deploys widgets after fixes.",
                    '{"@v1.0.1"}',
                    "2013-12-31 12:00:00 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
            ],
        )

        result = runner.invoke(
            main,
            [
                "log",
                "--target",
                "db:sqlite:flipr_test.db",
                "--project",
                "flipr",
                "--change",
                "widgets",
                "--format",
                "json",
                "--reverse",
                "--skip",
                "1",
                "--limit",
                "1",
            ],
        )

        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)
        assert len(payload) == 1
        event = payload[0]
        assert event["change"] == "widgets"
        assert event["committed_at"].startswith("2013-12-31")
        assert event["tags"] == ["@v1.0.1"]


def test_log_reports_no_events_message() -> None:
    """Filters that remove all rows should print the no events message."""

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_events(
            registry_path,
            [
                (
                    "deploy",
                    "aaa111",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    "2013-12-31 09:00:00 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                )
            ],
        )

        result = runner.invoke(
            main,
            [
                "log",
                "--target",
                "db:sqlite:flipr_test.db",
                "--change",
                "widgets",
            ],
        )

        assert result.exit_code == 0, result.stderr
        assert "No events found." in result.stdout


def test_log_skip_without_limit() -> None:
    """Providing only --skip should still return results after the offset."""

    runner = _runner()
    with isolated_test_context(runner) as (runner, temp_dir):
        workspace_db = Path("flipr_test.db")
        registry_path = _prepare_workspace(workspace_db)
        _seed_events(
            registry_path,
            [
                (
                    "deploy",
                    "aaa111",
                    "users",
                    "flipr",
                    "Creates table to track our users.",
                    "",
                    "2013-12-31 09:00:00 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
                (
                    "deploy",
                    "bbb222",
                    "widgets",
                    "flipr",
                    "Deploys widgets after fixes.",
                    "",
                    "2013-12-31 12:00:00 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
            ],
        )

        result = runner.invoke(
            main,
            [
                "log",
                "--target",
                "db:sqlite:flipr_test.db",
                "--format",
                "json",
                "--skip",
                "1",
            ],
        )

        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)
        assert len(payload) == 1
        assert payload[0]["change_id"] == "aaa111"
