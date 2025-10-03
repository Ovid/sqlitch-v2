"""Implementation of the ``sqlitch deploy`` command."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import click

from sqlitch.plan.model import Change, Plan
from sqlitch.plan.parser import PlanParseError, parse_plan

from . import CommandError, register_command
from ._context import (
    environment_from,
    plan_override_from,
    project_root_from,
    quiet_mode_enabled,
    require_cli_context,
)
from ._plan_utils import resolve_plan_path

__all__ = ["deploy_command"]


@dataclass(frozen=True, slots=True)
class _DeployRequest:
    project_root: Path
    env: Mapping[str, str]
    plan_path: Path
    plan: Plan
    target: str
    to_change: str | None
    to_tag: str | None
    log_only: bool
    quiet: bool


@click.command("deploy")
@click.option("--target", "target_option", help="Deployment target alias or URI.")
@click.option("--to-change", "to_change", help="Deploy through the specified change (inclusive).")
@click.option("--to-tag", "to_tag", help="Deploy through the specified tag (inclusive).")
@click.option(
    "--log-only",
    is_flag=True,
    help="Show the deployment actions without executing any scripts.",
)
@click.pass_context
def deploy_command(
    ctx: click.Context,
    *,
    target_option: str | None,
    to_change: str | None,
    to_tag: str | None,
    log_only: bool,
) -> None:
    """Deploy pending plan changes to the requested target."""

    cli_context = require_cli_context(ctx)
    project_root = project_root_from(ctx)
    env = environment_from(ctx)
    plan_override = plan_override_from(ctx)

    target = _resolve_target(target_option, cli_context.target)

    request = _build_request(
        project_root=project_root,
        env=env,
        plan_override=plan_override,
        to_change=to_change,
        to_tag=to_tag,
        target=target,
        log_only=log_only,
        quiet=quiet_mode_enabled(ctx),
    )

    _execute_deploy(request)


def _build_request(
    *,
    project_root: Path,
    env: Mapping[str, str],
    plan_override: Path | None,
    to_change: str | None,
    to_tag: str | None,
    target: str,
    log_only: bool,
    quiet: bool,
) -> _DeployRequest:
    if to_change and to_tag:
        raise CommandError("Cannot combine --to-change and --to-tag filters.")

    plan_path = _resolve_plan_path(project_root=project_root, override=plan_override, env=env)
    plan = _load_plan(plan_path)

    return _DeployRequest(
        project_root=project_root,
        env=env,
        plan_path=plan_path,
        plan=plan,
        target=target,
        to_change=to_change,
        to_tag=to_tag,
        log_only=log_only,
        quiet=quiet,
    )


def _execute_deploy(request: _DeployRequest) -> None:
    changes = _select_changes(
        plan=request.plan,
        to_change=request.to_change,
        to_tag=request.to_tag,
    )

    if request.log_only:
        _render_log_only_deploy(request, changes)
        return

    raise CommandError("Deployment execution is not yet implemented; rerun with --log-only for now.")


def _resolve_target(target_option: str | None, configured_target: str | None) -> str:
    target = target_option or configured_target
    if not target:
        raise CommandError("A deployment target must be provided via --target or configuration.")
    return target


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
        missing_plan_message="Cannot read plan file sqlitch.plan",
    )


def _load_plan(plan_path: Path) -> Plan:
    try:
        return parse_plan(plan_path)
    except (PlanParseError, ValueError) as exc:  # pragma: no cover - delegated to parser tests
        raise CommandError(str(exc)) from exc
    except OSError as exc:  # pragma: no cover - IO failures surfaced to the CLI user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _select_changes(
    *,
    plan: Plan,
    to_change: str | None,
    to_tag: str | None,
) -> tuple[Change, ...]:
    changes = plan.changes
    if not changes:
        return ()

    if to_change:
        try:
            index = next(i for i, change in enumerate(changes) if change.name == to_change)
        except StopIteration as exc:
            raise CommandError(f"Plan does not contain change '{to_change}'.") from exc
        return changes[: index + 1]

    if to_tag:
        try:
            tag_entry = next(tag for tag in plan.tags if tag.name == to_tag)
        except StopIteration as exc:
            raise CommandError(f"Plan does not contain tag '{to_tag}'.") from exc
        return _select_changes(plan=plan, to_change=tag_entry.change_ref, to_tag=None)

    return changes


def _render_log_only_deploy(request: _DeployRequest, changes: Sequence[Change]) -> None:
    emitter = _build_emitter(request.quiet)

    emitter(
        f"Deploying plan '{request.plan.project_name}' to target '{request.target}' (log-only)."
    )

    if not changes:
        emitter("No changes available for deployment.")
        emitter("Log-only run; no database changes were applied.")
        return

    for change in changes:
        emitter(f"Would deploy change {change.name}")

    emitter("Log-only run; no database changes were applied.")


def _build_emitter(quiet: bool) -> Callable[[str], None]:
    def _emit(message: str) -> None:
        if not quiet:
            click.echo(message)

    return _emit


@register_command("deploy")
def _register_deploy(group: click.Group) -> None:
    """Attach the deploy command to the root Click group."""

    group.add_command(deploy_command)
