"""Command-line entry point for SQLitch."""

from __future__ import annotations

import typing as t

import click


class CLIState(t.Protocol):
    """Placeholder protocol for future CLI state objects."""


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="sqlitch", prog_name="sqlitch")
def main() -> None:
    """Top-level SQLitch command group.

    The full command surface is implemented incrementally. For now, this
    function acts as a thin wrapper so the `sqlitch` executable exists after
    installation. Subcommands will be registered here as they land.
    """


if __name__ == "__main__":
    main()
