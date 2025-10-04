"""Implementation of the ``sqlitch bundle`` command."""

from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

import click

from . import CommandError, register_command
from ._context import environment_from, plan_override_from, project_root_from, quiet_mode_enabled
from ._plan_utils import resolve_plan_path

__all__ = ["bundle_command"]

_DEFAULT_BUNDLE_DIRECTORY = Path("bundle")
_SCRIPT_DIRECTORIES: tuple[str, ...] = ("deploy", "revert", "verify")


@click.command("bundle")
@click.argument("directory", type=click.Path(file_okay=False, path_type=Path), required=False)
@click.option(
    "--dest",
    "dest_option",
    type=click.Path(file_okay=False, path_type=Path),
    help="Destination directory for the bundle output.",
)
@click.option("--no-plan", is_flag=True, help="Skip copying the plan file into the bundle.")
@click.pass_context
def bundle_command(
    ctx: click.Context,
    directory: Path | None,
    *,
    dest_option: Path | None,
    no_plan: bool,
) -> None:
    """Bundle the current project for distribution."""

    project_root = project_root_from(ctx)
    env = environment_from(ctx)
    plan_override = plan_override_from(ctx)
    quiet = quiet_mode_enabled(ctx)

    destination = _determine_destination(
        project_root=project_root,
        directory_argument=directory,
        dest_option=dest_option,
        env=env,
    )

    _create_destination(destination)

    if not no_plan:
        plan_path = _resolve_plan_path(
            project_root=project_root,
            override=plan_override,
            env=env,
        )
        _copy_file(plan_path, destination / plan_path.name)

    for name in _SCRIPT_DIRECTORIES:
        source_directory = project_root / name
        if not source_directory.exists():
            continue
        _copy_directory(source_directory, destination / name)

    if not quiet:
        click.echo(f"Bundled project to {_format_display_path(destination, project_root)}")


def _determine_destination(
    *,
    project_root: Path,
    directory_argument: Path | None,
    dest_option: Path | None,
    env: Mapping[str, str],
) -> Path:
    candidates: tuple[Path | str, ...] = tuple(
        candidate
        for candidate in (
            dest_option,
            directory_argument,
            env.get("SQLITCH_BUNDLE_DIR"),
            env.get("SQITCH_BUNDLE_DIR"),
            _DEFAULT_BUNDLE_DIRECTORY,
        )
        if candidate is not None
    )

    raw_destination = candidates[0]
    as_path = Path(raw_destination) if not isinstance(raw_destination, Path) else raw_destination
    return as_path if as_path.is_absolute() else project_root / as_path


def _create_destination(destination: Path) -> None:
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:  # pragma: no cover - surfaced to the CLI user
        raise CommandError(f"Cannot create directory {destination}") from exc


def _resolve_plan_path(
    *,
    project_root: Path,
    override: Path | None,
    env: Mapping[str, str],
) -> Path:
    return resolve_plan_path(
        project_root=project_root,
        override=override,
        env=env,
        	missing_plan_message="Cannot read plan file sqitch.plan",
    )


def _copy_file(source: Path, destination: Path) -> None:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    except OSError as exc:  # pragma: no cover - surfaced to the CLI user
        raise CommandError(f"Failed to copy {source} to {destination}: {exc}") from exc


def _copy_directory(source: Path, destination: Path) -> None:
    try:
        shutil.copytree(source, destination, dirs_exist_ok=True)
    except OSError as exc:  # pragma: no cover - surfaced to the CLI user
        raise CommandError(f"Failed to copy directory {source} to {destination}: {exc}") from exc


def _format_display_path(path: Path, project_root: Path) -> str:
    try:
        relative = path.relative_to(project_root)
        return relative.as_posix()
    except ValueError:
        return os.path.relpath(path, project_root).replace(os.sep, "/")


@register_command("bundle")
def _register_bundle(group: click.Group) -> None:
    """Attach the bundle command to the root Click group."""

    group.add_command(bundle_command)
