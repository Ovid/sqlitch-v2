from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.plan import model, parser


PLAN_TEXT = """%project=widgets
%default_engine=pg
change core:init deploy/core.sql revert/core.sql planner=alice@example.com planned_at=2025-10-03T12:30:00Z
change widgets:add deploy/widgets.sql revert/widgets.sql verify=verify/widgets.sql planner=alice@example.com planned_at=2025-10-03T12:34:56Z notes="Add widgets table." depends=core:init tags=v1.0
change widgets:index deploy/index.sql revert/index.sql planner=alice@example.com planned_at=2025-10-03T12:35:10Z depends=widgets:add
tag v1.0 widgets:add planner=alice@example.com tagged_at=2025-10-03T12:35:30Z
"""


def _write_plan(tmp_path: Path, content: str = PLAN_TEXT) -> Path:
    path = tmp_path / "plan"
    path.write_text(content, encoding="utf-8")
    return path


def test_parse_plan_with_changes_and_tags(tmp_path: Path) -> None:
    plan_path = _write_plan(tmp_path)

    plan = parser.parse_plan(plan_path)

    assert isinstance(plan, model.Plan)
    assert plan.project_name == "widgets"
    assert plan.default_engine == "pg"
    assert plan.file_path == plan_path
    assert plan.checksum

    core_change = plan.get_change("core:init")
    assert core_change.dependencies == ()

    change = plan.get_change("widgets:add")
    assert change.script_paths["deploy"].name == "widgets.sql"
    assert change.script_paths["verify"].name == "widgets.sql"
    assert change.dependencies == ("core:init",)
    assert change.tags == ("v1.0",)
    assert change.planner == "alice@example.com"
    assert change.planned_at.isoformat() == "2025-10-03T12:34:56+00:00"
    assert change.notes == "Add widgets table."

    index_change = plan.get_change("widgets:index")
    assert index_change.dependencies == ("widgets:add",)
    assert index_change.script_paths["verify"] is None

    tag = plan.tags[0]
    assert tag.name == "v1.0"
    assert tag.change_ref == "widgets:add"
    assert tag.planner == "alice@example.com"
    assert tag.tagged_at.isoformat() == "2025-10-03T12:35:30+00:00"


def test_parse_plan_requires_headers(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "change widgets:add deploy/widgets.sql revert/widgets.sql planner=alice@example.com planned_at=2025-10-03T12:34:56Z\n",
    )

    with pytest.raises(ValueError, match="project header"):
        parser.parse_plan(plan_path)


def test_parse_plan_requires_planner_metadata(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy/widgets.sql revert/widgets.sql planned_at=2025-10-03T12:34:56Z\n",
    )

    with pytest.raises(ValueError, match="planner metadata"):
        parser.parse_plan(plan_path)


def test_parse_plan_requires_planned_at_metadata(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy/widgets.sql revert/widgets.sql planner=alice@example.com\n",
    )

    with pytest.raises(parser.PlanParseError, match="requires planned_at metadata"):
        parser.parse_plan(plan_path)


def test_parse_plan_unknown_token(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nunknown entry\n",
    )

    with pytest.raises(ValueError, match="Unknown plan entry"):
        parser.parse_plan(plan_path)


def test_parse_plan_invalid_header_format(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine\n",
    )

    with pytest.raises(parser.PlanParseError, match="Invalid header"):
        parser.parse_plan(plan_path)


def test_parse_plan_rejects_incomplete_change(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy.sql\n",
    )

    with pytest.raises(parser.PlanParseError, match="incomplete"):
        parser.parse_plan(plan_path)


def test_parse_plan_rejects_invalid_metadata_token(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy.sql revert.sql badtoken planner=alice@example.com planned_at=2025-10-03T12:34:56Z\n",
    )

    with pytest.raises(parser.PlanParseError, match="Invalid metadata token"):
        parser.parse_plan(plan_path)


def test_parse_plan_rejects_tag_without_planner(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy.sql revert.sql planner=alice@example.com planned_at=2025-10-03T12:34:56Z\ntag v1.0 widgets:add tagged_at=2025-10-03T12:35:00Z\n",
    )

    with pytest.raises(parser.PlanParseError, match="requires planner metadata"):
        parser.parse_plan(plan_path)


def test_parse_plan_rejects_incomplete_tag(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\ntag onlytwo fields\n",
    )

    with pytest.raises(parser.PlanParseError, match="Tag entry"):  # incomplete tag
        parser.parse_plan(plan_path)


def test_parse_plan_rejects_invalid_timestamp(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy.sql revert.sql planner=alice@example.com planned_at=not-a-timestamp\n",
    )

    with pytest.raises(parser.PlanParseError, match="Invalid planned_at"):
        parser.parse_plan(plan_path)


def test_parse_plan_normalizes_naive_timestamp(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy.sql revert.sql planner=alice@example.com planned_at=2025-10-03T12:34:56\n",
    )

    plan = parser.parse_plan(plan_path)
    change = plan.get_change("widgets:add")
    assert change.planned_at.tzinfo is not None
    assert change.planned_at.isoformat() == "2025-10-03T12:34:56+00:00"


def test_parse_plan_rejects_invalid_uuid(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\nchange widgets:add deploy.sql revert.sql planner=alice@example.com planned_at=2025-10-03T12:34:56Z change_id=not-a-uuid\n",
    )

    with pytest.raises(parser.PlanParseError, match="Invalid change_id"):
        parser.parse_plan(plan_path)


def test_parse_plan_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    plan_path = _write_plan(
        tmp_path,
        "%project=widgets\n%default_engine=pg\n\n# this is a comment\nchange widgets:add deploy.sql revert.sql planner=alice@example.com planned_at=2025-10-03T12:34:56Z\n",
    )

    plan = parser.parse_plan(plan_path)
    assert plan.entries
    assert plan.get_change("widgets:add").planner == "alice@example.com"
