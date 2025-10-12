"""Implementation of the ``sqlitch help`` command."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from click import BaseCommand

from ..options import global_output_options, global_sqitch_options
from . import CommandError, register_command
from ._context import quiet_mode_enabled, require_cli_context

__all__ = ["help_command"]


@click.command("help")
@click.option("--usage", "usage_only", is_flag=True, help="Show usage information only.")
@click.option(
    "--man", "man_flag", is_flag=True, help="Display the full manual page (falls back to stdout)."
)
@click.argument("topic", required=False)
@global_sqitch_options
@global_output_options
@click.pass_context
def help_command(
    ctx: click.Context,
    *,
    usage_only: bool,
    man_flag: bool,
    topic: str | None,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Display contextual help output for SQLitch CLI commands.

    Parameters
    ----------
    ctx : click.Context
        Invocation context supplied by Click. Must originate from the SQLitch
        root group so that registry state and global options are available.
    usage_only : bool
        When ``True``, render only the single-line usage string instead of the
        full command help text.
    man_flag : bool
        Indicates whether the user requested the manual page. SQLitch does not
        yet spawn a pager, so the flag currently falls back to standard output
        while maintaining parity with the Sqitch surface area.
    topic : str | None
        Optional command name for which to display help content. If ``None``,
        the root command summary is shown.

    Raises
    ------
    CommandError
        If mutually exclusive flags are combined or the requested topic is not
        registered with the CLI command registry.

    Notes
    -----
    This command respects the global ``--quiet`` flag and suppresses output
    when quiet mode is active.
    """

    require_cli_context(ctx)

    if usage_only and man_flag:
        raise CommandError("--man and --usage cannot be combined.")

    root_ctx = ctx.find_root()
    root_command = root_ctx.command
    text = _render_help(
        ctx=ctx,
        root_ctx=root_ctx,
        root_command=root_command,
        topic=topic,
        usage_only=usage_only,
    )

    # We do not yet spawn a pager; parity fallback prints directly to stdout.
    _emit(ctx, text.rstrip("\n"))


def _render_help(
    *,
    ctx: click.Context,
    root_ctx: click.Context,
    root_command: BaseCommand,
    topic: str | None,
    usage_only: bool,
) -> str:
    if topic is None:
        with click.Context(root_command, info_name=root_command.name) as help_ctx:
            if usage_only:
                return help_ctx.command.get_usage(help_ctx)
            return help_ctx.command.get_help(help_ctx)

    command = root_command.get_command(root_ctx, topic)
    if command is None:
        raise CommandError(f'No help for "{topic}"')

    with click.Context(command, info_name=topic, parent=root_ctx) as topic_ctx:
        if usage_only:
            return topic_ctx.command.get_usage(topic_ctx)
        return topic_ctx.command.get_help(topic_ctx)


def _emit(ctx: click.Context, message: str) -> None:
    if quiet_mode_enabled(ctx):
        return
    click.echo(message)


@register_command("help")
def _register_help(group: click.Group) -> None:
    """Attach the help command to the root Click group.

    Parameters
    ----------
    group : click.Group
        Root command group that aggregates SQLitch subcommands.
    """

    group.add_command(help_command)
