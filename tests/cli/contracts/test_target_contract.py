"""Contract parity tests for ``sqlitch target``."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_target_list_empty(runner: CliRunner) -> None:
    """sqlitch target list shows no targets initially."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "list"])
        assert result.exit_code == 0
        assert "No targets configured." in result.output


def test_target_add_and_list(runner: CliRunner) -> None:
    """sqlitch target add creates a target and list shows it."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(
            main,
            ["target", "add", "prod", "db:sqlite:prod.db", "--engine", "sqlite", "--registry", "db:sqlite:registry.db"],
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "list"])
        assert result.exit_code == 0
    assert "Name\tURI\tEngine\tRegistry" in result.output
    assert "prod\tdb:sqlite:prod.db\tsqlite\tdb:sqlite:registry.db" in result.output


def test_target_add_rejects_duplicates(runner: CliRunner) -> None:
    """Adding the same target twice should error."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db"])
        assert result.exit_code != 0
        assert 'Target "prod" already exists' in result.output


def test_target_show(runner: CliRunner) -> None:
    """sqlitch target show displays target details."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "show", "prod"])
        assert result.exit_code == 0
        assert "db:sqlite:prod.db" in result.output


def test_target_remove(runner: CliRunner) -> None:
    """sqlitch target remove deletes a target."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "remove", "prod"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "list"])
        assert result.exit_code == 0
        assert "prod" not in result.output


def test_target_alter_updates_existing_target(runner: CliRunner) -> None:
    """target alter should update stored attributes."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(
            main,
            ["target", "alter", "prod", "db:sqlite:new.db", "--engine", "pg", "--registry", "db:sqlite:registry.db"],
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "show", "prod"])
        assert result.exit_code == 0
        assert "db:sqlite:new.db" in result.output
        assert "Engine: pg" in result.output
        assert "Registry: db:sqlite:registry.db" in result.output


def test_target_unknown_show_error(runner: CliRunner) -> None:
    """Showing unknown target fails."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "show", "nonexistent"])
        assert result.exit_code != 0
        assert "Unknown target" in result.output


def test_target_remove_unknown_error(runner: CliRunner) -> None:
    """Removing an unknown target should raise a CommandError."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "remove", "ghost"])

    assert result.exit_code != 0
    assert "Unknown target \"ghost\"" in result.output
