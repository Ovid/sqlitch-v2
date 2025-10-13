"""Implementation of the ``sqlitch tag`` command."""

from __future__ import annotations

from datetime import datetime, timezone

import click

from sqlitch.config.resolver import resolve_config
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change, PlanEntry, Tag
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.utils.identity import resolve_planner_identity

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import quiet_mode_enabled, require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path

__all__ = ["tag_command"]


def _utcnow() -> datetime:
    """Return the current UTC timestamp.

    Wrapped to support monkeypatching in tests.
    """

    return datetime.now(timezone.utc)


@click.command("tag")
@click.argument("tag_name", required=False)
@click.argument("change_name_arg", required=False)
@click.option("--change", "-c", "change_option", help="Tag the specified change.")
@click.option("--list", "list_tags", is_flag=True, help="List all tags in the plan.")
@click.option("--note", "-n", "note", help="Note to associate with the tag.")
@global_sqitch_options
@global_output_options
@click.pass_context
def tag_command(  # pylint: disable=unused-argument
    # json_mode/verbose/quiet injected by @global_output_options
    ctx: click.Context,
    tag_name: str | None,
    change_name_arg: str | None,
    change_option: str | None,
    list_tags: bool,
    note: str | None,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Add or list tags in the deployment plan."""

    if list_tags:
        if tag_name or change_name_arg or change_option or note:
            raise click.UsageError("--list cannot be combined with other arguments")
        _list_tags(ctx)
        return

    # If no tag name provided, default to listing tags (Sqitch behavior)
    if not tag_name:
        _list_tags(ctx)
        return

    # Resolve change name from positional arg or option
    change_name = change_name_arg or change_option

    _add_tag(ctx, tag_name, change_name, note)


def _list_tags(ctx: click.Context) -> None:
    """List all tags in the plan."""

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    environment = cli_context.env
    plan_path = resolve_plan_path(
        project_root=project_root,
        override=cli_context.plan_file,
        env=environment,
        missing_plan_message="No plan file found. Run `sqlitch init` before tagging.",
    )

    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=environment,
        engine_override=cli_context.engine,
        plan_path=plan_path,
    )

    try:
        plan = parse_plan(plan_path, default_engine=default_engine)
    except FileNotFoundError as exc:
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc
    except PlanParseError as exc:
        raise CommandError(str(exc)) from exc

    for tag in plan.tags:
        click.echo(f"@{tag.name}")


def _add_tag(
    ctx: click.Context,
    tag_name: str,
    change_name: str | None,
    note: str | None,
) -> None:
    """Add a tag to the plan."""

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    environment = cli_context.env
    quiet = quiet_mode_enabled(ctx)

    # Load configuration for planner identity resolution
    config = resolve_config(
        root_dir=project_root,
        config_root=cli_context.config_root,
        env=environment,
    )

    plan_path = resolve_plan_path(
        project_root=project_root,
        override=cli_context.plan_file,
        env=environment,
        missing_plan_message="No plan file found. Run `sqlitch init` before tagging.",
    )

    default_engine = resolve_default_engine(
        project_root=project_root,
        config_root=cli_context.config_root,
        env=environment,
        engine_override=cli_context.engine,
        plan_path=plan_path,
    )

    try:
        plan = parse_plan(plan_path, default_engine=default_engine)
    except FileNotFoundError as exc:
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc
    except PlanParseError as exc:
        raise CommandError(str(exc)) from exc

    # Check if tag already exists
    if any(tag.name == tag_name for tag in plan.tags):
        raise CommandError(f'Tag "{tag_name}" already exists')

    # Determine the change to tag
    if change_name:
        if not plan.has_change(change_name):
            raise CommandError(f'Unknown change "{change_name}"')
        target_change = change_name
    else:
        # Tag the latest change
        changes = plan.changes
        if not changes:
            raise CommandError("No changes found in plan to tag")
        target_change = changes[-1].name

    # Create the tag
    tag = Tag(
        name=tag_name,
        change_ref=target_change,
        planner=resolve_planner_identity(environment, config),
        tagged_at=_utcnow(),
        note=note,
    )

    # Find the position to insert the tag (after the change it references)
    new_entries: list[PlanEntry] = []
    tag_inserted = False

    for entry in plan.entries:
        new_entries.append(entry)
        # Insert tag after its referenced change
        if isinstance(entry, Change) and entry.name == target_change:
            new_entries.append(tag)
            tag_inserted = True

    if not tag_inserted:
        # This shouldn't happen as we validate change exists, but be safe
        raise CommandError(f'Could not find change "{target_change}" in plan')

    entries = tuple(new_entries)

    write_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=entries,
        plan_path=plan.file_path,
        syntax_version=plan.syntax_version,
        uri=plan.uri,
    )

    if not quiet:
        click.echo(f"Tagged {target_change} with @{tag_name}")


@register_command("tag")
def _register_tag(group: click.Group) -> None:
    """Register the tag command with the root CLI group."""

    group.add_command(tag_command)
