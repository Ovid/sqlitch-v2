"""Implementation of the ``sqlitch init`` command."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

import click

from sqlitch.plan.formatter import write_plan
from sqlitch.utils.fs import ArtifactConflictError, resolve_config_file, resolve_plan_file

from . import CommandError, register_command
from ._context import require_cli_context

__all__ = ["init_command"]

_ENGINE_ALIASES: dict[str, str] = {
    "postgres": "pg",
    "postgresql": "pg",
}

_ENGINE_DEFAULTS: dict[str, dict[str, str]] = {
    "sqlite": {"target": "db:sqlite:", "registry": "sqlitch", "client": "sqlite3"},
    "pg": {"target": "db:pg:", "registry": "sqlitch", "client": "psql"},
    "mysql": {"target": "db:mysql:", "registry": "sqlitch", "client": "mysql"},
}

_TEMPLATE_CONTENT: dict[str, str] = {
    "deploy": (
        "-- Deploy [% project %]:[% change %] to [% engine %]\n"
        "[% FOREACH item IN requires -%]\n"
        "-- requires: [% item %]\n"
        "[% END -%]\n"
        "[% FOREACH item IN conflicts -%]\n"
        "-- conflicts: [% item %]\n"
        "[% END -%]\n\n"
        "BEGIN;\n\n"
        "-- XXX Add DDLs here.\n\n"
        "COMMIT;\n"
    ),
    "revert": (
        "-- Revert [% project %]:[% change %] from [% engine %]\n\n"
        "BEGIN;\n\n"
        "-- XXX Add DDLs here.\n\n"
        "COMMIT;\n"
    ),
    "verify": (
        "-- Verify [% project %]:[% change %] on [% engine %]\n\n"
        "BEGIN;\n\n"
        "-- XXX Add verifications here.\n\n"
        "ROLLBACK;\n"
    ),
}


@click.command("init")
@click.argument("project_name", required=False)
@click.option("-e", "--engine", "engine_option", help="Set the default engine for the project.")
@click.option(
    "--top-dir",
    "top_dir_option",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Set the top-level directory containing deploy/revert/verify scripts.",
)
@click.option(
    "--plan-file",
    "plan_file_option",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Override the plan file path for the project.",
)
@click.option("--target", "target_option", help="Default deployment target alias recorded in config.")
@click.pass_context
def init_command(
    ctx: click.Context,
    project_name: str | None,
    engine_option: str | None,
    top_dir_option: Path | None,
    plan_file_option: Path | None,
    target_option: str | None,
) -> None:
    """Initialize a new SQLitch project mirroring Sqitch scaffolding."""

    cli_context = require_cli_context(ctx)
    project_root = cli_context.project_root
    environment = cli_context.env
    quiet = bool(cli_context.quiet)
    global_plan_override = cli_context.plan_file
    context_engine = cli_context.engine
    context_target = cli_context.target

    project = _determine_project_name(project_name, project_root)
    engine = _normalize_engine(engine_option or context_engine)
    target = target_option or context_target or _ENGINE_DEFAULTS[engine]["target"]

    top_dir_path, top_dir_display = _determine_top_dir(project_root, top_dir_option, environment)
    plan_path = _determine_plan_path(
        project_root=project_root,
        plan_option=plan_file_option,
        global_override=global_plan_override,
        env=environment,
    )
    config_path = _determine_config_path(project_root)

    _validate_absent(plan_path, "Plan file")
    _validate_absent(config_path, "Config file")
    deploy_dir = top_dir_path / "deploy"
    revert_dir = top_dir_path / "revert"
    verify_dir = top_dir_path / "verify"
    for directory in (deploy_dir, revert_dir, verify_dir):
        _validate_directory_absent(directory)

    templates_root = project_root / "etc" / "templates"
    _validate_templates_absent(templates_root)

    top_dir_path.mkdir(parents=True, exist_ok=True)
    for directory in (deploy_dir, revert_dir, verify_dir):
        directory.mkdir(parents=True, exist_ok=False)

    template_paths = _create_templates(templates_root, engine)

    write_plan(
        project_name=project,
        default_engine=engine,
        entries=(),
        plan_path=plan_path,
    )

    config_content = _render_config(
        engine=engine,
        plan_path=plan_path,
        project_root=project_root,
        top_dir_display=top_dir_display,
        target=target,
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content, encoding="utf-8")

    messages = [
        f"Created config file {_format_display_path(config_path, project_root)}",
        f"Created plan file {_format_display_path(plan_path, project_root)}",
        f"Created deploy directory {_format_display_path(deploy_dir, project_root)}",
        f"Created revert directory {_format_display_path(revert_dir, project_root)}",
        f"Created verify directory {_format_display_path(verify_dir, project_root)}",
    ]
    if template_paths:
        messages.append(
            f"Created templates under {_format_display_path(templates_root, project_root)}"
        )

    if not quiet:
        for message in messages:
            click.echo(message)


@register_command("init")
def _register_init(group: click.Group) -> None:
    """Register the init command with the root CLI group."""

    group.add_command(init_command)


def _determine_project_name(project_name: str | None, project_root: Path) -> str:
    if project_name:
        return project_name
    if project_root.name:
        return project_root.name
    return "sqlitch"


def _normalize_engine(engine: str | None) -> str:
    if not engine:
        return "sqlite"
    lowered = engine.strip().lower()
    canonical = _ENGINE_ALIASES.get(lowered, lowered)
    if canonical not in _ENGINE_DEFAULTS:
        supported = ", ".join(sorted(_ENGINE_DEFAULTS))
        raise CommandError(f"Unsupported engine '{engine}'. Supported engines: {supported}")
    return canonical


def _determine_top_dir(
    project_root: Path, top_dir_option: Path | None, env: Mapping[str, str]
) -> tuple[Path, str]:
    if top_dir_option is not None:
        display = top_dir_option.as_posix()
        path = top_dir_option if top_dir_option.is_absolute() else project_root / top_dir_option
        return path, display

    env_value = env.get("SQLITCH_TOP_DIR")
    if env_value:
        env_path = Path(env_value)
        display = env_path.as_posix()
        path = env_path if env_path.is_absolute() else project_root / env_path
        return path, display

    return project_root, "."


def _determine_plan_path(
    *,
    project_root: Path,
    plan_option: Path | None,
    global_override: Path | None,
    env: Mapping[str, str],
) -> Path:
    if plan_option is not None:
        return plan_option if plan_option.is_absolute() else project_root / plan_option

    if global_override is not None:
        return global_override

    env_value = env.get("SQITCH_PLAN_FILE") or env.get("SQLITCH_PLAN_FILE")
    if env_value:
        env_path = Path(env_value)
        return env_path if env_path.is_absolute() else project_root / env_path

    try:
        resolution = resolve_plan_file(project_root)
    except ArtifactConflictError as exc:  # pragma: no cover - exercised in integration tests
        raise CommandError(str(exc)) from exc

    if resolution.path is not None:
        return resolution.path

    return project_root / "sqlitch.plan"


def _determine_config_path(project_root: Path) -> Path:
    try:
        resolution = resolve_config_file(project_root)
    except ArtifactConflictError as exc:  # pragma: no cover - integration coverage
        raise CommandError(str(exc)) from exc

    if resolution.path is not None:
        return resolution.path

    return project_root / "sqlitch.conf"


def _validate_absent(path: Path, label: str) -> None:
    if path.exists():
        raise CommandError(f"{label} {path} already exists")


def _validate_directory_absent(path: Path) -> None:
    if path.exists():
        raise CommandError(f"Directory {path} already exists")


def _validate_templates_absent(templates_root: Path) -> None:
    if templates_root.exists():
        raise CommandError(f"Templates directory {templates_root} already exists")


def _create_templates(templates_root: Path, engine: str) -> tuple[Path, ...]:
    templates_root.mkdir(parents=True, exist_ok=False)

    created: list[Path] = []
    for kind, content in _TEMPLATE_CONTENT.items():
        target_dir = templates_root / kind
        target_dir.mkdir(exist_ok=False)
        template_path = target_dir / f"{engine}.tmpl"
        template_path.write_text(content, encoding="utf-8")
        created.append(template_path)
    return tuple(created)


def _render_config(
    *,
    engine: str,
    plan_path: Path,
    project_root: Path,
    top_dir_display: str,
    target: str,
) -> str:
    defaults = _ENGINE_DEFAULTS.get(engine, {})
    registry = defaults.get("registry", "sqlitch")
    client = defaults.get("client")

    plan_display = _format_display_path(plan_path, project_root)

    lines = ["[core]", f"    engine = {engine}", f"    # plan_file = {plan_display}"]
    lines.append(f"    # top_dir = {top_dir_display}")

    engine_section_header = f"# [engine \"{engine}\"]"
    lines.extend(["", engine_section_header, f"    # target = {target}", f"    # registry = {registry}"])
    if client:
        lines.append(f"    # client = {client}")

    lines.extend(["", "# [user]", "    # name = ", "    # email = "])
    return "\n".join(lines) + "\n"


def _format_display_path(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return os.path.relpath(path, project_root).replace(os.sep, "/")