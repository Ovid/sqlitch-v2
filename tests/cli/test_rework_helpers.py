"""Unit coverage for helper utilities in ``sqlitch.cli.commands.rework``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands import rework as rework_module
from sqlitch.plan.model import Change


def _make_change(name: str) -> Change:
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return Change.create(
        name=name,
        script_paths={
            "deploy": Path("deploy") / f"{name}.sql",
            "revert": Path("revert") / f"{name}.sql",
            "verify": Path("verify") / f"{name}.sql",
        },
        planner="Planner",
        planned_at=timestamp,
    )


def test_resolve_new_path_with_override(tmp_path: Path) -> None:
    override = tmp_path / "custom.sql"

    result = rework_module._resolve_new_path(
        project_root=tmp_path,
        original=None,
        override=str(override),
        slug="widgets",
        suffix="@v1.0",
    )

    assert result == override


def test_resolve_new_path_generates_when_original_present(tmp_path: Path) -> None:
    original = tmp_path / "deploy" / "widgets.sql"
    generated = rework_module._resolve_new_path(
        project_root=tmp_path,
        original=original,
        override=None,
        slug="widgets",
        suffix="@v1.0",
    )

    assert generated == original.parent / "widgets@v1.0.sql"


def test_copy_script_missing_source_errors(tmp_path: Path) -> None:
    target = tmp_path / "deploy" / "rework.sql"

    with pytest.raises(CommandError, match="missing a script"):
        rework_module._copy_script(None, target)


def test_copy_script_missing_file_errors(tmp_path: Path) -> None:
    source = tmp_path / "missing.sql"
    target = tmp_path / "deploy" / "rework.sql"

    with pytest.raises(CommandError, match="Source script"):
        rework_module._copy_script(source, target)


def test_copy_script_creates_target(tmp_path: Path) -> None:
    source = tmp_path / "source.sql"
    source.write_text("data", encoding="utf-8")
    target = tmp_path / "deploy" / "rework.sql"

    rework_module._copy_script(source, target)

    assert target.read_text(encoding="utf-8") == "data"


def test_append_rework_change_adds_at_end(tmp_path: Path) -> None:
    """Test that rework appends change instead of replacing (Sqitch behavior)."""
    original = _make_change("widgets")
    other = _make_change("gadgets")
    entries = (original, other)
    rework = _make_change("widgets")

    updated = rework_module._append_rework_change(
        entries=entries, name="widgets", rework=rework
    )

    # Should have original, other, and rework (3 entries total)
    assert len(updated) == 3
    assert updated[0] == original
    assert updated[1] == other
    assert updated[2] == rework


def test_append_rework_change_missing_raises(tmp_path: Path) -> None:
    """Test that reworking non-existent change raises error."""
    entries = (_make_change("widgets"),)
    rework = _make_change("reports")

    with pytest.raises(CommandError, match='Unknown change "reports"'):
        rework_module._append_rework_change(entries=entries, name="reports", rework=rework)
