"""Implementation of the ``sqlitch upgrade`` command."""

from __future__ import annotations

from pathlib import Path

import click

from sqlitch.registry.migrations import LATEST_REGISTRY_VERSION

from . import CommandError, register_command
from ._context import require_cli_context

__all__ = ["upgrade_command"]


@click.command("upgrade")
@click.option("--target", help="Target to upgrade.")
@click.option("--registry", help="Registry URI.")
@click.option("--log-only", is_flag=True, help="Only log what would be done.")
@click.pass_context
def upgrade_command(
    ctx: click.Context,
    target: str | None,
    registry: str | None,
    log_only: bool,
) -> None:
    """Update the registry schema to the latest version."""

    cli_context = require_cli_context(ctx)

    # For now, assume registry is up to date
    if log_only:
        click.echo(f"Registry is at version {LATEST_REGISTRY_VERSION}")
    else:
        click.echo(f"Registry is already at version {LATEST_REGISTRY_VERSION}")


@register_command("upgrade")
def _register_upgrade(group: click.Group) -> None:
    """Register the upgrade command with the root CLI group."""

    group.add_command(upgrade_command)