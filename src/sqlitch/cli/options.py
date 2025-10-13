"""Shared CLI option declarations and logging configuration helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, TypeVar
from uuid import uuid4

import click

F = TypeVar("F", bound=Callable[..., Any])

RUN_IDENTIFIER_ENV_VAR = "SQLITCH_RUN_ID"
"""Environment variable that forces a specific run identifier for logging."""

DEFAULT_LOG_DESTINATION = "stderr"
"""Default stderr destination used for structured logging sinks."""


@dataclass(frozen=True, slots=True)
class LogConfiguration:
    """Immutable structured logging configuration for a CLI invocation.

    Attributes:
        run_identifier: Unique identifier attached to every log record.
        verbosity: Count of ``-v`` flags supplied by the user.
        quiet: Indicates whether quiet mode suppresses non-error output.
        json_mode: Whether structured JSON output has been requested globally.
        destination: Where log output should be directed (defaults to stderr).
        rich_markup: Controls whether Rich markup should be enabled.
        rich_tracebacks: Controls whether Rich traceback formatting is enabled.
        structured_logging_enabled: Indicates whether structured log sinks should emit
            records to stderr/stdout (derived from verbosity and json mode).
    """

    run_identifier: str
    verbosity: int
    quiet: bool
    json_mode: bool
    destination: str = DEFAULT_LOG_DESTINATION
    rich_markup: bool = True
    rich_tracebacks: bool = False

    @property
    def level(self) -> str:
        """Return the effective log level name derived from verbosity flags."""

        if self.quiet:
            return "ERROR"
        if self.verbosity >= 2:
            return "TRACE"
        if self.verbosity >= 1:
            return "DEBUG"
        return "INFO"

    def as_dict(self) -> dict[str, object]:
        """Return a serialisable representation of the configuration."""

        return {
            "run_id": self.run_identifier,
            "verbosity": self.verbosity,
            "quiet": self.quiet,
            "json": self.json_mode,
            "level": self.level,
            "destination": self.destination,
            "rich_markup": self.rich_markup,
            "rich_tracebacks": self.rich_tracebacks,
            "structured_logging": self.structured_logging_enabled,
        }

    @property
    def structured_logging_enabled(self) -> bool:
        """Return whether structured log sinks should emit console/JSON payloads."""

        return self.json_mode or self.verbosity > 0


def generate_run_identifier() -> str:
    """Return a new unique identifier for the current CLI invocation."""

    return uuid4().hex


@dataclass(frozen=True, slots=True)
class CredentialOverrides:
    """Credential values supplied via CLI flags prior to precedence resolution."""

    username: str | None = None
    password: str | None = None

    def as_dict(self) -> dict[str, str]:
        """Return a dictionary containing defined credential values."""

        data: dict[str, str] = {}
        if self.username is not None:
            data["username"] = self.username
        if self.password is not None:
            data["password"] = self.password
        return data


def build_log_configuration(
    *,
    verbosity: int,
    quiet: bool,
    json_mode: bool,
    env: Mapping[str, str] | None = None,
) -> LogConfiguration:
    """Build a :class:`LogConfiguration` from global CLI flag values.

    Args:
        verbosity: Number of times the ``--verbose`` flag was supplied.
        quiet: Whether quiet mode was enabled for the invocation.
        json_mode: Whether JSON output was requested globally.
        env: Optional environment mapping used to honour run identifier overrides.

    Returns:
        A :class:`LogConfiguration` instance suitable for downstream logging.
    """

    mapping = env or {}
    run_identifier = mapping.get(RUN_IDENTIFIER_ENV_VAR, generate_run_identifier())
    return LogConfiguration(
        run_identifier=run_identifier,
        verbosity=verbosity,
        quiet=quiet,
        json_mode=json_mode,
    )


def global_output_options(func: F) -> F:
    """Apply shared global output flags to a Click command callback."""

    func = click.option(
        "--json",
        "json_mode",
        is_flag=True,
        help="Emit structured JSON output instead of human-readable text.",
    )(func)
    func = click.option(
        "-q",
        "--quiet",
        is_flag=True,
        help="Suppress non-error output for scripts and automation use.",
    )(func)
    func = click.option(
        "-v",
        "--verbose",
        count=True,
        help="Increase output verbosity. May be specified multiple times.",
    )(func)
    return func


def global_sqitch_options(func: F) -> F:
    """Apply global Sqitch-compatible options to a Click command.

    These options are accepted by all Sqitch commands and should be
    available on all SQLitch commands for parity.
    """
    func = click.option(
        "-C",
        "--chdir",
        "chdir_path",
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
        help="Change to directory before executing command.",
        expose_value=False,  # Handled at group level
        is_eager=True,
    )(func)
    func = click.option(
        "--no-pager",
        is_flag=True,
        help="Do not pipe output into a pager.",
        expose_value=False,  # Stored in context
        is_eager=True,
    )(func)
    # Note: --quiet and --verbose are already in global_output_options
    return func


__all__ = [
    "RUN_IDENTIFIER_ENV_VAR",
    "DEFAULT_LOG_DESTINATION",
    "LogConfiguration",
    "CredentialOverrides",
    "build_log_configuration",
    "generate_run_identifier",
    "global_output_options",
    "global_sqitch_options",
]
