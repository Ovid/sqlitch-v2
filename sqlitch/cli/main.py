"""Command-line entry point for SQLitch."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import click

from sqlitch.config import resolver as config_resolver

from .commands import CommandError, iter_command_registrars, load_commands
from .options import LogConfiguration, build_log_configuration, global_output_options

_CLI_CONTEXT_META_KEY = "sqlitch_cli_context"


@dataclass(slots=True)
class CLIContext:
    """Resolved execution context shared across CLI commands.

    Attributes:
        project_root: Root directory of the working SQLitch project.
        config_root: User configuration directory resolved from flags or env.
        env: Frozen snapshot of the process environment for deterministic usage.
        engine: Default engine identifier supplied via global options or env.
        target: Default deployment target alias.
        registry: Override for the registry target alias.
        plan_file: Explicit plan file path, if overridden from the default.
        verbosity: Verbosity level where larger values indicate more detail.
        quiet: Indicates whether non-essential output should be suppressed.
        json_mode: Indicates whether structured JSON output has been requested.
        log_config: Default logging configuration for the invocation.
    """

    project_root: Path
    config_root: Path
    env: Mapping[str, str]
    engine: str | None
    target: str | None
    registry: str | None
    plan_file: Path | None
    verbosity: int
    quiet: bool
    json_mode: bool
    log_config: LogConfiguration

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

    if quiet and verbosity > 0:
        raise CommandError("--quiet cannot be combined with --verbose flags")

    normalized_plan_file = plan_file.resolve() if plan_file is not None else None
    log_config = build_log_configuration(
        verbosity=verbosity,
        quiet=quiet,
        json_mode=json_mode,
        env=environment,
    )

    return CLIContext(
        project_root=Path.cwd(),
        config_root=resolved_config_root,
        env=environment,
        engine=engine,
        target=target,
        registry=registry,
        plan_file=normalized_plan_file,
        verbosity=verbosity,
        quiet=quiet,
        json_mode=json_mode,
        log_config=log_config,
    )


@click.group(name="sqlitch", context_settings={"help_option_names": ["-h", "--help"]})
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
) -> None:
    """Top-level SQLitch command group.

    The function resolves global options into a shared context that downstream
    command handlers can consume via :func:`click.get_current_context`.
    """

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


load_commands()
for registrar in iter_command_registrars():
    registrar(main)


if __name__ == "__main__":
    main()
