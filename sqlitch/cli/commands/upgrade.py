"""Implementation of the ``sqlitch upgrade`` command."""

from __future__ import annotations

from pathlib import Path

import click

from sqlitch.registry.migrations import LATEST_REGISTRY_VERSION

from . import CommandError, register_command
from ._context import require_cli_context
from ..options import global_output_options, global_sqitch_options

__all__ = ["upgrade_command"]


@click.command("upgrade")
@click.argument("target_args", nargs=-1)
@click.option("--target", help="Target to upgrade.")
@click.option("--registry", help="Registry URI.")
@click.option("--log-only", is_flag=True, help="Only log what would be done.")
@global_sqitch_options
@global_output_options
@click.pass_context
def upgrade_command(
    ctx: click.Context,
    target_args: tuple[str, ...],
    target: str | None,
    registry: str | None,
    log_only: bool,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Update the registry schema to the latest version."""

    require_cli_context(ctx)

    message = (
        "sqlitch upgrade is not implemented yet; registry migrations pending. "
        f"Latest supported version is {LATEST_REGISTRY_VERSION}."
    )
    if log_only:
        click.echo(message)

    raise CommandError(message)


@register_command("upgrade")
def _register_upgrade(group: click.Group) -> None:
    """Register the upgrade command with the root CLI group."""

    group.add_command(upgrade_command)
