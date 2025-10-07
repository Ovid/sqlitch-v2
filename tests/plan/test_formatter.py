from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from sqlitch.plan import formatter, parser
from sqlitch.plan.model import Change, Tag


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def test_format_plan_generates_expected_text(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan"
    change_core = Change(
        name="core:init",
        script_paths={"deploy": "deploy/core.sql", "revert": "revert/core.sql"},
        planner="alice@example.com",
        planned_at=_dt("2025-10-03T12:30:00+00:00"),
        change_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    )
    change_widgets = Change(
        name="widgets:add",
        script_paths={
            "deploy": "deploy/widgets.sql",
            "revert": "revert/widgets.sql",
            "verify": "verify/widgets.sql",
        },
        planner="alice@example.com",
        planned_at=_dt("2025-10-03T12:34:56+00:00"),
        notes="Add widgets table.",
        dependencies=("core:init",),
        tags=("v1.0",),
        change_id=UUID("223e4567-e89b-12d3-a456-426614174000"),
    )
    tag_v1 = Tag(
        name="v1.0",
        change_ref="widgets:add",
        planner="alice@example.com",
        tagged_at=_dt("2025-10-03T12:35:30+00:00"),
    )

    plan_text = formatter.format_plan(
        project_name="widgets",
        default_engine="pg",
        entries=[change_core, change_widgets, tag_v1],
        base_path=plan_path.parent,
    )

    # Compact Sqitch format: <name> [<dependencies>] <timestamp> <planner> # <note>
    # Note: default_engine is NOT written to plan (Sqitch stores it in config/target URIs)
    expected = "%syntax-version=1.0.0\n%project=widgets\n\ncore:init 2025-10-03T12:30:00Z alice@example.com\nwidgets:add [core:init] 2025-10-03T12:34:56Z alice@example.com # Add widgets table.\n@v1.0 2025-10-03T12:35:30Z alice@example.com\n"

    assert plan_text == expected


def test_write_plan_persists_content_and_returns_plan(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan"
    change = Change(
        name="core:init",
        script_paths={"deploy": "deploy/core.sql", "revert": "revert/core.sql"},
        planner="alice@example.com",
        planned_at=_dt("2025-10-03T12:30:00+00:00"),
        change_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    )
    tag = Tag(
        name="init",
        change_ref="core:init",
        planner="alice@example.com",
        tagged_at=_dt("2025-10-03T12:45:00+00:00"),
    )

    plan = formatter.write_plan(
        project_name="widgets",
        default_engine="pg",
        entries=[change, tag],
        plan_path=plan_path,
    )

    content = plan_path.read_text(encoding="utf-8")
    expected_content = formatter.format_plan(
        project_name="widgets",
        default_engine="pg",
        entries=[change, tag],
        base_path=plan_path.parent,
    )

    assert content == expected_content
    assert plan.checksum == formatter.compute_checksum(expected_content)
    assert plan.project_name == "widgets"
    assert plan.default_engine == "pg"
    assert plan.file_path == plan_path
    assert plan.entries == (change, tag)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        ("hello", "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
    ],
)
def test_compute_checksum_matches_sha256(value: str, expected: str) -> None:
    assert formatter.compute_checksum(value) == expected


def test_format_plan_preserves_missing_change_id(tmp_path: Path) -> None:
    # Compact format does not include change_id, script_paths, or tags metadata
    # Only: <name> [<dependencies>] <timestamp> <planner> # <note>
    # Note: default_engine NOT in plan (Sqitch stores in config)
    original = "%syntax-version=1.0.0\n%project=widgets\n\ncore:init 2025-10-03T12:30:00Z alice@example.com\n"
    plan_path = tmp_path / "plan"
    plan_path.write_text(original, encoding="utf-8")

    # Parser needs default_engine parameter since it's not in the file
    plan = parser.parse_plan(plan_path, default_engine="pg")
    rendered = formatter.format_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=plan.entries,
        base_path=plan_path.parent,
    )

    assert rendered == original
