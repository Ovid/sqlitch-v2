"""Regression tests ensuring SQLitch matches Sqitch tutorial outputs."""

from __future__ import annotations

import gc
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from sqlitch.engine.sqlite import derive_sqlite_registry_uri, resolve_sqlite_filesystem_path
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change

__all__ = []

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "support" / "golden"
CLI_GOLDEN_ROOT = GOLDEN_ROOT / "cli"
CONFIG_GOLDEN_ROOT = GOLDEN_ROOT / "config"
PLANS_GOLDEN_ROOT = GOLDEN_ROOT / "plans"
REGISTRY_GOLDEN_ROOT = GOLDEN_ROOT / "registry" / "sqlite"

INIT_URI = "https://github.com/sqitchers/sqitch-sqlite-intro/"


def _normalize_deploy_output(output: str) -> str:
    """Normalize deploy output by collapsing workspace-specific paths."""

    # Replace absolute paths to the temporary registry database with deterministic placeholder.
    return re.sub(
        r"db:sqlite:[^\s]+/sqitch\.db",
        "db:sqlite:./sqitch.db",
        output.strip(),
    )


def test_init_output_matches_sqitch() -> None:
    """`sqlitch init` should emit Sqitch-identical scaffolding."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "init",
                "flipr",
                "--uri",
                INIT_URI,
                "--engine",
                "sqlite",
            ],
        )

        assert result.exit_code == 0, result.output

        expected_output = (CLI_GOLDEN_ROOT / "init_output.txt").read_text(encoding="utf-8")
        assert result.output == expected_output

        generated_plan = Path("sqitch.plan").read_text(encoding="utf-8")
        expected_plan = (PLANS_GOLDEN_ROOT / "init.plan").read_text(encoding="utf-8")
        assert generated_plan == expected_plan

        generated_config = Path("sqitch.conf").read_text(encoding="utf-8")
        expected_config = (CONFIG_GOLDEN_ROOT / "init_sqitch.conf").read_text(encoding="utf-8")
        assert generated_config == expected_config

        for directory in ("deploy", "revert", "verify"):
            assert Path(directory).is_dir(), f"Directory {directory} should be created"


def test_add_output_matches_sqitch() -> None:
    """`sqlitch add` should mirror Sqitch output and script headers."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        init_result = runner.invoke(
            main,
            [
                "init",
                "flipr",
                "--uri",
                INIT_URI,
                "--engine",
                "sqlite",
            ],
        )
        assert init_result.exit_code == 0, init_result.output

        result = runner.invoke(
            main,
            [
                "add",
                "users",
                "-n",
                "Creates table to track our users.",
            ],
        )

        assert result.exit_code == 0, result.output

        expected_output = (CLI_GOLDEN_ROOT / "add_users_output.txt").read_text(encoding="utf-8")
        assert result.output == expected_output

        deploy_header, *deploy_rest = Path("deploy/users.sql").read_text(encoding="utf-8").splitlines()
        revert_header, *revert_rest = Path("revert/users.sql").read_text(encoding="utf-8").splitlines()
        verify_header, *verify_rest = Path("verify/users.sql").read_text(encoding="utf-8").splitlines()

        assert deploy_header == "-- Deploy flipr:users to sqlite"
        assert revert_header == "-- Revert flipr:users from sqlite"
        assert verify_header == "-- Verify flipr:users on sqlite"


def test_deploy_output_matches_sqitch(tmp_path: Path) -> None:
    """`sqlitch deploy` should emit Sqitch-identical output and registry state."""

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        init_result = runner.invoke(
            main,
            [
                "init",
                "flipr",
                "--uri",
                INIT_URI,
                "--engine",
                "sqlite",
            ],
        )
        assert init_result.exit_code == 0, init_result.output

        add_result = runner.invoke(
            main,
            [
                "add",
                "users",
                "-n",
                "Creates table to track our users.",
            ],
        )
        assert add_result.exit_code == 0, add_result.output

        Path("deploy/users.sql").write_text(
            """-- Deploy flipr:users to sqlite

BEGIN;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE
);

COMMIT;
""",
            encoding="utf-8",
        )

        Path("revert/users.sql").write_text(
            """-- Revert flipr:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
""",
            encoding="utf-8",
        )

        Path("verify/users.sql").write_text(
            """-- Verify flipr:users on sqlite

SELECT user_id, username, email
  FROM users
 WHERE 0;
""",
            encoding="utf-8",
        )

        deploy_result = runner.invoke(
            main,
            [
                "deploy",
                "db:sqlite:flipr_test.db",
            ],
        )

        assert deploy_result.exit_code == 0, deploy_result.output

        normalized_output = _normalize_deploy_output(deploy_result.output)
        expected_output = (CLI_GOLDEN_ROOT / "deploy_users_output.txt").read_text(encoding="utf-8").strip()
        assert normalized_output == expected_output

        # Validate registry state mirrors expectations.
        conn = sqlite3.connect("sqitch.db")
        try:
            cursor = conn.execute(
                "SELECT change, project, note FROM changes ORDER BY committed_at DESC"
            )
            row = cursor.fetchone()
            cursor.close()
        finally:
            conn.close()

        assert row is not None
        change, project, note = row
        assert change == "users"
        assert project == "flipr"
        assert note == "Creates table to track our users."

        # Ensure any lingering SQLite connections are finalized to avoid resource warnings.
        gc.collect()


