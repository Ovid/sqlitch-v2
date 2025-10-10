"""SQLite database comparison helpers for UAT harnesses."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

__all__ = ["compare_user_databases"]

_USER_TABLE_EXCLUSIONS = ("sqlite_", "sqitch_")


def compare_user_databases(left: Path, right: Path) -> tuple[bool, str]:
    """Compare user-visible tables between two SQLite databases.

    Parameters
    ----------
    left, right:
        Paths to the SQLite database files to compare. Missing files are
        treated as empty databases and considered matching.

    Returns
    -------
    tuple[bool, str]
        ``(True, "")`` if the user tables match, otherwise ``(False, message)``
        where ``message`` describes the divergence.
    """

    if not left.exists() or not right.exists():
        return True, ""

    conn_left = sqlite3.connect(str(left))
    conn_right = sqlite3.connect(str(right))

    try:
        tables_left = _user_tables(conn_left)
        tables_right = _user_tables(conn_right)

        if tables_left != tables_right:
            return (
                False,
                "User table sets differ:\n"
                f"  left: {sorted(tables_left)}\n"
                f"  right: {sorted(tables_right)}",
            )

        for table in sorted(tables_left):
            rows_left = _table_rows(conn_left, table)
            rows_right = _table_rows(conn_right, table)
            if rows_left != rows_right:
                return False, f"Data differs in table '{table}'"

        return True, ""
    finally:
        conn_left.close()
        conn_right.close()


def _user_tables(connection: sqlite3.Connection) -> set[str]:
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {row[0] for row in cursor.fetchall()}
        return {
            name
            for name in names
            if not any(name.startswith(prefix) for prefix in _USER_TABLE_EXCLUSIONS)
        }
    finally:
        cursor.close()


def _table_rows(connection: sqlite3.Connection, table: str) -> Iterable[tuple]:
    cursor = connection.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table}")
        return cursor.fetchall()
    finally:
        cursor.close()
