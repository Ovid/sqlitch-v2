"""Command-line entry point for SQLitch."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import click

from sqlitch.config import resolver as config_resolver
from sqlitch.utils.logging import StructuredLogger, create_logger

from .commands import (
    CommandError,
    iter_command_registrars,
    load_commands,
    reset_global_json_mode,
    set_global_json_mode,
)
from .options import LogConfiguration, build_log_configuration, global_output_options

_CLI_CONTEXT_META_KEY = "sqlitch_cli_context"
_CLI_ARGS_META_KEY = "sqlitch_cli_args"
_CLI_SUBCOMMAND_META_KEY = "sqlitch_cli_subcommand"
_CLI_START_TIME_META_KEY = "sqlitch_cli_start_time"


@dataclass(slots=True)
class CLIContext:
    """Resolved execution context shared across CLI commands.

    Attributes:
        project_root: Root directory of the working SQLitch project.
        config_root: User configuration directory resolved from flags or env.
        config_root_overridden: Indicates whether config_root was explicitly set via CLI.
        env: Frozen snapshot of the process environment for deterministic usage.
        engine: Default engine identifier supplied via global options or env.
        target: Default deployment target alias.
        registry: Override for the registry target alias.
        plan_file: Explicit plan file path, if overridden from the default.
        verbosity: Verbosity level where larger values indicate more detail.
        quiet: Indicates whether non-essential output should be suppressed.
        json_mode: Indicates whether structured JSON output has been requested.
        log_config: Default logging configuration for the invocation.
        logger: Structured logger that honors the configured verbosity/quiet settings.
    """

    project_root: Path
    config_root: Path
    config_root_overridden: bool
    env: Mapping[str, str]
    engine: str | None
    target: str | None
    registry: str | None
    plan_file: Path | None
    verbosity: int
    quiet: bool
    json_mode: bool
    log_config: LogConfiguration
    logger: StructuredLogger

    @property
    def run_identifier(self) -> str:
        """Return the unique run identifier assigned to this invocation."""

        return self.log_config.run_identifier


def _build_cli_context(
    *,
    config_root: Path | None,
    engine: str | None,
    target: str | None,
    registry: str | None,
    plan_file: Path | None,
    verbosity: int,
    quiet: bool,
    json_mode: bool,
    env: Mapping[str, str] | None = None,
) -> CLIContext:
    """Return a :class:`CLIContext` assembled from CLI arguments and env vars."""

    environment = MappingProxyType({k: str(v) for k, v in (env or os.environ).items()})
    resolved_config_root = (
        config_root
        if config_root is not None
        else config_resolver.determine_config_root(env=environment)
    )
    config_root_overridden = config_root is not None

    if quiet and verbosity > 0:
        raise CommandError("--quiet cannot be combined with --verbose flags")

    normalized_plan_file = plan_file.resolve() if plan_file is not None else None
    log_config = build_log_configuration(
        verbosity=verbosity,
        quiet=quiet,
        json_mode=json_mode,
        env=environment,
    )
    logger = create_logger(log_config)

    resolved_target = (
        target or environment.get("SQLITCH_TARGET") or environment.get("SQITCH_TARGET")
    )

    return CLIContext(
        project_root=Path.cwd(),
        config_root=resolved_config_root,
        config_root_overridden=config_root_overridden,
        env=environment,
        engine=engine,
        target=resolved_target,
        registry=registry,
        plan_file=normalized_plan_file,
        verbosity=verbosity,
        quiet=quiet,
        json_mode=json_mode,
        log_config=log_config,
        logger=logger,
    )


class SqlitchGroup(click.Group):
    """Custom Click group that emits structured logging events."""

    def invoke(self, ctx: click.Context) -> Any:
        error: BaseException | None = None
        try:
            return super().invoke(ctx)
        except click.ClickException as exc:  # pragma: no cover - exercised in tests via CLI
            error = exc
            raise
        except Exception as exc:  # pragma: no cover - safety net for unexpected failures
            error = exc
            raise
        finally:
            cli_context = _resolve_cli_context(ctx)
            if cli_context is not None:
                logger = cli_context.logger
                payload = _command_payload(ctx, cli_context)

                start_time = ctx.meta.get(_CLI_START_TIME_META_KEY)
                if isinstance(start_time, (int, float)):
                    payload["duration_ms"] = round((time.perf_counter() - start_time) * 1000, 3)

                if error is None:
                    payload["status"] = "success"
                    payload["exit_code"] = 0
                    logger.info("command.complete", message="Command completed", payload=payload)
                else:
                    payload["status"] = "error"
                    payload["error_type"] = type(error).__name__
                    message = str(error)
                    if isinstance(error, click.ClickException):
                        payload["exit_code"] = error.exit_code
                        logger.error("command.error", message=message, payload=payload)
                        logger.info(
                            "command.complete",
                            message="Command aborted",
                            payload=payload,
                        )
                    else:
                        logger.critical("command.error", message=message, payload=payload)


@click.group(
    name="sqlitch",
    context_settings={"help_option_names": ["-h", "--help"]},
    cls=SqlitchGroup,
)
@click.version_option(package_name="sqlitch", prog_name="sqlitch")
@click.option(
    "--config-root",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help=(
        "Override the configuration root directory. Defaults to the value "
        "derived from SQLITCH_CONFIG_ROOT, SQITCH_CONFIG_ROOT, or the user's "
        "standard config location."
    ),
)
@click.option("-e", "--engine", help="Set the default engine for this invocation.")
@click.option(
    "-t",
    "--target",
    help="Set the default deployment target alias for commands that accept one.",
)
@click.option(
    "--registry",
    help="Override the registry target alias when deploying or verifying.",
)
@click.option(
    "--plan-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Use an alternate plan file instead of the default discovery rules.",
)
@click.option(
    "-C",
    "--chdir",
    "chdir_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Change to directory before executing command.",
)
@click.option(
    "--no-pager",
    is_flag=True,
    help="Do not pipe output into a pager.",
)
@global_output_options
@click.pass_context
def main(
    ctx: click.Context,
    *,
    config_root: Path | None,
    engine: str | None,
    target: str | None,
    registry: str | None,
    plan_file: Path | None,
    json_mode: bool,
    verbose: int,
    quiet: bool,
    chdir_path: Path | None,
    no_pager: bool,
) -> None:
    """Top-level SQLitch command group.

    The function resolves global options into a shared context that downstream
    command handlers can consume via :func:`click.get_current_context`.
    """
    token = set_global_json_mode(json_mode)

    def _restore_json_mode() -> None:
        reset_global_json_mode(token)

    ctx.call_on_close(_restore_json_mode)

    # Handle --chdir before any other processing
    if chdir_path:
        os.chdir(chdir_path)

    cli_context = _build_cli_context(
        config_root=config_root,
        engine=engine,
        target=target,
        registry=registry,
        plan_file=plan_file,
        verbosity=verbose,
        quiet=quiet,
        json_mode=json_mode,
    )
    ctx.obj = cli_context
    ctx.meta[_CLI_CONTEXT_META_KEY] = cli_context
    ctx.meta["no_pager"] = no_pager  # Store for commands that need it
    leftover_args = tuple(ctx.args)
    ctx.meta[_CLI_ARGS_META_KEY] = leftover_args
    if leftover_args:
        ctx.meta[_CLI_SUBCOMMAND_META_KEY] = leftover_args[0]
    ctx.meta[_CLI_START_TIME_META_KEY] = time.perf_counter()

    _log_command_start(ctx, cli_context)


def _resolve_cli_context(ctx: click.Context) -> CLIContext | None:
    obj = ctx.obj
    if isinstance(obj, CLIContext):
        return obj

    candidate = ctx.meta.get(_CLI_CONTEXT_META_KEY)
    if isinstance(candidate, CLIContext):
        return candidate
    return None


def _command_payload(ctx: click.Context, cli_context: CLIContext) -> dict[str, Any]:
    argv = list(ctx.meta.get(_CLI_ARGS_META_KEY, ()))
    payload: dict[str, Any] = {
        "command": ctx.command_path,
        "subcommand": ctx.invoked_subcommand or ctx.meta.get(_CLI_SUBCOMMAND_META_KEY),
        "argv": argv,
        "verbosity": cli_context.verbosity,
        "quiet": cli_context.quiet,
        "json": cli_context.json_mode,
    }
    return payload


def _log_command_start(ctx: click.Context, cli_context: CLIContext) -> None:
    payload = _command_payload(ctx, cli_context)
    cli_context.logger.info(
        "command.start",
        message=f"Starting {payload['command']}",
        payload=payload,
    )


load_commands()
for registrar in iter_command_registrars():
    registrar(main)


if __name__ == "__main__":
    main()
