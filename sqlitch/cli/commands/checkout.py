"""Implementation of the ``sqlitch checkout`` command."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import click

from . import CommandError, register_command
from ._context import (
    environment_from,
    plan_override_from,
    project_root_from,
    quiet_mode_enabled,
    require_cli_context,
)
from ._plan_utils import resolve_plan_path

__all__ = ["checkout_command"]


@dataclass(frozen=True, slots=True)
class _CheckoutRequest:
    project_root: Path
    env: Mapping[str, str]
    plan_path: Path
    target: str
    mode: str
    to_change: str | None
    log_only: bool
    vcs_command: str
    quiet: bool


@click.command("checkout")
@click.option("--target", "target_option", help="Deployment target alias or URI.")
@click.option(
    "--mode",
    "mode",
    default="latest",
    show_default=True,
    help="Checkout mode (latest, tag:<tag>, change:<change>).",
)
@click.option("--to-change", "to_change", help="Checkout through the specified change (inclusive).")
@click.option("--log-only", is_flag=True, help="Describe the checkout pipeline without executing it.")
@click.pass_context
def checkout_command(
    ctx: click.Context,
    *,
    target_option: str | None,
    mode: str,
    to_change: str | None,
    log_only: bool,
) -> None:
    """Coordinate revert, VCS checkout, and redeploy operations."""

    cli_context = require_cli_context(ctx)
    project_root = project_root_from(ctx)
    env = environment_from(ctx)
    plan_override = plan_override_from(ctx)

    target = _resolve_target(target_option, cli_context.target)
    vcs_command = _resolve_vcs_command(env)

    request = _build_request(
        project_root=project_root,
        env=env,
        plan_override=plan_override,
        target=target,
        mode=mode,
        to_change=to_change,
        log_only=log_only,
        vcs_command=vcs_command,
        quiet=quiet_mode_enabled(ctx),
    )

    _execute_checkout(request)


def _build_request(
    *,
    project_root: Path,
    env: Mapping[str, str],
    plan_override: Path | None,
    target: str,
    mode: str,
    to_change: str | None,
    log_only: bool,
    vcs_command: str,
    quiet: bool,
) -> _CheckoutRequest:
    plan_path = _resolve_plan_path(project_root=project_root, override=plan_override, env=env)

    return _CheckoutRequest(
        project_root=project_root,
        env=env,
        plan_path=plan_path,
        target=target,
        mode=mode,
        to_change=to_change,
        log_only=log_only,
        vcs_command=vcs_command,
        quiet=quiet,
    )


def _execute_checkout(request: _CheckoutRequest) -> None:
    emitter = _build_emitter(request.quiet)

    emitter(
        f"Would revert target '{request.target}' using mode '{request.mode}'"
        + (f" to change '{request.to_change}'" if request.to_change else "")
    )
    emitter(f"Would run VCS command: {request.vcs_command}")
    emitter(f"Would deploy pending changes to target '{request.target}'")

    if request.log_only:
        emitter("Log-only run; no database changes were applied.")
        return

    raise CommandError(
        "Checkout execution is not yet implemented; rerun with --log-only for now."
    )


def _resolve_target(target_option: str | None, configured_target: str | None) -> str:
    target = target_option or configured_target
    if not target:
        raise CommandError("A deployment target must be provided via --target or configuration.")
    return target


def _resolve_vcs_command(env: Mapping[str, str]) -> str:
    command = (
        env.get("SQLITCH_VCS_COMMAND")
        or env.get("SQLITCH_CHECKOUT_COMMAND")
        or env.get("SQITCH_VCS_COMMAND")
        or env.get("SQITCH_CHECKOUT_COMMAND")
    )
    if not command:
        raise CommandError("No VCS configured for checkout operations.")
    return command


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


def _build_emitter(quiet: bool) -> Callable[[str], None]:
    def _emit(message: str) -> None:
        if not quiet:
            click.echo(message)

    return _emit


@register_command("checkout")
def _register_checkout(group: click.Group) -> None:
    """Attach the checkout command to the root Click group."""

    group.add_command(checkout_command)
