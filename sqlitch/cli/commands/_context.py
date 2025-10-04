"""Shared CLI context helpers used by command implementations."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

import click

from . import CommandError

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from ..main import CLIContext


_CLI_CONTEXT_META_KEY = "sqlitch_cli_context"


def require_cli_context(ctx: click.Context) -> CLIContext:
    """Return the prepared :class:`CLIContext` from ``ctx``.

    Raises:
        CommandError: If the Click context has not been initialised by the
            top-level command group.
    """

    context = _context_from_obj(ctx.obj)
    if context is not None:
        return context

    context = _context_from_meta(ctx)
    if context is not None:
        return context

    raise CommandError("CLI context is not initialised")


def _context_from_obj(obj: object | None) -> CLIContext | None:
    if obj is None:
        return None
    if _is_cli_context_like(obj):
        return cast("CLIContext", obj)
    return None


def _context_from_meta(ctx: click.Context) -> CLIContext | None:
    current: click.Context | None = ctx
    while current is not None:
        candidate = current.meta.get(_CLI_CONTEXT_META_KEY)
        context = _context_from_obj(candidate)
        if context is not None:
            return context
        current = current.parent
    return None


def _is_cli_context_like(obj: object) -> bool:
    required_attributes = (
        "project_root",
        "config_root",
        "env",
        "log_config",
        "quiet",
    )
    return all(hasattr(obj, attribute) for attribute in required_attributes)


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
