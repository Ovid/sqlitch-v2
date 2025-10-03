"""Implementation of the ``sqlitch plan`` command."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import click

from sqlitch.plan.formatter import format_plan
from sqlitch.plan.model import Change, Plan, PlanEntry, Tag
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.utils.fs import ArtifactConflictError, resolve_plan_file

from . import CommandError, register_command
from ._context import environment_from, plan_override_from, project_root_from

__all__ = ["plan_command"]


@click.command("plan")
@click.option("--project", "project_filter", help="Restrict output to the specified project name.")
@click.option(
    "--change",
    "change_filters",
    multiple=True,
    help="Filter output to one or more change entries (repeatable).",
)
@click.option(
    "--tag",
    "tag_filters",
    multiple=True,
    help="Filter output to one or more tag entries (repeatable).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(("human", "json"), case_sensitive=False),
    default="human",
    show_default=True,
    help="Select the output format (human or json).",
)
@click.option(
    "--short",
    "short_output",
    is_flag=True,
    help="Shorten human-readable output by omitting notes metadata tokens.",
)
@click.option(
    "--no-header",
    "suppress_headers",
    is_flag=True,
    help="Omit plan header pragmas from human-readable output.",
)
@click.pass_context
def plan_command(
    ctx: click.Context,
    *,
    project_filter: str | None,
    change_filters: Sequence[str],
    tag_filters: Sequence[str],
    output_format: str,
    short_output: bool,
    suppress_headers: bool,
) -> None:
    """Render the deployment plan content using Sqitch-compatible ergonomics."""

    project_root = project_root_from(ctx)
    plan_override = plan_override_from(ctx)
    environment = environment_from(ctx)

    plan_path = _resolve_plan_path(project_root, override=plan_override, env=environment)
    raw_content = _read_plan_text(plan_path)

    requires_model = bool(project_filter or change_filters or tag_filters or output_format.lower() == "json")

    if output_format.lower() == "human" and not requires_model:
        text = _prepare_human_output(raw_content, strip_headers=suppress_headers, short=short_output)
        click.echo(text, nl=False)
        return

    plan = _parse_plan_model(plan_path)

    if project_filter and project_filter != plan.project_name:
        raise CommandError(
            f"Plan project '{plan.project_name}' does not match requested project '{project_filter}'"
        )

    filtered_entries = _filter_entries(plan, change_filters, tag_filters)

    if output_format.lower() == "json":
        payload = _build_json_payload(plan, filtered_entries)
        click.echo(json.dumps(payload, indent=2, sort_keys=False))
        return

    rendered = format_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=filtered_entries,
        base_path=plan.file_path.parent,
    )
    text = _prepare_human_output(rendered, strip_headers=suppress_headers, short=short_output)
    click.echo(text, nl=False)


@register_command("plan")
def _register_plan(group: click.Group) -> None:
    """Attach the plan command to the root Click group."""

    group.add_command(plan_command)


def _resolve_plan_path(
    project_root: Path,
    *,
    override: Path | None,
    env: Mapping[str, str],
) -> Path:
    if override is not None:
        if not override.exists():
            raise CommandError(f"Plan file {override} is missing")
        return override

    env_value = env.get("SQITCH_PLAN_FILE") or env.get("SQLITCH_PLAN_FILE")
    if env_value:
        env_path = Path(env_value)
        resolved = env_path if env_path.is_absolute() else project_root / env_path
        if not resolved.exists():
            raise CommandError(f"Plan file {resolved} is missing")
        return resolved

    try:
        resolution = resolve_plan_file(project_root)
    except ArtifactConflictError as exc:
        raise CommandError(str(exc)) from exc

    if resolution.path is None:
        raise CommandError("No plan file found. Run `sqlitch init` before inspecting the plan.")
    return resolution.path


def _read_plan_text(plan_path: Path) -> str:
    try:
        return plan_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:  # pragma: no cover - IO failures propagated to the user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _parse_plan_model(plan_path: Path) -> Plan:
    try:
        return parse_plan(plan_path)
    except (PlanParseError, ValueError) as exc:
        raise CommandError(str(exc)) from exc
    except OSError as exc:  # pragma: no cover - IO failures propagated to the user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _filter_entries(
    plan: Plan,
    change_filters: Sequence[str],
    tag_filters: Sequence[str],
) -> tuple[PlanEntry, ...]:
    if not change_filters and not tag_filters:
        return tuple(plan.entries)

    change_set = {value for value in change_filters}
    tag_set = {value for value in tag_filters}

    selected: list[PlanEntry] = []
    matched_changes: set[str] = set()
    matched_tags: set[str] = set()

    for entry in plan.entries:
        if isinstance(entry, Change):
            if change_set and entry.name in change_set:
                selected.append(entry)
                matched_changes.add(entry.name)
        else:
            if tag_set and entry.name in tag_set:
                selected.append(entry)
                matched_tags.add(entry.name)
            elif change_set and entry.change_ref in change_set:
                selected.append(entry)

    missing_changes = change_set.difference(matched_changes)
    if missing_changes:
        missing = ", ".join(sorted(missing_changes))
        raise CommandError(f"Change filter matched no entries: {missing}")

    missing_tags = tag_set.difference(matched_tags)
    if missing_tags:
        missing = ", ".join(sorted(missing_tags))
        raise CommandError(f"Tag filter matched no entries: {missing}")

    return tuple(selected)


def _prepare_human_output(content: str, *, strip_headers: bool, short: bool) -> str:
    lines = content.splitlines()
    processed: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if strip_headers and stripped.startswith("%"):
            continue
        if short and "notes=" in line:
            tokens = [token for token in line.split() if not token.startswith("notes=")]
            line = " ".join(tokens)
        processed.append(line)

    text = "\n".join(processed)
    if content.endswith("\n"):
        text += "\n"
    return text


def _build_json_payload(plan: Plan, entries: Sequence[PlanEntry]) -> dict[str, object]:
    base_dir = plan.file_path.parent
    return {
        "project": plan.project_name,
        "default_engine": plan.default_engine,
        "plan_path": str(plan.file_path.resolve()),
        "entries": [_entry_to_json(entry, base_dir) for entry in entries],
    }


def _entry_to_json(entry: PlanEntry, base_dir: Path) -> dict[str, object]:
    if isinstance(entry, Change):
        return {
            "type": "change",
            "name": entry.name,
            "planner": entry.planner,
            "planned_at": entry.planned_at.isoformat(),
            "notes": entry.notes,
            "dependencies": list(entry.dependencies),
            "tags": list(entry.tags),
            "change_id": str(entry.change_id) if entry.change_id is not None else None,
            "scripts": {
                key: _format_path(path, base_dir) for key, path in entry.script_paths.items()
            },
        }

    assert isinstance(entry, Tag)
    return {
        "type": "tag",
        "name": entry.name,
        "change": entry.change_ref,
        "planner": entry.planner,
        "tagged_at": entry.tagged_at.isoformat(),
    }


def _format_path(path: Path | None, base_dir: Path) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.resolve().as_posix()