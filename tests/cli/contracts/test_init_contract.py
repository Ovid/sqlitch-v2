"""Contract parity tests for ``sqlitch init``.

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


def test_init_creates_project_layout(runner: CliRunner) -> None:
    """sqlitch init should mirror Sqitch project scaffolding for SQLite."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"])

        assert result.exit_code == 0, result.output
        output_lines = result.output.splitlines()
        assert "Created sqitch.conf" in output_lines
        assert "Created sqitch.plan" in output_lines
        assert "Created deploy/" in output_lines
        assert "Created revert/" in output_lines
        assert "Created verify/" in output_lines
        assert "Created templates under etc/templates" not in output_lines

        plan_path = Path("sqitch.plan")
        config_path = Path("sqitch.conf")
        deploy_dir = Path("deploy")
        revert_dir = Path("revert")
        verify_dir = Path("verify")
        template_root = Path("etc/templates")

        assert plan_path.is_file()
        assert config_path.is_file()
        assert deploy_dir.is_dir()
        assert revert_dir.is_dir()
        assert verify_dir.is_dir()
        assert not template_root.exists()

        plan_content = plan_path.read_text(encoding="utf-8")
        lines = plan_content.splitlines()
        assert lines[0] == "%syntax-version=1.0.0"
        assert lines[1] == "%project=flipr"
        # Note: Sqitch doesn't store engine in plan - it's in config
        assert lines[2] == ""  # Blank line after headers

        config_content = config_path.read_text(encoding="utf-8")
        assert "[core]" in config_content
        assert "engine = sqlite" in config_content
        assert "# plan_file = sqitch.plan" in config_content
        assert "# top_dir = ." in config_content
        assert "# target = db:sqlite:" in config_content


