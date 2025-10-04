"""Implementation of the ``sqlitch rebase`` command."""

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

__all__ = ["rebase_command"]


@dataclass(frozen=True, slots=True)
class _RebaseRequest:
    project_root: Path
    env: Mapping[str, str]
    plan_path: Path
    plan: Plan
    target: str
    onto: str | None
    from_ref: str | None
    mode: str
    log_only: bool
    quiet: bool


@click.command("rebase")
@click.option("--target", "target_option", help="Deployment target alias or URI.")
@click.option("--onto", "onto_ref", help="Rebase onto the specified change or tag.")
@click.option("--from", "from_ref", help="Redeploy starting from the specified change or tag.")
@click.option(
    "--mode",
    type=click.Choice(("latest", "all"), case_sensitive=False),
    default="latest",
    show_default=True,
    help="Control how many deployed changes are considered when determining drift.",
)
@click.option(
    "--log-only",
    is_flag=True,
    help="Show the rebase actions without executing any scripts.",
)
@click.pass_context
def rebase_command(
    ctx: click.Context,
    *,
    target_option: str | None,
    onto_ref: str | None,
    from_ref: str | None,
    mode: str,
    log_only: bool,
) -> None:
    """Rebase deployed plan changes to align with the current plan state."""

    cli_context = require_cli_context(ctx)
    project_root = project_root_from(ctx)
    env = environment_from(ctx)
    plan_override = plan_override_from(ctx)

    target = _resolve_target(target_option, cli_context.target)

    request = _build_request(
        project_root=project_root,
        env=env,
        plan_override=plan_override,
        target=target,
        onto_ref=onto_ref,
        from_ref=from_ref,
        mode=mode.lower(),
        log_only=log_only,
        quiet=quiet_mode_enabled(ctx),
    )

    _execute_rebase(request)


def _build_request(
    *,
    project_root: Path,
    env: Mapping[str, str],
    plan_override: Path | None,
    target: str,
    onto_ref: str | None,
    from_ref: str | None,
    mode: str,
    log_only: bool,
    quiet: bool,
) -> _RebaseRequest:
    plan_path = _resolve_plan_path(project_root=project_root, override=plan_override, env=env)
    plan = _load_plan(plan_path)

    return _RebaseRequest(
        project_root=project_root,
        env=env,
        plan_path=plan_path,
        plan=plan,
        target=target,
        onto=onto_ref,
        from_ref=from_ref,
        mode=mode,
        log_only=log_only,
        quiet=quiet,
    )


def _execute_rebase(request: _RebaseRequest) -> None:
    reverts, redeploys = _plan_rebase_actions(
        plan=request.plan,
        onto_ref=request.onto,
        from_ref=request.from_ref,
    )

    if request.log_only:
        _render_log_only_rebase(request, reverts, redeploys)
        return

    raise CommandError("Rebase execution is not yet implemented; rerun with --log-only for now.")


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
        missing_plan_message="Cannot read plan file sqitch.plan",
    )


def _load_plan(plan_path: Path) -> Plan:
    try:
        return parse_plan(plan_path)
    except (PlanParseError, ValueError) as exc:  # pragma: no cover - delegated to parser tests
        raise CommandError(str(exc)) from exc
    except OSError as exc:  # pragma: no cover - IO failures surfaced to the CLI user
        raise CommandError(f"Unable to read plan file {plan_path}: {exc}") from exc


def _plan_rebase_actions(
    *,
    plan: Plan,
    onto_ref: str | None,
    from_ref: str | None,
) -> tuple[tuple[Change, ...], tuple[Change, ...]]:
    changes = plan.changes
    if not changes:
        return (), ()

    start_revert_index = _resolve_reference_index(plan, onto_ref) if onto_ref else 0
    revert_changes = changes[start_revert_index:]

    if from_ref:
        from_index = _resolve_reference_index(plan, from_ref)
    else:
        from_index = start_revert_index

    start_index = max(from_index, start_revert_index, 0)
    redeploy_changes = changes[start_index:]

    return tuple(revert_changes), tuple(redeploy_changes)


def _resolve_reference_index(plan: Plan, reference: str) -> int:
    change_indexes = {change.name: index for index, change in enumerate(plan.changes)}
    if reference in change_indexes:
        return change_indexes[reference]

    for tag in plan.tags:
        if tag.name == reference:
            try:
                return change_indexes[tag.change_ref]
            except KeyError as exc:
                raise CommandError(
                    f"Tag '{tag.name}' references unknown change '{tag.change_ref}'."
                ) from exc

    raise CommandError(f"Plan does not contain change '{reference}'.")


def _render_log_only_rebase(
    request: _RebaseRequest,
    reverts: Sequence[Change],
    redeploys: Sequence[Change],
) -> None:
    emitter = _build_emitter(request.quiet)

    emitter(f"Rebasing plan '{request.plan.project_name}' on target '{request.target}' (log-only).")

    if not reverts and not redeploys:
        emitter("No changes require rebase.")
        emitter("Log-only run; no database changes were applied.")
        return

    for change in reversed(reverts):
        emitter(f"Would revert change {change.name}")

    for change in redeploys:
        emitter(f"Would deploy change {change.name}")

    emitter("Log-only run; no database changes were applied.")


def _build_emitter(quiet: bool) -> Callable[[str], None]:
    def _emit(message: str) -> None:
        if not quiet:
            click.echo(message)

    return _emit


@register_command("rebase")
def _register_rebase(group: click.Group) -> None:
    """Attach the rebase command to the root Click group."""

    group.add_command(rebase_command)