def test_status_output_matches_sqitch(tmp_path: Path) -> None:
    """`sqlitch status` should emit Sqitch-identical output after deploy."""

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Seed plan and config with deterministic tutorial metadata.
        planned_at = datetime(2013, 12, 31, 18, 26, 59, tzinfo=timezone.utc)
        change = Change.create(
            name="users",
            script_paths={
                "deploy": Path("deploy/20131231182659_users_deploy.sql"),
                "revert": Path("revert/20131231182659_users_revert.sql"),
            },
            planner="Marge N. O’Vera <marge@example.com>",
            planned_at=planned_at,
            notes="Creates table to track our users.",
        )

        write_plan(
            project_name="flipr",
            default_engine="sqlite",
            entries=[change],
            plan_path=Path("sqitch.plan"),
            uri=INIT_URI,
        )

        Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

        # Ensure script directories exist to mirror tutorial layout.
        Path("deploy").mkdir(parents=True, exist_ok=True)
        Path("revert").mkdir(parents=True, exist_ok=True)
        Path("deploy/20131231182659_users_deploy.sql").touch()
        Path("revert/20131231182659_users_revert.sql").touch()

        # Prepare registry database with Sqitch tutorial snapshot.
        workspace_db = Path("flipr_test.db")
        workspace_db.touch()
        workspace_uri = f"db:sqlite:{workspace_db.resolve().as_posix()}"
        registry_uri = derive_sqlite_registry_uri(
            workspace_uri=workspace_uri,
            project_root=Path.cwd(),
        )
        registry_path = resolve_sqlite_filesystem_path(registry_uri)
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(registry_path)
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
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "flipr",
                    INIT_URI,
                    "2013-12-31T00:00:00Z",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
            )

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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    "f30fe47f5f99501fb8d481e910d9112c5ac0a676",
                    "users",
                    "flipr",
                    "",
                    "2013-12-31 10:26:59 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                    "2013-12-31 10:26:59 -0800",
                    "Marge N. O’Vera",
                    "marge@example.com",
                ),
            )

            connection.commit()
        finally:
            connection.close()

        result = runner.invoke(main, ["status", "db:sqlite:flipr_test.db"])

        assert result.exit_code == 0, result.output

        expected_output = (REGISTRY_GOLDEN_ROOT / "status_after_users.txt").read_text(
            encoding="utf-8"
        )
        assert result.output == expected_output


def test_log_output_matches_sqitch(tmp_path: Path) -> None:
    """`sqlitch log` should emit Sqitch-identical history for recent events."""

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        planned_at = datetime(2013, 12, 31, 18, 26, 59, tzinfo=timezone.utc)
        change = Change.create(
            name="users",
            script_paths={
                "deploy": Path("deploy/20131231182659_users_deploy.sql"),
                "revert": Path("revert/20131231182659_users_revert.sql"),
            },
            planner="Marge N. O’Vera <marge@example.com>",
            planned_at=planned_at,
            notes="Creates table to track our users.",
        )

        write_plan(
            project_name="flipr",
            default_engine="sqlite",
            entries=[change],
            plan_path=Path("sqitch.plan"),
            uri=INIT_URI,
        )

        Path("sqitch.conf").write_text("[core]\n\tengine = sqlite\n", encoding="utf-8")

        Path("deploy").mkdir(parents=True, exist_ok=True)
        Path("revert").mkdir(parents=True, exist_ok=True)
        Path("deploy/20131231182659_users_deploy.sql").touch()
        Path("revert/20131231182659_users_revert.sql").touch()

        workspace_db = Path("flipr_test.db")
        workspace_db.touch()
        workspace_uri = f"db:sqlite:{workspace_db.resolve().as_posix()}"
        registry_uri = derive_sqlite_registry_uri(
            workspace_uri=workspace_uri,
            project_root=Path.cwd(),
        )
        registry_path = resolve_sqlite_filesystem_path(registry_uri)
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(registry_path)
        try:
            cursor = connection.cursor()
            cursor.executescript(
                """
                CREATE TABLE events (
                    event TEXT NOT NULL,
                    change_id TEXT NOT NULL,
                    change TEXT NOT NULL,
                    project TEXT NOT NULL,
                    note TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    committed_at TEXT NOT NULL,
                    committer_name TEXT NOT NULL,
                    committer_email TEXT NOT NULL
                );
                """
            )

            cursor.executemany(
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

            connection.commit()
        finally:
            connection.close()

        result = runner.invoke(main, ["log", "db:sqlite:flipr_test.db"])

        assert result.exit_code == 0, result.output

        expected_output = (REGISTRY_GOLDEN_ROOT / "log_users_revert.txt").read_text(
            encoding="utf-8"
        )
        assert result.output == expected_output
