"""Implementation of the ``sqlitch add`` command."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

import click

from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.utils.fs import ArtifactConflictError, resolve_plan_file

from . import CommandError, register_command
from ._context import environment_from, plan_override_from, project_root_from, quiet_mode_enabled

__all__ = ["add_command"]


def _utcnow() -> datetime:
    """Return the current UTC timestamp.

    Wrapped to support monkeypatching in tests.
    """

    return datetime.now(timezone.utc)


def _slugify(name: str) -> str:
    """Return a filesystem-friendly slug for ``name``."""

    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)


def _resolve_planner(env: Mapping[str, str]) -> str:
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


def _resolve_script_path(root: Path, value: str | None, default: Path) -> Path:
    candidate = Path(value) if value is not None else default
    return candidate if candidate.is_absolute() else root / candidate


def _ensure_script_path(path: Path) -> None:
    if path.exists():
        raise CommandError(f"Script {path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_placeholder(path: Path, change_name: str, kind: str) -> None:
    content = (
        "-- SQLitch generated {kind} script for {change}\n".format(kind=kind, change=change_name)
    )
    path.write_text(content, encoding="utf-8")


def _format_display_path(path: Path, project_root: Path) -> str:
    try:
        relative = path.relative_to(project_root)
        return relative.as_posix()
    except ValueError:
        return os.path.relpath(path, project_root).replace(os.sep, "/")


@click.command("add")
@click.argument("change_name")
@click.option("--requires", "requires", multiple=True, help="Declare change dependencies.")
@click.option("--tags", "tags", multiple=True, help="Attach tags to the change.")
@click.option("--note", "note", help="Add a note to the change entry.")
@click.option("--deploy", "deploy_path", help="Explicit deploy script path.")
@click.option("--revert", "revert_path", help="Explicit revert script path.")
@click.option("--verify", "verify_path", help="Explicit verify script path.")
@click.option("--template", "template_name", help="Template name (not yet supported).")
@click.pass_context
def add_command(
    ctx: click.Context,
    change_name: str,
    requires: Sequence[str],
    tags: Sequence[str],
    note: str | None,
    deploy_path: str | None,
    revert_path: str | None,
    verify_path: str | None,
    template_name: str | None,
) -> None:
    """Create change scripts and append an entry to the project plan.

    Args:
        ctx: The Click context containing the prepared ``CLIContext``.
        change_name: Human-readable name used for plan entry and script files.
        requires: Zero or more change identifiers this change depends on.
        tags: Optional collection of tag strings applied to the new change.
        note: Optional free-form note stored with the change metadata.
        deploy_path: Optional explicit path for the deploy script template.
        revert_path: Optional explicit path for the revert script template.
        verify_path: Optional explicit path for the verify script template.
        template_name: Name of a script template to apply (currently unsupported).

    Raises:
        CommandError: If templates are requested, plan discovery fails, plan parsing
            fails, scripts already exist, or the change name has already been
            recorded in the plan.
    """

    if template_name is not None:
        raise CommandError("--template is not supported yet")

    project_root = project_root_from(ctx)
    plan_override = plan_override_from(ctx)
    environment = environment_from(ctx)
    quiet = quiet_mode_enabled(ctx)

    if plan_override is not None:
        plan_path = plan_override
        if not plan_path.exists():
            raise CommandError(f"Plan file {plan_path} is missing")
    else:
        try:
            resolution = resolve_plan_file(project_root)
        except ArtifactConflictError as exc:  # pragma: no cover - exercised via integration tests
            raise CommandError(str(exc)) from exc

        plan_path = resolution.path
        if plan_path is None:
            raise CommandError("No plan file found. Run `sqlitch init` before adding changes.")

    try:
        plan = parse_plan(plan_path)
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:  # pragma: no cover - IO failure propagated as command error
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc
    except PlanParseError as exc:
        raise CommandError(str(exc)) from exc

    if plan.has_change(change_name):
        raise CommandError(f'Change "{change_name}" already exists in plan')

    timestamp = _utcnow()
    token = timestamp.strftime("%Y%m%d%H%M%S")
    slug = _slugify(change_name)

    default_deploy = Path("deploy") / f"{token}_{slug}.sql"
    default_revert = Path("revert") / f"{token}_{slug}.sql"
    default_verify = Path("verify") / f"{token}_{slug}.sql"

    deploy_target = _resolve_script_path(project_root, deploy_path, default_deploy)
    revert_target = _resolve_script_path(project_root, revert_path, default_revert)
    verify_target = _resolve_script_path(project_root, verify_path, default_verify)

    _ensure_script_path(deploy_target)
    _ensure_script_path(revert_target)
    _ensure_script_path(verify_target)

    _write_placeholder(deploy_target, change_name, "deploy")
    _write_placeholder(revert_target, change_name, "revert")
    _write_placeholder(verify_target, change_name, "verify")

    script_map: dict[str, Path] = {
        "deploy": deploy_target,
        "revert": revert_target,
        "verify": verify_target,
    }

    change = Change.create(
        name=change_name,
        script_paths=script_map,
        planner=_resolve_planner(environment),
        planned_at=timestamp,
        notes=note,
        dependencies=tuple(requires) or None,
        tags=tuple(tags) or None,
    )

    entries = tuple(plan.entries) + (change,)

    write_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=entries,
        plan_path=plan.file_path,
    )

    def _echo(message: str) -> None:
        if not quiet:
            click.echo(message)

    _echo(f"Created deploy script {_format_display_path(deploy_target, project_root)}")
    _echo(f"Created revert script {_format_display_path(revert_target, project_root)}")
    _echo(f"Created verify script {_format_display_path(verify_target, project_root)}")
    _echo(f"Added {change_name}")


@register_command("add")
def _register_add(group: click.Group) -> None:
    """Register the add command with the root CLI group."""

    group.add_command(add_command)