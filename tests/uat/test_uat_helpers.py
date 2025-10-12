"""Lockdown tests for upcoming UAT helper modules.

These tests codify the public contracts that shared helper modules must satisfy
once implemented in the ``uat`` package. They intentionally reference modules
that do not yet exist so the implementation tasks (T115+) can drive them to
pass.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def test_sanitization_masks_change_ids_and_timestamps() -> None:
    """Sanitized output should redact change IDs and timestamp seconds."""

    from uat import sanitization

    raw = (
        "Processing change 1234567 for deployment\n"
        "Deployed change 1234567890abcdef1234567890abcdef12345678\n"
        "2025-01-01 12:34:56Z Some event\n"
        "# Deployed: 2025-01-01 12:34:56Z\n"
    )

    sanitized = sanitization.sanitize_output(raw)

    assert "1234567" not in sanitized
    assert "[REDACTED_CHANGE_ID]" in sanitized
    assert "12:34:SS" in sanitized
    # ``# Deployed`` lines should retain original content for parity diffs
    assert "# Deployed: 2025-01-01 12:34:56Z" in sanitized


def test_compare_user_databases_detects_differences(tmp_path: Path) -> None:
    """Comparison helper should flag data mismatches while ignoring registries."""

    from uat import comparison

    left = tmp_path / "sqitch.db"
    right = tmp_path / "sqlitch.db"

    for db_path in (left, right):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE users (nickname TEXT PRIMARY KEY, email TEXT)")
        cur.execute(
            "INSERT INTO users (nickname, email) VALUES (?, ?)",
            ("test-user", "user@example.com"),
        )
        conn.commit()
        conn.close()

    matched, message = comparison.compare_user_databases(left, right)
    assert matched is True
    assert message == ""

    # mutate the second database to trigger a diff
    conn = sqlite3.connect(right)
    cur = conn.cursor()
    cur.execute("DELETE FROM users")
    conn.commit()
    conn.close()

    matched, message = comparison.compare_user_databases(left, right)
    assert matched is False
    assert "users" in message


def test_tutorial_step_manifest_matches_side_by_side_expectations() -> None:
    """Tutorial steps must expose consistent metadata for every CLI invocation."""

    from uat.test_steps import TUTORIAL_STEPS, Step

    assert TUTORIAL_STEPS, "tutorial step manifest must not be empty"

    numbers = [step.number for step in TUTORIAL_STEPS]
    assert numbers == sorted(numbers), "tutorial steps must be ordered by their step number"
    assert len(numbers) == len(set(numbers)), "tutorial step numbers must be unique"

    first = TUTORIAL_STEPS[0]
    assert isinstance(first, Step)
    assert first.description == "Initialize Project"
    assert first.command == "sqlitch"
    assert first.args[:3] == (
        "init",
        "flipr",
        "--uri",
    )

    config_step = next(
        step for step in TUTORIAL_STEPS if step.description == "Configure User Email"
    )
    assert config_step.command == "sqlitch"
    assert "user.email" in config_step.args
