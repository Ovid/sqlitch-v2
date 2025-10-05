"""Regression coverage for deploy scripts that manage their own SQLite transactions."""

from __future__ import annotations

import sqlite3
from contextlib import chdir, closing

from click.testing import CliRunner

from sqlitch.cli.main import main

from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project


def test_deploy_respects_script_managed_transactions(tmp_path) -> None:
    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="script_transactions_commit",
                deploy_sql="""
                BEGIN;
                CREATE TABLE committed_data (id INTEGER PRIMARY KEY, value TEXT);
                INSERT INTO committed_data (value) VALUES ('ok');
                COMMIT;
                """,
            ),
            ChangeScript(
                name="script_transactions_rollback",
                deploy_sql="""
                BEGIN;
                CREATE TABLE rollback_data (id INTEGER PRIMARY KEY, value TEXT);
                INSERT INTO rollback_data (value) VALUES ('should rollback');
                ROLLBACK;
                SELECT * FROM nonexistent_table;
                """,
            ),
        ],
    )

    workspace_db = project.project_root / "workspace.db"

    runner = CliRunner()
    with chdir(project.project_root):
        result = runner.invoke(
            main,
            [
                "deploy",
                "--target",
                workspace_db.as_posix(),
            ],
            catch_exceptions=False,
        )

    assert result.exit_code != 0, "Deploy should fail after the script-triggered rollback"
    assert "no such table: nonexistent_table" in result.output

    assert workspace_db.exists(), "Workspace database should exist for inspection"

    with closing(sqlite3.connect(workspace_db)) as connection:
        committed_cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("committed_data",),
        )
        committed_tables = {row[0] for row in committed_cursor.fetchall()}
        committed_cursor.close()

        row_cursor = connection.execute("SELECT COUNT(*) FROM committed_data")
        committed_rows = row_cursor.fetchone()[0]
        row_cursor.close()

        rollback_cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("rollback_data",),
        )
        rollback_tables = {row[0] for row in rollback_cursor.fetchall()}
        rollback_cursor.close()

    assert committed_tables == {"committed_data"}, "Manual transaction change should commit data"
    assert committed_rows == 1, "Committed change should persist inserted rows"
    assert not rollback_tables, "Rolled-back change must not leave tables behind"

    assert (
        project.registry_path.exists()
    ), "Registry database should be created even when a later change fails"

    with closing(sqlite3.connect(project.registry_path)) as connection:
        cursor = connection.execute(
            "SELECT change FROM changes ORDER BY committed_at ASC",
        )
        recorded_changes = [row[0] for row in cursor.fetchall()]
        cursor.close()

    assert recorded_changes == [
        "script_transactions_commit"
    ], "Registry must only record successfully committed changes"
