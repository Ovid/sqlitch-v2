"""Regression coverage for SQLite deploy atomicity guarantees."""

from __future__ import annotations

import sqlite3
from contextlib import chdir, closing

from click.testing import CliRunner

from sqlitch.cli.main import main

from tests.support.sqlite_fixtures import ChangeScript, create_sqlite_project


def test_failed_deploy_does_not_persist_workspace_mutations(tmp_path) -> None:
    project = create_sqlite_project(
        tmp_path,
        changes=[
            ChangeScript(
                name="alpha",
                deploy_sql="""
                CREATE TABLE alpha_data (id INTEGER PRIMARY KEY);
                INSERT INTO alpha_data DEFAULT VALUES;
                SELECT RAISE(ABORT, 'deploy failure');
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

    assert result.exit_code != 0, "Deploy should fail when the deploy script raises"

    assert workspace_db.exists(), "Workspace database should still be created for inspection"

    with closing(sqlite3.connect(workspace_db)) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("alpha_data",),
        )
        tables = {row[0] for row in cursor.fetchall()}

    assert not tables, "Failed deploy must not leave change tables behind in the workspace database"
