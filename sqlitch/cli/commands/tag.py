"""Implementation of the ``sqlitch tag`` command."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import click

from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Tag
from sqlitch.plan.parser import PlanParseError, parse_plan

from . import CommandError, register_command
from ._context import require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path

__all__ = ["tag_command"]


def _utcnow() -> datetime:
    """Return the current UTC timestamp.

    Wrapped to support monkeypatching in tests.
    """

    return datetime.now(timezone.utc)


def _resolve_planner(env: dict[str, str]) -> str:
    """Resolve the planner identity from available environment variables."""

    name = (
        env.get("SQLITCH_USER_NAME")
        or env.get("GIT_AUTHOR_NAME")
        or env.get("USER")
        or env.get("USERNAME")
        or "SQLitch User"
    )
    email = env.get("SQLITCH_USER_EMAIL") or env.get("GIT_AUTHOR_EMAIL") or env.get("EMAIL")
    return f"{name} <{email}>" if email else name


@click.command("tag")
@click.argument("tag_name", required=False)
@click.argument("change_name", required=False)
@click.option("--list", "list_tags", is_flag=True, help="List all tags in the plan.")
@click.option("--note", "note", help="Note to associate with the tag.")
@click.pass_context
def tag_command(
    ctx: click.Context,
    tag_name: str | None,
    change_name: str | None,
    list_tags: bool,
    note: str | None,
) -> None:
    """Add or list tags in the deployment plan."""

    if list_tags:
        if tag_name or change_name or note:
            raise click.UsageError("--list cannot be combined with other arguments")
        _list_tags(ctx)
        return

    if not tag_name:
        raise click.UsageError("A tag name must be provided when not using --list")

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
        planner=_resolve_planner(environment),
        tagged_at=_utcnow(),
    )

    # Append to plan entries
    entries = tuple(plan.entries) + (tag,)

    write_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=entries,
        plan_path=plan.file_path,
        syntax_version=plan.syntax_version,
        uri=plan.uri,
    )

    click.echo(f"Tagged {target_change} with @{tag_name}")


@register_command("tag")
def _register_tag(group: click.Group) -> None:
    """Register the tag command with the root CLI group."""

    group.add_command(tag_command)