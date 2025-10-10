"""Lockdown tests targeting SQLite engine edge cases."""

from __future__ import annotations

import pytest

from sqlitch.engine.sqlite import SQLiteEngineError, validate_sqlite_script


def test_validate_sqlite_script_rejects_disabling_foreign_keys() -> None:
    """Foreign key enforcement must stay enabled during deployments."""
    script = """
    PRAGMA foreign_keys = OFF;
    CREATE TABLE users(id INTEGER PRIMARY KEY);
    """

    with pytest.raises(SQLiteEngineError, match="foreign_keys pragma must remain enabled"):
        validate_sqlite_script(script)


def test_validate_sqlite_script_rejects_unfinished_transaction() -> None:
    """Scripts that open transactions must close them explicitly."""
    script = """
    BEGIN;
    CREATE TABLE stuff(id INTEGER PRIMARY KEY);
    -- missing COMMIT/ROLLBACK on purpose
    """

    with pytest.raises(SQLiteEngineError, match="must end with COMMIT or ROLLBACK"):
        validate_sqlite_script(script)


def test_validate_sqlite_script_ignores_leading_comments() -> None:
    """Comments before statements should not break transaction balancing."""
    script = """
    -- Deploy flipr:users to sqlite

    BEGIN;
    CREATE TABLE users (id INTEGER PRIMARY KEY);
    COMMIT;
    """

    validate_sqlite_script(script)
