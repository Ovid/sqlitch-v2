"""Unit coverage for helper functions in ``sqlitch.cli.commands.deploy``."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import click
import pytest

from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands import deploy as deploy_module
from sqlitch.plan.model import Change, Plan, Tag


def _make_change(name: str) -> Change:
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return Change.create(
        name=name,
        script_paths={"deploy": Path("deploy.sql"), "revert": Path("revert.sql")},
        planner="Tester",
        planned_at=timestamp,
    )


def _make_plan(changes: tuple[Change, ...], tags: tuple[Tag, ...] = ()) -> Plan:
    entries = changes + tags
    return Plan(
        project_name="demo",
        file_path=Path("sqlitch.plan"),
        entries=entries,
        checksum="checksum",
        default_engine="sqlite",
    )


def test_resolve_target_prefers_option() -> None:
    assert deploy_module._resolve_target("cli", "config") == "cli"


def test_resolve_target_requires_value() -> None:
    with pytest.raises(CommandError, match="must be provided"):
        deploy_module._resolve_target(None, None)


def test_select_changes_by_change_filters() -> None:
    first = _make_change("one")
    second = _make_change("two")
    plan = _make_plan((first, second))

    selected = deploy_module._select_changes(plan=plan, to_change="two", to_tag=None)

    assert selected == (first, second)


def test_select_changes_by_tag_filters() -> None:
    first = _make_change("one")
    second = _make_change("two")
    tag = Tag(
        name="v1.0",
        change_ref=second.name,
        planner="Tester",
        tagged_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    plan = _make_plan((first, second), (tag,))

    selected = deploy_module._select_changes(plan=plan, to_change=None, to_tag="v1.0")

    assert selected == (first, second)


def test_select_changes_missing_change_raises() -> None:
    plan = _make_plan((_make_change("one"),))

    with pytest.raises(CommandError, match="does not contain change"):
        deploy_module._select_changes(plan=plan, to_change="missing", to_tag=None)


def test_select_changes_missing_tag_raises() -> None:
    plan = _make_plan((_make_change("one"),))

    with pytest.raises(CommandError, match="does not contain tag"):
        deploy_module._select_changes(plan=plan, to_change=None, to_tag="v1.0")


def test_render_log_only_deploy_respects_quiet(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[str] = []
    monkeypatch.setattr(click, "echo", lambda message: captured.append(message))

    plan = _make_plan((_make_change("one"),))
    request = deploy_module._DeployRequest(
        project_root=tmp_path,
        env={},
        plan_path=tmp_path / "sqlitch.plan",
        plan=plan,
        target="db:sqlite:demo",
        to_change=None,
        to_tag=None,
        log_only=True,
        quiet=True,
    )

    deploy_module._render_log_only_deploy(request, plan.changes)

    assert captured == []


def test_render_log_only_deploy_outputs_messages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[str] = []
    monkeypatch.setattr(click, "echo", lambda message: captured.append(message))

    plan = _make_plan((_make_change("one"),))
    request = deploy_module._DeployRequest(
        project_root=tmp_path,
        env={},
        plan_path=tmp_path / "sqlitch.plan",
        plan=plan,
        target="db:sqlite:demo",
        to_change=None,
        to_tag=None,
        log_only=True,
        quiet=False,
    )

    deploy_module._render_log_only_deploy(request, ())

    assert "No changes available for deployment." in captured
    assert any("Log-only run" in line for line in captured)


def test_build_emitter_obeys_quiet_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []
    monkeypatch.setattr(click, "echo", lambda message: captured.append(message))

    loud = deploy_module._build_emitter(False)
    quiet = deploy_module._build_emitter(True)

    loud("hello")
    quiet("ignored")

    assert captured == ["hello"]

