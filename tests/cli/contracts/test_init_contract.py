"""Contract parity tests for ``sqlitch init``."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner for isolated filesystem tests."""

    return CliRunner()


def test_init_creates_project_layout(runner: CliRunner) -> None:
    """sqlitch init should mirror Sqitch project scaffolding for SQLite."""

    with runner.isolated_filesystem():
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
        assert lines[2] == "%default_engine=sqlite"

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

    with runner.isolated_filesystem():
        plan_override = Path("plans/custom.plan")
        result = runner.invoke(
            main,
            ["--plan-file", str(plan_override), "init", "--engine", "sqlite"],
        )

        assert result.exit_code == 0, result.output
        output_lines = result.output.splitlines()
        assert "Created plans/custom.plan" in output_lines

        assert plan_override.is_file()
        assert not Path("sqitch.plan").exists()

        top_dir = Path("db/scripts")
        assert top_dir.is_dir()
        for subdir in ("deploy", "revert", "verify"):
            assert (top_dir / subdir).is_dir()

        config_content = Path("sqitch.conf").read_text(encoding="utf-8")
        assert "# plan_file = plans/custom.plan" in config_content
        assert "# top_dir = db/scripts" in config_content


def test_init_accepts_uri_option(runner: CliRunner) -> None:
    """--uri should be recorded in the generated config file."""

    with runner.isolated_filesystem():
        uri = "https://github.com/example/project"
        result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite", "--uri", uri])

        assert result.exit_code == 0, result.output

        config_content = Path("sqitch.conf").read_text(encoding="utf-8")
        assert f"uri = {uri}" in config_content


def test_init_rejects_unknown_engine(runner: CliRunner) -> None:
    """Unrecognized engines must raise a user-facing CommandError."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--engine", "oracle"])

    assert result.exit_code != 0
    assert "Unsupported engine 'oracle'" in result.output


def test_init_aborts_when_plan_file_exists(runner: CliRunner) -> None:
    """Existing plan files should prevent accidental overwrites."""

    with runner.isolated_filesystem():
        plan_path = Path("sqitch.plan")
        plan_path.write_text("%project=existing\n", encoding="utf-8")

        result = runner.invoke(main, ["init"])

    assert result.exit_code != 0
    assert "Plan file" in result.output
    assert "already exists" in result.output


def test_init_engine_alias_applies_defaults(runner: CliRunner) -> None:
    """Engine aliases like postgres should normalize to canonical defaults."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "flipr", "--engine", "postgres"])

        assert result.exit_code == 0, result.output

        config_content = Path("sqitch.conf").read_text(encoding="utf-8")
        assert "engine = pg" in config_content
        assert "# target = db:pg:" in config_content


def test_init_respects_top_dir_option(runner: CliRunner) -> None:
    """The --top-dir option should drive scaffold placement and config hints."""

    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--top-dir", "db/sql"])

        assert result.exit_code == 0, result.output

        top_dir = Path("db/sql")
        for subdir in ("deploy", "revert", "verify"):
            assert (top_dir / subdir).is_dir()

        config_content = Path("sqitch.conf").read_text(encoding="utf-8")
        assert "# top_dir = db/sql" in config_content


def test_init_ignores_existing_templates_directory(runner: CliRunner) -> None:
    """Pre-existing template directories are ignored now that we do not scaffold templates."""

    with runner.isolated_filesystem():
        templates_root = Path("etc/templates")
        templates_root.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0, result.output
        assert "Templates" not in result.output

        assert templates_root.is_dir()
