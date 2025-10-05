"""Implementation of the ``sqlitch verify`` command."""

from __future__ import annotations

import click

from . import CommandError, register_command
from ._context import require_cli_context
from ..options import global_output_options, global_sqitch_options

__all__ = ["verify_command"]


@click.command("verify")
@click.argument("target_args", nargs=-1)
@click.option("--target", "target_option", help="Target to verify against.")
@click.option("--to-change", help="Verify up to this change.")
@click.option("--to-tag", help="Verify up to this tag.")
@click.option("--event", type=click.Choice(["deploy", "revert", "fail"]), help="Event type.")
@click.option("--mode", type=click.Choice(["all", "change", "tag"]), help="Verification mode.")
@click.option("--log-only", is_flag=True, help="Only log what would be done.")
@global_sqitch_options
@global_output_options
@click.pass_context
def verify_command(
    ctx: click.Context,
    target_args: tuple[str, ...],
    target_option: str | None,
    to_change: str | None,
    to_tag: str | None,
    event: str | None,
    mode: str | None,
    log_only: bool,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Execute verification scripts against deployed changes."""

    require_cli_context(ctx)

    # Resolve target from positional args or --target option
    if target_args and target_option:
        raise CommandError("Provide either a positional target or --target, not both.")
    if len(target_args) > 1:
        raise CommandError("Multiple positional targets are not supported.")

    target = target_args[0] if target_args else target_option

    message = "sqlitch verify is not implemented yet; Sqitch parity pending"
    if log_only:
        click.echo(message)

    raise CommandError(message)


@register_command("verify")
def _register_verify(group: click.Group) -> None:
    """Register the verify command with the root CLI group."""

    group.add_command(verify_command)
