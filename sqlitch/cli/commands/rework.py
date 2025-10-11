"""Implementation of the ``sqlitch rework`` command."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import click

from sqlitch.config.resolver import resolve_config
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change, Plan, PlanEntry, Tag
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.plan.utils import slugify_change_name
from sqlitch.utils.identity import resolve_planner_identity

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path
from .add import _ensure_script_path, _format_display_path

__all__ = ["rework_command"]


def _utcnow() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


def _resolve_new_path(
    *,
    project_root: Path,
    original: Path | None,
    override: str | None,
    slug: str,
    suffix: str,
) -> Path | None:
    if override:
        candidate = Path(override)
        return candidate if candidate.is_absolute() else project_root / candidate

    if original is None:
        return None

    filename = f"{slug}{suffix}{original.suffix}"
    return original.parent / filename


def _resolve_rework_suffix(plan: Plan, change_name: str) -> str:
    """Return the suffix (``@tag``) used for reworked script filenames.
    
    Sqitch uses the most recent tag in the plan (the one closest to the
    rework point), not necessarily a tag associated with the change being
    reworked.
    """
    # Find the last tag in the plan (most recent)
    latest_tag: str | None = None
    for entry in plan.entries:
        if isinstance(entry, Tag):
            latest_tag = entry.name

    if latest_tag is None:
        raise CommandError(
            f'Change "{change_name}" has not been tagged. Tag the change before reworking it.'
        )

    return f"@{latest_tag}"


def _copy_script(source: Path | None, target: Path | None) -> None:
    if target is None:
        return
    if source is None:
        raise CommandError("Change is missing a script required for rework.")
    if not source.exists():
        raise CommandError(f"Source script {source} is missing")

    _ensure_script_path(target)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _append_rework_change(
    *,
    entries: Sequence[PlanEntry],
    name: str,
    rework: Change,
) -> tuple[PlanEntry, ...]:
    """Append a reworked change to the plan entries (Sqitch behavior).
    
    Unlike _replace_change, this adds a new entry at the end of the plan
    while keeping the original entry intact. This matches Sqitch's rework
    behavior where the same change name can appear multiple times.
    
    Args:
        entries: Current plan entries
        name: Name of the change being reworked
        rework: New Change object representing the reworked version
        
    Returns:
        Updated tuple of entries with rework appended
        
    Raises:
        CommandError: If the change doesn't exist in the plan
    """
    # Verify the change exists
    has_change = any(
        isinstance(entry, Change) and entry.name == name
        for entry in entries
    )
    if not has_change:
        raise CommandError(f'Unknown change "{name}"')
    
    # Append the reworked change at the end
    return tuple(list(entries) + [rework])


@click.command("rework")
@click.argument("change_name")
@click.option("--requires", "requires", multiple=True, help="Override change dependencies.")
@click.option("-n", "--note", "note", help="Update the change note.")
@click.option("--deploy", "deploy_override", help="Explicit path for the reworked deploy script.")
@click.option("--revert", "revert_override", help="Explicit path for the reworked revert script.")
@click.option("--verify", "verify_override", help="Explicit path for the reworked verify script.")
@global_sqitch_options
@global_output_options
@click.pass_context
def rework_command(
    ctx: click.Context,
    change_name: str,
    requires: Sequence[str],
    note: str | None,
    deploy_override: str | None,
    revert_override: str | None,
    verify_override: str | None,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Duplicate change scripts and update the plan entry for ``change_name``."""

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    env = cli_context.env

    # Load configuration for planner identity resolution
    config = resolve_config(
        root_dir=project_root,
        config_root=cli_context.config_root,
        env=env,
    )

    plan_path = resolve_plan_path(
        project_root=project_root,
        override=cli_context.plan_file,
        env=env,
        missing_plan_message="No plan file found. Run `sqlitch init` before reworking changes.",
    )

    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=env,
        engine_override=cli_context.engine,
        plan_path=plan_path,
    )

    try:
        original_plan_text = plan_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:  # pragma: no cover - IO propagated as command error
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc

    include_default_engine_header = "%default_engine=" in original_plan_text

    try:
        plan = parse_plan(plan_path, default_engine=default_engine)
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:  # pragma: no cover - IO propagated as command error
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc
    except PlanParseError as exc:
        raise CommandError(str(exc)) from exc

    try:
        original_change = plan.get_change(change_name)
    except KeyError as exc:
        raise CommandError(f'Unknown change "{change_name}"') from exc

    timestamp = _utcnow()
    slug = slugify_change_name(change_name)
    suffix = _resolve_rework_suffix(plan, change_name)

    deploy_source = original_change.script_paths.get("deploy")
    revert_source = original_change.script_paths.get("revert")
    verify_source = original_change.script_paths.get("verify")

    deploy_target = _resolve_new_path(
        project_root=project_root,
        original=deploy_source,
        override=deploy_override,
        slug=slug,
        suffix=suffix,
    )
    revert_target = _resolve_new_path(
        project_root=project_root,
        original=revert_source,
        override=revert_override,
        slug=slug,
        suffix=suffix,
    )
    verify_target = _resolve_new_path(
        project_root=project_root,
        original=verify_source,
        override=verify_override,
        slug=slug,
        suffix=suffix,
    )

    _copy_script(deploy_source, deploy_target)
    _copy_script(revert_source, revert_target)
    _copy_script(verify_source, verify_target)

    new_notes = note if note is not None else original_change.notes

    script_map: dict[str, Path | None] = {
        "deploy": deploy_target,
        "revert": revert_target,
    }
    if verify_target is not None:
        script_map["verify"] = verify_target

    # Create rework change with dependency on previous version via tag
    # Format: change_name [change_name@tag]
    # The rework inherits a single dependency: reference to the previous version
    # If --requires is specified, use those instead
    rework_dependency = f"{change_name}{suffix}"
    rework_dependencies = tuple(requires) if requires else (rework_dependency,)
    
    replacement = Change.create(
        name=original_change.name,
        script_paths=script_map,
        planner=resolve_planner_identity(env, config),
        planned_at=timestamp,
        notes=new_notes,
        change_id=original_change.change_id,
        dependencies=rework_dependencies,
        tags=original_change.tags,
        rework_of=rework_dependency,  # Mark as rework
    )

    # Append rework to plan (Sqitch behavior: adds new entry, doesn't replace)
    updated_entries = _append_rework_change(
        entries=plan.entries, name=change_name, rework=replacement
    )

    write_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=updated_entries,
        plan_path=plan.file_path,
        syntax_version=plan.syntax_version,
        uri=plan.uri,
        include_default_engine=include_default_engine_header,
    )

    quiet = bool(cli_context.quiet)

    def _emit(message: str) -> None:
        if not quiet:
            click.echo(message)

    for kind, target in (
        ("deploy", deploy_target),
        ("revert", revert_target),
        ("verify", verify_target),
    ):
        if target is not None:
            _emit(f"Created rework {kind} script {_format_display_path(target, project_root)}")

    _emit(f"Reworked {change_name}")
    _emit("")


@register_command("rework")
def _register_rework(group: click.Group) -> None:
    """Attach the rework command to the root Click group."""

    group.add_command(rework_command)
