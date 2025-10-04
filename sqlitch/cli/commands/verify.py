"""Implementation of the ``sqlitch verify`` command."""

from __future__ import annotations

import click

from . import CommandError, register_command
from ._context import require_cli_context

__all__ = ["verify_command"]


@click.command("verify")
@click.option("--target", help="Target to verify against.")
@click.option("--to-change", help="Verify up to this change.")
@click.option("--to-tag", help="Verify up to this tag.")
@click.option("--event", type=click.Choice(["deploy", "revert", "fail"]), help="Event type.")
@click.option("--mode", type=click.Choice(["all", "change", "tag"]), help="Verification mode.")
@click.option("--log-only", is_flag=True, help="Only log what would be done.")
@click.pass_context
def verify_command(
    ctx: click.Context,
    target: str | None,
    to_change: str | None,
    to_tag: str | None,
    event: str | None,
    mode: str | None,
    log_only: bool,
) -> None:
    """Execute verification scripts against deployed changes."""

    require_cli_context(ctx)

    message = "sqlitch verify is not implemented yet; Sqitch parity pending"
    if log_only:
        click.echo(message)

    raise CommandError(message)


@register_command("verify")
def _register_verify(group: click.Group) -> None:
    """Register the verify command with the root CLI group."""

    group.add_command(verify_command)
