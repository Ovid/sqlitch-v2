"""Regression coverage for SQLite registry attachment behavior."""

from __future__ import annotations

import sqlite3

from contextlib import chdir, closing

from click.testing import CliRunner

from sqlitch.cli.main import main

from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project


def test_registry_isolated_from_workspace(tmp_path) -> None:
    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="alpha",
                deploy_sql="""
                CREATE TABLE workspace_data (id INTEGER PRIMARY KEY);
                INSERT INTO workspace_data DEFAULT VALUES;
                """,
            )
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

    assert result.exit_code == 0, result.output

    assert (
        project.registry_path.exists()
    ), "SQLite deployment should create a dedicated sqitch.db registry database"

    with closing(sqlite3.connect(workspace_db)) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?)",
            ("changes", "releases"),
        )
        workspace_tables = {row[0] for row in cursor.fetchall()}

    assert (
        not workspace_tables
    ), "Workspace database must remain free of registry tables when deploy completes"

    with closing(sqlite3.connect(project.registry_path)) as registry_conn:
        cursor = registry_conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("changes",),
        )
        registry_tables = {row[0] for row in cursor.fetchall()}

    assert registry_tables == {"changes"}, "Registry database should contain the Sqitch schema"
