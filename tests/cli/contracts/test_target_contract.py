"""Contract parity tests for ``sqlitch target``.

Includes CLI signature contract tests merged from tests/cli/commands/
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_target_list_empty(runner: CliRunner) -> None:
    """sqlitch target list shows no targets initially."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "list"])
        assert result.exit_code == 0
        assert "No targets configured." in result.output


def test_target_add_and_list(runner: CliRunner) -> None:
    """sqlitch target add creates a target and list shows it."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(
            main,
            [
                "target",
                "add",
                "prod",
                "db:sqlite:prod.db",
                "--engine",
                "sqlite",
                "--registry",
                "db:sqlite:registry.db",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "list"])
        assert result.exit_code == 0
    assert "Name\tURI\tEngine\tRegistry" in result.output
    assert "prod\tdb:sqlite:prod.db\tsqlite\tdb:sqlite:registry.db" in result.output


def test_target_add_rejects_duplicates(runner: CliRunner) -> None:
    """Adding the same target twice should error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db"])
        assert result.exit_code != 0
        assert 'Target "prod" already exists' in result.output


def test_target_show(runner: CliRunner) -> None:
    """sqlitch target show displays target details."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "add", "prod", "db:sqlite:prod.db"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "show", "prod"])
        assert result.exit_code == 0
        assert "db:sqlite:prod.db" in result.output


def test_target_remove(runner: CliRunner) -> None:
    """sqlitch target remove deletes a target."""

    with isolated_test_context(runner) as (runner, temp_dir):
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

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(
            main, ["target", "add", "prod", "db:sqlite:prod.db", "--engine", "sqlite"]
        )
        assert result.exit_code == 0

        result = runner.invoke(
            main,
            [
                "target",
                "alter",
                "prod",
                "db:sqlite:new.db",
                "--engine",
                "pg",
                "--registry",
                "db:sqlite:registry.db",
            ],
        )
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "show", "prod"])
        assert result.exit_code == 0
        assert "db:sqlite:new.db" in result.output
        assert "Engine: pg" in result.output
        assert "Registry: db:sqlite:registry.db" in result.output


def test_target_unknown_show_error(runner: CliRunner) -> None:
    """Showing unknown target fails."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "show", "nonexistent"])
        assert result.exit_code != 0
        assert "Unknown target" in result.output


def test_target_remove_unknown_error(runner: CliRunner) -> None:
    """Removing an unknown target should raise a CommandError."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["target", "remove", "ghost"])

    assert result.exit_code != 0
    assert 'Unknown target "ghost"' in result.output


def test_target_honours_config_root_override(runner: CliRunner) -> None:
    """Targets should be persisted under the resolved config root when provided."""

    with isolated_test_context(runner) as (runner, temp_dir):
        config_root = Path(temp_dir) / "config-home"
        result = runner.invoke(
            main,
            [
                "--config-root",
                str(config_root),
                "target",
                "add",
                "prod",
                "db:sqlite:prod.db",
            ],
        )
        assert result.exit_code == 0

        config_file = config_root / "sqitch.conf"
        assert config_file.exists()
        contents = config_file.read_text(encoding="utf-8")
        assert "db:sqlite:prod.db" in contents


def test_target_suppresses_output_when_quiet(runner: CliRunner) -> None:
    """Global --quiet flag suppresses informational messages."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(
            main,
            [
                "--quiet",
                "target",
                "add",
                "prod",
                "db:sqlite:prod.db",
            ],
        )
        assert result.exit_code == 0
        assert result.output == ""

        result = runner.invoke(main, ["--quiet", "target", "list"])
        assert result.exit_code == 0
        assert result.output == ""


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_target_contract.py)
# =============================================================================


class TestTargetHelp:
    """Test CC-TARGET help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Target command must support --help flag."""
        result = runner.invoke(main, ["target", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["target", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the target command."""
        result = runner.invoke(main, ["target", "--help"])
        assert "target" in result.output.lower()


class TestTargetAction:
    """Test CC-TARGET-001: Action handling."""

    def test_no_action_lists_targets_or_succeeds(self, runner):
        """Target without action should list targets or succeed with default action."""
        result = runner.invoke(main, ["target"])
        # Should either:
        # - Exit 0 and list targets (implemented behavior)
        # - Exit 1 with "not implemented" (stub behavior)
        # - Exit 2 only if there's a parsing error (not expected)
        assert result.exit_code in (
            0,
            1,
        ), f"Expected exit 0 (success/list) or 1 (not implemented), got {result.exit_code}"

    def test_list_action_accepted(self, runner):
        """Target command must accept 'list' action."""
        result = runner.invoke(main, ["target", "list"])
        # Should accept the action (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_add_action_accepted(self, runner):
        """Target command must accept 'add' action."""
        result = runner.invoke(main, ["target", "add", "test_target", "db:sqlite:test.db"])
        # Should accept the action structure (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_remove_action_accepted(self, runner):
        """Target command must accept 'remove' action."""
        result = runner.invoke(main, ["target", "remove", "test_target"])
        # Should accept the action structure (not a parsing error)
        assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestTargetGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Target must accept --quiet global option."""
        result = runner.invoke(main, ["target", "--quiet"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Target must accept --verbose global option."""
        result = runner.invoke(main, ["target", "--verbose"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Target must accept --chdir global option."""
        result = runner.invoke(main, ["target", "--chdir", "/tmp"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Target must accept --no-pager global option."""
        result = runner.invoke(main, ["target", "--no-pager"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestTargetErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Target must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["target", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