def test_init_respects_env_and_plan_override(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Environment variables and overrides should influence init scaffolding."""

    monkeypatch.setenv("SQLITCH_TOP_DIR", "db/scripts")

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_override = Path("plans/custom.plan")
        result = runner.invoke(
            main,
            ["--plan-file", str(plan_override), "init", "--engine", "sqlite"],
        )

        assert result.exit_code == 0, result.output
        output_lines = result.output.splitlines()
        assert "Created plans/custom.plan" in output_lines

        assert plan_override.is_file()
        assert not (temp_dir / "sqitch.plan").exists()

        top_dir = Path("db/scripts")
        assert top_dir.is_dir()
        for subdir in ("deploy", "revert", "verify"):
            assert (top_dir / subdir).is_dir()

        config_content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert "# plan_file = plans/custom.plan" in config_content
        assert "# top_dir = db/scripts" in config_content


def test_init_accepts_uri_option(runner: CliRunner) -> None:
    """--uri should be recorded in the generated config file."""

    with isolated_test_context(runner) as (runner, temp_dir):
        uri = "https://github.com/example/project"
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite", "--uri", uri])

        assert result.exit_code == 0, result.output

        config_content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert f"uri = {uri}" in config_content


def test_init_rejects_unknown_engine(runner: CliRunner) -> None:
    """Unrecognized engines must raise a user-facing CommandError."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "--engine", "oracle"])

    assert result.exit_code != 0
    assert "Unsupported engine 'oracle'" in result.output


def test_init_aborts_when_plan_file_exists(runner: CliRunner) -> None:
    """Existing plan files should prevent accidental overwrites."""

    with isolated_test_context(runner) as (runner, temp_dir):
        plan_path = Path("sqitch.plan")
        plan_path.write_text("%project=existing\n", encoding="utf-8")

        result = runner.invoke(main, ["init"])

    assert result.exit_code != 0
    assert "Plan file" in result.output
    assert "already exists" in result.output


def test_init_engine_alias_applies_defaults(runner: CliRunner) -> None:
    """Engine aliases like postgres should normalize to canonical defaults."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "flipr", "--engine", "postgres"])

        assert result.exit_code == 0, result.output

        config_content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert "engine = pg" in config_content
        assert "# target = db:pg:" in config_content


def test_init_respects_top_dir_option(runner: CliRunner) -> None:
    """The --top-dir option should drive scaffold placement and config hints."""

    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(main, ["init", "--top-dir", "db/sql"])

        assert result.exit_code == 0, result.output

        top_dir = Path("db/sql")
        for subdir in ("deploy", "revert", "verify"):
            assert (top_dir / subdir).is_dir()

        config_content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert "# top_dir = db/sql" in config_content


def test_init_ignores_existing_templates_directory(runner: CliRunner) -> None:
    """Pre-existing template directories are ignored now that we do not scaffold templates."""

    with isolated_test_context(runner) as (runner, temp_dir):
        templates_root = Path("etc/templates")
        templates_root.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0, result.output
        assert "Templates" not in result.output

        assert templates_root.is_dir()


# =============================================================================
# CLI Contract Tests (merged from tests/cli/commands/test_init_contract.py)
# =============================================================================


class TestInitHelp:
    """Test CC-INIT help support (GC-001)."""

    def test_help_flag_exits_zero(self, runner):
        """Init command must support --help flag."""
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}"

    def test_help_shows_usage(self, runner):
        """Help output must include usage information."""
        result = runner.invoke(main, ["init", "--help"])
        assert "Usage:" in result.output or "usage:" in result.output.lower()

    def test_help_shows_command_name(self, runner):
        """Help output must mention the init command."""
        result = runner.invoke(main, ["init", "--help"])
        assert "init" in result.output.lower()


class TestInitOptionalProjectName:
    """Test CC-INIT-001: Optional project name."""

    def test_init_without_project_name_accepted(self, runner):
        """Init without project name must be accepted (uses directory name)."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init"])
            # Should accept (not a parsing error)
            # May exit 0 (success), 1 (not implemented), or fail validation
            assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestInitWithProjectName:
    """Test CC-INIT-002: With project name."""

    def test_init_with_project_name_accepted(self, runner):
        """Init with project name must be accepted."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "myproject"])
            # Should accept (not a parsing error)
            assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"

    def test_init_with_engine_option(self, runner):
        """Init with --engine option must be accepted."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "myproject", "--engine", "sqlite"])
            # Should accept (not a parsing error)
            assert result.exit_code != 2, f"Should not be parsing error, got: {result.output}"


class TestInitGlobalOptions:
    """Test GC-002: Global options recognition."""

    def test_quiet_option_accepted(self, runner):
        """Init must accept --quiet global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "--quiet"])
            # Should not fail with "no such option" error
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_verbose_option_accepted(self, runner):
        """Init must accept --verbose global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "--verbose"])
            # Should not fail with "no such option" error
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_chdir_option_accepted(self, runner):
        """Init must accept --chdir global option."""
        result = runner.invoke(main, ["init", "--chdir", "/tmp", "test"])
        # Should not fail with "no such option" error
        assert "no such option" not in result.output.lower()
        assert result.exit_code != 2 or "no such option" not in result.output.lower()

    def test_no_pager_option_accepted(self, runner):
        """Init must accept --no-pager global option."""
        with isolated_test_context(runner) as (runner, temp_dir):
            result = runner.invoke(main, ["init", "--no-pager"])
            # Should not fail with "no such option" error
            assert "no such option" not in result.output.lower()
            assert result.exit_code != 2 or "no such option" not in result.output.lower()


class TestInitErrorHandling:
    """Test GC-004: Error output and GC-005: Unknown options."""

    def test_unknown_option_rejected(self, runner):
        """Init must reject unknown options with exit code 2."""
        result = runner.invoke(main, ["init", "--nonexistent-option"])
        assert result.exit_code == 2, f"Expected exit 2 for unknown option, got {result.exit_code}"
        assert "no such option" in result.output.lower() or "unrecognized" in result.output.lower()
