"""Implementation of the ``sqlitch show`` command."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import click

from sqlitch.plan.model import Change, Plan
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.utils.time import isoformat_utc

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import (
    environment_from,
    plan_override_from,
    project_root_from,
    require_cli_context,
)
from ._plan_utils import resolve_default_engine, resolve_plan_path
from .add import _format_display_path

__all__ = ["show_command"]


@click.command("show")
@click.argument("item", required=False)
@click.option("--target", "target_option", help="Deployment target URI or database path.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("human", "json"), case_sensitive=False),
    default="human",
    show_default=True,
    help="Select the output format.",
)
@click.option(
    "--script",
    "script_kind",
    type=click.Choice(("deploy", "revert", "verify"), case_sensitive=False),
    help="Print the contents of the specified script instead of metadata.",
)
@click.option(
    "--project",
    "project_filter",
    help="Assert the plan project name matches this value.",
)
@global_sqitch_options
@global_output_options
@click.pass_context
def show_command(
    ctx: click.Context,
    item: str | None,
    target_option: str | None,
    output_format: str,
    script_kind: str | None,
    project_filter: str | None,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Display plan metadata or scripts for ``item`` change or tag."""

    cli_context = require_cli_context(ctx)
    project_root = project_root_from(ctx)
    env = environment_from(ctx)
    plan_override = plan_override_from(ctx)

    plan_path = resolve_plan_path(
        project_root=project_root,
        override=plan_override,
        env=env,
        missing_plan_message="Cannot read plan file sqitch.plan",
    )

    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        engine_override=cli_context.engine,
        plan_path=plan_path,
    )

    plan = _load_plan(plan_path, default_engine)

    if project_filter and project_filter != plan.project_name:
        raise CommandError(
            f"Plan project '{plan.project_name}' does not match "
            f"requested project '{project_filter}'."
        )

    if not item:
        raise CommandError("Change or tag name must be specified")

    change = _resolve_change(plan, item)

    if script_kind:
        _emit_script(change=change, project_root=project_root, kind=script_kind.lower())
        return

    tags = _collect_tags(plan, change)
    if output_format.lower() == "json":
        payload = _build_json_payload(change=change, tags=tags, project_root=project_root)
        click.echo(json.dumps(payload, indent=2))
        return

    lines = _build_human_output(change=change, tags=tags, project_root=project_root)
    click.echo("\n".join(lines))


def _load_plan(plan_path: Path, default_engine: str | None) -> Plan:
    try:
        return parse_plan(plan_path, default_engine=default_engine)
    except FileNotFoundError as exc:  # pragma: no cover - defensive guard
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:  # pragma: no cover - surfaced to user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc
    except PlanParseError as exc:
        raise CommandError(str(exc)) from exc


def _resolve_change(plan: Plan, reference: str) -> Change:
    if plan.has_change(reference):
        return plan.get_change(reference)

    for tag in plan.tags:
        if tag.name == reference:
            try:
                return plan.get_change(tag.change_ref)
            except KeyError as exc:  # pragma: no cover - defensive guard
                raise CommandError(
                    f"Tag '{tag.name}' references unknown change '{tag.change_ref}'."
                ) from exc

    raise CommandError(f'Unknown change "{reference}"')


def _collect_tags(plan: Plan, change: Change) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()

    for tag_name in change.tags:
        if tag_name not in seen:
            ordered.append(tag_name)
            seen.add(tag_name)

    for tag_entry in plan.tags:
        if tag_entry.change_ref != change.name:
            continue
        if tag_entry.name in seen:
            continue
        ordered.append(tag_entry.name)
        seen.add(tag_entry.name)

    return tuple(ordered)


def _build_json_payload(
    *,
    change: Change,
    tags: tuple[str, ...],
    project_root: Path,
) -> dict[str, object]:
    scripts: dict[str, str] = {}
    for kind, path in change.script_paths.items():
        if path is None:
            continue
        path_obj = Path(path)
        scripts[kind] = _format_display_path(path_obj, project_root)

    return {
        "change": change.name,
        "planner": change.planner,
        "planned_at": isoformat_utc(
            change.planned_at,
            drop_microseconds=True,
            use_z_suffix=True,
        ),
        "dependencies": list(change.dependencies),
        "tags": list(tags),
        "notes": change.notes,
        "scripts": scripts,
    }


def _build_human_output(
    *,
    change: Change,
    tags: tuple[str, ...],
    project_root: Path,
) -> list[str]:
    lines = [
        f"Change: {change.name}",
        f"Planner: {change.planner}",
        f"Planned At: {isoformat_utc(change.planned_at, drop_microseconds=True, use_z_suffix=True)}",  # noqa: E501 pylint: disable=line-too-long
        f"Dependencies: {_format_list(change.dependencies)}",
        f"Tags: {_format_list(tags)}",
    ]

    if change.notes:
        lines.append(f"Notes: {change.notes}")
    else:
        lines.append("Notes: (none)")

    for kind in ("deploy", "revert", "verify"):
        path = change.script_paths.get(kind)
        if path is None:
            continue
        path_obj = Path(path)
        lines.append(f"{kind.capitalize()} Script: {_format_display_path(path_obj, project_root)}")

    return lines


def _format_list(values: Sequence[str]) -> str:
    items = list(values)
    return ", ".join(items) if items else "(none)"


def _emit_script(*, change: Change, project_root: Path, kind: str) -> None:
    script_path = change.script_paths.get(kind)
    if script_path is None:
        raise CommandError(f"Cannot find {kind} script for {change.name}")

    path_obj = Path(script_path)
    path_obj = path_obj if path_obj.is_absolute() else (project_root / path_obj).resolve()

    if not path_obj.exists():
        raise CommandError(f"Cannot find {kind} script for {change.name}")

    content = path_obj.read_text(encoding="utf-8")
    click.echo(content, nl=False)


@register_command("show")
def _register_show(group: click.Group) -> None:
    """Attach the show command to the root Click group."""

    group.add_command(show_command)
