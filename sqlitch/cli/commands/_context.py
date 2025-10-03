"""Shared CLI context helpers used by command implementations."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import click

from ..main import CLIContext
from . import CommandError


def require_cli_context(ctx: click.Context) -> CLIContext:
    """Return the prepared :class:`CLIContext` from ``ctx``.

    Raises:
        CommandError: If the Click context has not been initialised by the
            top-level command group.
    """

    obj = ctx.obj
    if not isinstance(obj, CLIContext):
        raise CommandError("CLI context is not initialised")
    return obj


def project_root_from(ctx: click.Context) -> Path:
    """Return the project root associated with ``ctx``."""

    return require_cli_context(ctx).project_root


def environment_from(ctx: click.Context) -> Mapping[str, str]:
    """Return the environment mapping associated with ``ctx``."""

    return require_cli_context(ctx).env


def plan_override_from(ctx: click.Context) -> Path | None:
    """Return the explicit plan file override if one was provided."""

    return require_cli_context(ctx).plan_file


def config_root_from(ctx: click.Context) -> Path:
    """Return the configuration root directory associated with ``ctx``."""

    return require_cli_context(ctx).config_root


def quiet_mode_enabled(ctx: click.Context) -> bool:
    """Return whether the command should suppress informational output."""

    return bool(require_cli_context(ctx).quiet)
