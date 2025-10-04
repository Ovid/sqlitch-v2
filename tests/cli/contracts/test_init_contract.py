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
        assert "Created config file sqlitch.conf" in output_lines
        assert "Created plan file sqlitch.plan" in output_lines
        assert "Created deploy directory deploy" in output_lines
        assert "Created revert directory revert" in output_lines
        assert "Created verify directory verify" in output_lines
        assert "Created templates under etc/templates" in output_lines

        plan_path = Path("sqlitch.plan")
        config_path = Path("sqlitch.conf")
        deploy_dir = Path("deploy")
        revert_dir = Path("revert")
        verify_dir = Path("verify")
        template_root = Path("etc/templates")

        assert plan_path.is_file()
        assert config_path.is_file()
        assert deploy_dir.is_dir()
        assert revert_dir.is_dir()
        assert verify_dir.is_dir()
        assert template_root.is_dir()
        for kind in ("deploy", "revert", "verify"):
            template_file = template_root / kind / "sqlite.tmpl"
            assert template_file.is_file()
            content = template_file.read_text(encoding="utf-8")
            assert "[% project %]" in content
            assert "[% change %]" in content

        plan_content = plan_path.read_text(encoding="utf-8")
        assert plan_content.startswith("%project=flipr\n")
        assert "%default_engine=sqlite\n" in plan_content

        config_content = config_path.read_text(encoding="utf-8")
        assert "[core]" in config_content
        assert "engine = sqlite" in config_content
        assert "# plan_file = sqlitch.plan" in config_content
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
        assert "Created plan file plans/custom.plan" in output_lines

        assert plan_override.is_file()
        assert not Path("sqlitch.plan").exists()

        top_dir = Path("db/scripts")
        assert top_dir.is_dir()
        for subdir in ("deploy", "revert", "verify"):
            assert (top_dir / subdir).is_dir()

        config_content = Path("sqlitch.conf").read_text(encoding="utf-8")
        assert "# plan_file = plans/custom.plan" in config_content
        assert "# top_dir = db/scripts" in config_content
