"""Registration utilities and shared exceptions for SQLitch CLI commands.

The command surface is built incrementally. This module provides the
infrastructure required to add individual command implementations while keeping
registration deterministic and discoverable. Future command modules import this
package and use :func:`register_command` to hook themselves into the main Click
command group.
"""

from __future__ import annotations

import importlib
import typing as t

import click

CommandRegistrar = t.Callable[[click.Group], None]
"""Callable responsible for attaching a command to the root Click group."""

_COMMAND_REGISTRY: dict[str, CommandRegistrar] = {}
"""Registry mapping command names to their Click registration functions.

The registry lifecycle mirrors the process documented in
``docs/architecture/registry-lifecycle.md``:

* Command modules call :func:`register_command` during import (registration phase).
* :func:`iter_command_registrars` feeds the CLI bootstrap, after which the registry is
  treated as immutable (operational phase).
* Tests that import command modules must call :func:`_clear_registry` during teardown to
  avoid leaking state (test isolation phase).

Command registration is intentionally single-threaded and should complete before any
parallel CLI invocations occur. Do not mutate ``_COMMAND_REGISTRY`` outside the helpers
defined in this module.
"""


class CommandRegistrationError(RuntimeError):
    """Raised when a command registrar cannot be added to the registry."""


class CommandError(click.ClickException):
    """Base error used for user-facing CLI failures.

    The exception extends :class:`click.ClickException` so that Click renders a
    clean error message without a stack trace while still allowing an override of
    the exit code when necessary.

    Args:
        message: Human-friendly description of the failure.
        exit_code: Optional process exit code to report. Defaults to ``1``.
    """

    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def register_command(name: str | None = None) -> t.Callable[[CommandRegistrar], CommandRegistrar]:
    """Decorator that registers a command registrar for later attachment.

    The decorator stores the callable in an internal registry keyed by the
    command name. Actual attachment to the Click group occurs when
    :func:`iter_command_registrars` is consumed by the CLI bootstrapper.

    Args:
        name: Optional explicit command name. When omitted the callable's
            ``__name__`` attribute is used.

    Returns:
        The original callable, enabling decorator stacking.

    Raises:
        CommandRegistrationError: If a registrar has already been recorded for
            the chosen command name.
    """

    def decorator(func: CommandRegistrar) -> CommandRegistrar:
        command_name = name or func.__name__
        if command_name in _COMMAND_REGISTRY:
            raise CommandRegistrationError(f"Command '{command_name}' is already registered.")
        _COMMAND_REGISTRY[command_name] = func
        return func

    return decorator


def add_command(name: str, registrar: CommandRegistrar) -> None:
    """Programmatically register a command registrar.

    This helper mirrors :func:`register_command` for call sites where decorators
    are inconvenient (for instance, in dynamic registration scenarios).
    """

    if name in _COMMAND_REGISTRY:
        raise CommandRegistrationError(f"Command '{name}' is already registered.")
    _COMMAND_REGISTRY[name] = registrar


def iter_command_registrars() -> t.Iterator[CommandRegistrar]:
    """Yield registered command registrar callables in insertion order."""

    yield from _COMMAND_REGISTRY.values()


def load_commands(module_names: t.Iterable[str] | None = None) -> None:
    """Import command modules to populate the registry.

    Args:
        module_names: Iterable of module names (without the package prefix)
            to import. When omitted, the :data:`COMMAND_MODULES` constant is
            used instead.
    """

    names = tuple(module_names) if module_names is not None else COMMAND_MODULES
    for module_name in names:
        importlib.import_module(f"sqlitch.cli.commands.{module_name}")


def _clear_registry() -> None:
    """Reset the registry (intended for use in tests)."""

    _COMMAND_REGISTRY.clear()


COMMAND_MODULES: tuple[str, ...] = (
    "add",
    "bundle",
    "checkout",
    "config",
    "deploy",
    "engine",
    "init",
    "log",
    "help",
    "plan",
    "rebase",
    "rework",
    "revert",
    "show",
    "status",
)
"""Default set of command modules imported by :func:`load_commands`."""


__all__ = [
    "CommandError",
    "CommandRegistrar",
    "CommandRegistrationError",
    "COMMAND_MODULES",
    "add_command",
    "iter_command_registrars",
    "load_commands",
    "register_command",
]
