"""Implementation of the ``sqlitch plan`` command."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import click

from sqlitch.plan.formatter import format_plan
from sqlitch.plan.model import Change, Plan, PlanEntry, Tag
from sqlitch.plan.parser import PlanParseError, parse_plan

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import environment_from, plan_override_from, project_root_from, require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path

__all__ = ["plan_command"]


@click.command("plan")
@click.argument("target_args", nargs=-1)
@click.option("--target", "target_option", help="Deployment target URI or database path.")
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
@global_sqitch_options
@global_output_options
@click.pass_context
def plan_command(
    ctx: click.Context,
    *,
    target_args: tuple[str, ...],
    target_option: str | None,
    project_filter: str | None,
    change_filters: Sequence[str],
    tag_filters: Sequence[str],
    output_format: str,
    short_output: bool,
    suppress_headers: bool,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Render the deployment plan content using Sqitch-compatible ergonomics."""

    cli_context = require_cli_context(ctx)
    project_root = project_root_from(ctx)
    plan_override = plan_override_from(ctx)
    environment = environment_from(ctx)

    plan_path = resolve_plan_path(
        project_root=project_root,
        override=plan_override,
        env=environment,
        missing_plan_message="No plan file found. Run `sqlitch init` before inspecting the plan.",
    )
    raw_content = _read_plan_text(plan_path)

    normalized_format = output_format.lower()
    requires_model = bool(
        project_filter
        or change_filters
        or tag_filters
        or normalized_format == "json"
        or short_output
    )

    engine_error: CommandError | None = None
    try:
        default_engine = resolve_default_engine(
            project_root=project_root,
            config_root=cli_context.config_root,
            env=environment,
            engine_override=cli_context.engine,
            plan_path=plan_path,
        )
    except CommandError as exc:
        engine_error = exc
        default_engine = None

    try:
        plan = _parse_plan_model(plan_path, default_engine)
    except CommandError:
        if default_engine is None and engine_error is not None:
            raise engine_error
        raise

    _emit_missing_dependency_warnings(plan)

    if normalized_format == "human" and not requires_model:
        text = _prepare_human_output(
            raw_content, strip_headers=suppress_headers, short=short_output
        )
        click.echo(text, nl=False)
        return

    if project_filter and project_filter != plan.project_name:
        raise CommandError(
            f"Plan project '{plan.project_name}' does not match "
            f"requested project '{project_filter}'"
        )

    filtered_entries = _filter_entries(plan, change_filters, tag_filters)

    if normalized_format == "json":
        payload = _build_json_payload(plan, filtered_entries)
        click.echo(json.dumps(payload, indent=2, sort_keys=False))
        return

    entries_to_render = filtered_entries
    if short_output:
        entries_to_render = _strip_notes_from_entries(entries_to_render)

    rendered = format_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=entries_to_render,
        base_path=plan.file_path.parent,
        syntax_version=plan.syntax_version,
        uri=plan.uri,
    )
    text = _prepare_human_output(rendered, strip_headers=suppress_headers, short=False)
    click.echo(text, nl=False)


@register_command("plan")
def _register_plan(group: click.Group) -> None:
    """Attach the plan command to the root Click group."""

    group.add_command(plan_command)


def _read_plan_text(plan_path: Path) -> str:
    try:
        return plan_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:  # pragma: no cover - IO failures propagated to the user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _parse_plan_model(plan_path: Path, default_engine: str | None) -> Plan:
    try:
        return parse_plan(plan_path, default_engine=default_engine)
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
        if short:
            if "notes=" in line:
                tokens = [token for token in line.split() if not token.startswith("notes=")]
                line = " ".join(tokens)
            if "#" in line:
                line = line.split("#", 1)[0].rstrip()
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
        "syntax_version": plan.syntax_version,
        "uri": plan.uri,
        "plan_path": str(plan.file_path.resolve()),
        "missing_dependencies": list(plan.missing_dependencies),
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

    assert isinstance(entry, Tag)  # nosec B101 - type guard after Change branch
    return {
        "type": "tag",
        "name": entry.name,
        "change": entry.change_ref,
        "planner": entry.planner,
        "tagged_at": entry.tagged_at.isoformat(),
    }


def _format_path(path: Path | str | None, base_dir: Path) -> str | None:
    if path is None:
        return None
    if isinstance(path, str):
        path = Path(path)
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _strip_notes_from_entries(entries: Sequence[PlanEntry]) -> tuple[PlanEntry, ...]:
    sanitized: list[PlanEntry] = []
    for entry in entries:
        if isinstance(entry, Change) and entry.notes:
            sanitized.append(replace(entry, notes=None))
        else:
            sanitized.append(entry)
    return tuple(sanitized)


def _emit_missing_dependency_warnings(plan: Plan) -> None:
    if not plan.missing_dependencies:
        return

    for spec in plan.missing_dependencies:
        change, dependency = spec.split("->", 1)
        click.secho(
            f"Warning: change '{change}' references dependency "
            f"'{dependency}' before it appears in the plan.",
            err=True,
            fg="yellow",
        )
