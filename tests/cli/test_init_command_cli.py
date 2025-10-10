"""CLI integration tests for the ``sqlitch init`` command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


def test_init_command_accepts_uri_option(tmp_path: Path) -> None:
    runner = CliRunner()
    uri = "https://github.com/sqitchers/sqitch-sqlite-intro/"

    with isolated_test_context(runner) as (runner, temp_dir):
        config_root = Path("config-root")
        result = runner.invoke(
            main,
            [
                "--config-root",
                str(config_root),
                "--engine",
                "sqlite",
                "init",
                "flipr",
                "--uri",
                uri,
            ],
        )

        assert result.exit_code == 0, result.output
        config_path = Path("sqitch.conf")
        assert config_path.exists()
        contents = config_path.read_text(encoding="utf-8")
        assert f"uri = {uri}" in contents
        plan_path = Path("sqitch.plan")
        assert plan_path.exists()
        templates_dir = Path("etc") / "templates"
        assert not templates_dir.exists()
        assert not templates_dir.exists()
