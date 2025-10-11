"""Tests for symbolic reference support in revert command (Sqitch parity)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from click.testing import CliRunner

from sqlitch.cli.main import main


def test_revert_to_head_caret(tmp_path: Path, monkeypatch):
    """Test reverting to @HEAD^ symbolic reference."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Initialize project
    result = runner.invoke(main, ["init", "test", "--uri", "https://test.example.com", "--engine", "sqlite"])
    assert result.exit_code == 0

    # Configure user
    runner.invoke(main, ["config", "user.name", "Test User"])
    runner.invoke(main, ["config", "user.email", "test@example.com"])

    # Add three changes
    result = runner.invoke(main, ["add", "change1", "-n", "First change"])
    assert result.exit_code == 0
    result = runner.invoke(main, ["add", "change2", "-n", "Second change"])
    assert result.exit_code == 0
    result = runner.invoke(main, ["add", "change3", "-n", "Third change"])
    assert result.exit_code == 0

    # Write deploy/revert/verify scripts
    for change in ["change1", "change2", "change3"]:
        (tmp_path / "deploy" / f"{change}.sql").write_text(
            f"CREATE TABLE {change} (id INTEGER PRIMARY KEY);"
        )
        (tmp_path / "revert" / f"{change}.sql").write_text(f"DROP TABLE {change};")
        (tmp_path / "verify" / f"{change}.sql").write_text(f"SELECT * FROM {change} WHERE 1=0;")

    # Deploy all changes
    db_path = tmp_path / "test.db"
    result = runner.invoke(main, ["deploy", f"db:sqlite:{db_path}"])
    assert result.exit_code == 0, f"Deploy failed: {result.output}"

    # Verify all three tables exist
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'change%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    assert tables == ["change1", "change2", "change3"]

    # Revert to @HEAD^ (should revert change3 only, keeping change1 and change2)
    result = runner.invoke(main, ["revert", f"db:sqlite:{db_path}", "--to", "@HEAD^", "-y"])
    assert result.exit_code == 0, f"Revert failed: {result.output}"

    # Verify only change1 and change2 remain
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'change%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    assert tables == ["change1", "change2"], f"Expected [change1, change2], got {tables}"


def test_revert_to_root_symbolic_reference(tmp_path: Path, monkeypatch):
    """Test reverting to @ROOT symbolic reference."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Initialize project
    result = runner.invoke(main, ["init", "test", "--uri", "https://test.example.com", "--engine", "sqlite"])
    assert result.exit_code == 0

    # Configure user
    runner.invoke(main, ["config", "user.name", "Test User"])
    runner.invoke(main, ["config", "user.email", "test@example.com"])

    # Add two changes
    result = runner.invoke(main, ["add", "first", "-n", "First change"])
    assert result.exit_code == 0
    result = runner.invoke(main, ["add", "second", "-n", "Second change"])
    assert result.exit_code == 0

    # Write scripts
    (tmp_path / "deploy" / "first.sql").write_text("CREATE TABLE first (id INTEGER);")
    (tmp_path / "revert" / "first.sql").write_text("DROP TABLE first;")
    (tmp_path / "verify" / "first.sql").write_text("SELECT * FROM first WHERE 1=0;")
    
    (tmp_path / "deploy" / "second.sql").write_text("CREATE TABLE second (id INTEGER);")
    (tmp_path / "revert" / "second.sql").write_text("DROP TABLE second;")
    (tmp_path / "verify" / "second.sql").write_text("SELECT * FROM second WHERE 1=0;")

    # Deploy both
    db_path = tmp_path / "test.db"
    result = runner.invoke(main, ["deploy", f"db:sqlite:{db_path}"])
    assert result.exit_code == 0

    # Revert to @ROOT (should keep only the first change)
    result = runner.invoke(main, ["revert", f"db:sqlite:{db_path}", "--to", "@ROOT", "-y"])
    assert result.exit_code == 0

    # Verify only 'first' remains
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('first', 'second')")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    assert tables == ["first"]


def test_revert_to_change_with_caret(tmp_path: Path, monkeypatch):
    """Test reverting to named change with caret offset."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Initialize project
    result = runner.invoke(main, ["init", "test", "--uri", "https://test.example.com", "--engine", "sqlite"])
    assert result.exit_code == 0

    # Configure user
    runner.invoke(main, ["config", "user.name", "Test User"])
    runner.invoke(main, ["config", "user.email", "test@example.com"])

    # Add four changes
    for i in range(1, 5):
        result = runner.invoke(main, ["add", f"change{i}", "-n", f"Change {i}"])
        assert result.exit_code == 0
        (tmp_path / "deploy" / f"change{i}.sql").write_text(f"CREATE TABLE change{i} (id INTEGER);")
        (tmp_path / "revert" / f"change{i}.sql").write_text(f"DROP TABLE change{i};")
        (tmp_path / "verify" / f"change{i}.sql").write_text(f"SELECT * FROM change{i} WHERE 1=0;")

    # Deploy all
    db_path = tmp_path / "test.db"
    result = runner.invoke(main, ["deploy", f"db:sqlite:{db_path}"])
    assert result.exit_code == 0

    # Revert to change4^ (should keep change1, change2, change3)
    result = runner.invoke(main, ["revert", f"db:sqlite:{db_path}", "--to", "change4^", "-y"])
    assert result.exit_code == 0

    # Verify change1, change2, change3 remain
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'change%' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    assert tables == ["change1", "change2", "change3"]
