"""Implementation of the ``sqlitch add`` command."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

import click

from sqlitch.config.resolver import resolve_config
from sqlitch.engine.base import UnsupportedEngineError, canonicalize_engine_name
from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change
from sqlitch.plan.parser import PlanParseError, parse_plan
from sqlitch.plan.utils import slugify_change_name
from sqlitch.utils.identity import resolve_planner_identity
from sqlitch.utils.templates import default_template_body, render_template, resolve_template_path

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import require_cli_context
from ._plan_utils import resolve_default_engine, resolve_plan_path

__all__ = ["add_command"]


def _utcnow() -> datetime:
    """Return the current UTC timestamp.

    Wrapped to support monkeypatching in tests.
    """

    return datetime.now(timezone.utc)


def _resolve_script_path(root: Path, value: str | None, default: Path) -> Path:
    candidate = Path(value) if value is not None else default
    return candidate if candidate.is_absolute() else root / candidate


def _ensure_script_path(path: Path) -> None:
    if path.exists():
        raise CommandError(f"Script {path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)


def _format_display_path(path: Path, project_root: Path) -> str:
    try:
        relative = path.relative_to(project_root)
        return relative.as_posix()
    except ValueError:
        return os.path.relpath(path, project_root).replace(os.sep, "/")


def _discover_template_directories(
    project_root: Path, config_root: Path | None
) -> tuple[Path, ...]:
    directories: list[Path] = [project_root, project_root / "sqitch"]

    if config_root is not None:
        directories.append(config_root)
        directories.append(config_root / "sqitch")

    directories.append(Path("/etc/sqlitch"))
    directories.append(Path("/etc/sqitch"))

    ordered: list[Path] = []
    seen: set[Path] = set()
    for directory in directories:
        if directory in seen:
            continue
        seen.add(directory)
        ordered.append(directory)
    return tuple(ordered)


def _resolve_template_content(
    *,
    kind: str,
    engine: str,
    template_dirs: Sequence[Path],
    template_name: str | None,
) -> str:
    absolute_override: Path | None = None
    if template_name:
        candidate = Path(template_name)
        if candidate.is_absolute():
            absolute_override = candidate

    if absolute_override is not None:
        if not absolute_override.exists():
            raise CommandError(f"Template '{absolute_override}' does not exist")
        return absolute_override.read_text(encoding="utf-8")

    template_path = resolve_template_path(
        kind=kind,
        engine=engine,
        directories=template_dirs,
        template_name=template_name,
    )

    if template_name and template_path is None:
        raise CommandError(f"Template '{template_name}' could not be located for {kind}")

    if template_path is not None:
        return template_path.read_text(encoding="utf-8")

    return default_template_body(kind)


@click.command("add")
@click.argument("change_name")
@click.option("--requires", "requires", multiple=True, help="Declare change dependencies.")
@click.option("--conflicts", "conflicts", multiple=True, help="Declare conflicting changes.")
@click.option("--tags", "tags", multiple=True, help="Attach tags to the change.")
@click.option("-n", "--note", "note", help="Add a note to the change entry.")
@click.option("--deploy", "deploy_path", help="Explicit deploy script path.")
@click.option("--revert", "revert_path", help="Explicit revert script path.")
@click.option("--verify", "verify_path", help="Explicit verify script path.")
@click.option("--template", "template_name", help="Template name to apply when generating scripts.")
@global_sqitch_options
@global_output_options
@click.pass_context
def add_command(
    ctx: click.Context,
    change_name: str,
    requires: Sequence[str],
    conflicts: Sequence[str],
    tags: Sequence[str],
    note: str | None,
    deploy_path: str | None,
    revert_path: str | None,
    verify_path: str | None,
    template_name: str | None,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Create change scripts and append an entry to the project plan.

    Args:
        ctx: The Click context containing the prepared ``CLIContext``.
        change_name: Human-readable name used for plan entry and script files.
        requires: Zero or more change identifiers this change depends on.
        conflicts: Zero or more change identifiers this change conflicts with.
        tags: Optional collection of tag strings applied to the new change.
        note: Optional free-form note stored with the change metadata.
        deploy_path: Optional explicit path for the deploy script template.
        revert_path: Optional explicit path for the revert script template.
        verify_path: Optional explicit path for the verify script template.
        template_name: Name or path of a script template to apply for all script kinds.

    Raises:
        CommandError: If template discovery fails, plan discovery fails, plan parsing
            fails, scripts already exist, or the change name has already been
            recorded in the plan.
    """

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    environment = cli_context.env
    plan_path = resolve_plan_path(
        project_root=project_root,
        override=cli_context.plan_file,
        env=environment,
        missing_plan_message="No plan file found. Run `sqlitch init` before adding changes.",
    )
    quiet = bool(cli_context.quiet)

    # Load configuration for planner identity resolution
    config = resolve_config(
        root_dir=project_root,
        config_root=cli_context.config_root,
        env=environment,
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
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise CommandError(f"Plan file {plan_path} is missing") from exc
    except OSError as exc:  # pragma: no cover - IO failure propagated as command error
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc
    except PlanParseError as exc:
        raise CommandError(str(exc)) from exc

    if plan.has_change(change_name):
        raise CommandError(f'Change "{change_name}" already exists in plan')

    engine_hint = cli_context.engine or plan.default_engine
    try:
        engine_name = canonicalize_engine_name(engine_hint)
    except UnsupportedEngineError as exc:
        raise CommandError(f"Unsupported engine '{engine_hint}'") from exc

    template_dirs = _discover_template_directories(project_root, cli_context.config_root)

    timestamp = _utcnow()
    slug = slugify_change_name(change_name)

    default_deploy = Path("deploy") / f"{slug}.sql"
    default_revert = Path("revert") / f"{slug}.sql"
    default_verify = Path("verify") / f"{slug}.sql"

    deploy_target = _resolve_script_path(project_root, deploy_path, default_deploy)
    revert_target = _resolve_script_path(project_root, revert_path, default_revert)
    verify_target = _resolve_script_path(project_root, verify_path, default_verify)

    _ensure_script_path(deploy_target)
    _ensure_script_path(revert_target)
    _ensure_script_path(verify_target)

    script_map: dict[str, Path] = {
        "deploy": deploy_target,
        "revert": revert_target,
        "verify": verify_target,
    }

    template_context: dict[str, object] = {
        "project": plan.project_name,
        "change": change_name,
        "engine": engine_name,
        "requires": list(requires),
        "conflicts": list(conflicts),
        "tags": list(tags),
    }

    for kind, target in script_map.items():
        template_body = _resolve_template_content(
            kind=kind,
            engine=engine_name,
            template_dirs=template_dirs,
            template_name=template_name,
        )
        rendered = render_template(template_body, template_context)
        target.write_text(rendered, encoding="utf-8")

    change = Change.create(
        name=change_name,
        script_paths=script_map,
        planner=resolve_planner_identity(environment, config),
        planned_at=timestamp,
        notes=note,
        dependencies=tuple(requires) or None,
        conflicts=tuple(conflicts) or None,
        tags=tuple(tags) or None,
    )

    entries = tuple(plan.entries) + (change,)

    write_plan(
        project_name=plan.project_name,
        default_engine=plan.default_engine,
        entries=entries,
        plan_path=plan.file_path,
        syntax_version=plan.syntax_version,
        uri=plan.uri,
    )

    def _echo(message: str) -> None:
        if not quiet:
            click.echo(message)

    _echo(f"Created {_format_display_path(deploy_target, project_root)}")
    _echo(f"Created {_format_display_path(revert_target, project_root)}")
    _echo(f"Created {_format_display_path(verify_target, project_root)}")
    _echo(f'Added "{change_name}" to sqitch.plan')


@register_command("add")
def _register_add(group: click.Group) -> None:
    """Register the add command with the root CLI group."""

    group.add_command(add_command)
