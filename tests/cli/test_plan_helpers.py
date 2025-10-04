"""Unit coverage for helper functions in ``sqlitch.cli.commands.plan``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import click
import pytest

from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands import plan as plan_module
from sqlitch.plan.model import Change, Plan, Tag
from sqlitch.plan.parser import PlanParseError


def _make_change(name: str, *, notes: str | None = None) -> Change:
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return Change.create(
        name=name,
        script_paths={"deploy": Path("deploy.sql"), "revert": Path("revert.sql")},
        planner="Planner",
        planned_at=timestamp,
        notes=notes,
    )


def _make_plan(entries: tuple[Change | Tag, ...], *, missing: tuple[str, ...] = ()) -> Plan:
    plan = Plan(
        project_name="widgets",
        file_path=Path("sqlitch.plan"),
        entries=entries,
        checksum="checksum",
        default_engine="sqlite",
    )
    if missing:
        object.__setattr__(plan, "missing_dependencies", missing)
    return plan


def test_read_plan_text_missing_file(tmp_path: Path) -> None:
    target = tmp_path / "missing.plan"

    with pytest.raises(CommandError, match="missing"):
        plan_module._read_plan_text(target)


def test_parse_plan_model_wraps_parser_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plan_path = tmp_path / "sqlitch.plan"
    plan_path.write_text("%project=widgets\n", encoding="utf-8")

    def fake_parse(_: Path, **__: object) -> None:
        raise PlanParseError("boom")

    monkeypatch.setattr(plan_module, "parse_plan", fake_parse)

    with pytest.raises(CommandError, match="boom"):
        plan_module._parse_plan_model(plan_path, None)


def test_filter_entries_no_filters_returns_all(tmp_path: Path) -> None:
    first = _make_change("one")
    second = _make_change("two")
    tag = Tag(
        name="v1.0",
        change_ref=second.name,
        planner="Planner",
        tagged_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    plan = _make_plan((first, second, tag))

    result = plan_module._filter_entries(plan, (), ())

    assert result == (first, second, tag)


def test_filter_entries_missing_change_errors(tmp_path: Path) -> None:
    plan = _make_plan((_make_change("one"),))

    with pytest.raises(CommandError, match="Change filter matched no entries"):
        plan_module._filter_entries(plan, ("two",), ())


def test_prepare_human_output_strips_headers_and_shortens() -> None:
    content = "%default_engine=sqlite\nchange widgets # comment\n"

    result = plan_module._prepare_human_output(content, strip_headers=True, short=True)

    assert "default_engine" not in result
    assert "# comment" not in result


def test_build_json_payload_serialises_entries(tmp_path: Path) -> None:
    change = _make_change("one", notes="note")
    tag = Tag(
        name="v1.0",
        change_ref=change.name,
        planner="Planner",
        tagged_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    plan = _make_plan((change, tag))
    object.__setattr__(plan, "file_path", tmp_path / "sqlitch.plan")

    payload = plan_module._build_json_payload(plan, plan.entries)

    assert payload["project"] == "widgets"
    assert payload["entries"][0]["type"] == "change"
    assert payload["entries"][1]["type"] == "tag"


def test_strip_notes_from_entries_removes_notes(tmp_path: Path) -> None:
    change = _make_change("one", notes="note")
    plan = _make_plan((change,))

    stripped = plan_module._strip_notes_from_entries(plan.entries)

    assert isinstance(stripped[0], Change)
    assert stripped[0].notes is None


def test_emit_missing_dependency_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(click, "secho", lambda message, **kwargs: captured.append(message))

    change = _make_change("one")
    plan = _make_plan((change,))
    object.__setattr__(plan, "missing_dependencies", ("one->users",))

    plan_module._emit_missing_dependency_warnings(plan)

    assert captured == [
        "Warning: change 'one' references dependency 'users' before it appears in the plan."
    ]


def test_entry_to_json_formats_relative_paths(tmp_path: Path) -> None:
    change = _make_change("one")
    base = tmp_path
    entry_json = plan_module._entry_to_json(change, base)

    assert entry_json["scripts"]["deploy"].endswith("deploy.sql")


def test_prepare_human_output_preserves_trailing_newline() -> None:
    content = "line\n"

    assert plan_module._prepare_human_output(content, strip_headers=False, short=False).endswith(
        "\n"
    )
