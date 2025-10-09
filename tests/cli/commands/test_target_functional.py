from __future__ import annotations

import configparser
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from sqlitch.cli.main import main


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click CLI test runner."""

    return CliRunner()


def _build_isolated_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("XDG_CONFIG_HOME", None)
    # HOME and SQLITCH_CONFIG_ROOT will be populated per-test based on cwd.
    return env


class TestTargetAliasPersistence:
    """Functional tests for target alias persistence (T010d)."""

    def test_target_add_persists_alias_in_project_config(self, runner: CliRunner) -> None:
        """Target add should persist alias entries used by engine commands."""

        with runner.isolated_filesystem():
            env = _build_isolated_env()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            result = runner.invoke(
                main,
                ["target", "add", "flipr_test", "db:sqlite:flipr_test.db"],
                env=env,
            )
            assert result.exit_code == 0, f"Target add failed: {result.output}"
            assert result.output.strip() == "Added target flipr_test"

            config_path = Path("sqitch.conf")
            assert config_path.exists(), "sqitch.conf should exist in project root"

            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(config_path, encoding="utf-8")

            section = 'target "flipr_test"'
            assert parser.has_section(section), "Target section should be created"
            assert (
                parser.get(section, "uri") == "db:sqlite:flipr_test.db"
            ), "Target URI should match provided value"

    def test_target_add_respects_quiet_mode(self, runner: CliRunner) -> None:
        """Target add should suppress output when quiet mode is active."""

        with runner.isolated_filesystem():
            env = _build_isolated_env()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            result = runner.invoke(
                main,
                ["--quiet", "target", "add", "flipr_test", "db:sqlite:flipr_test.db"],
                env=env,
            )
            assert result.exit_code == 0, f"Target add --quiet failed: {result.output}"
            assert result.output == ""

            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read("sqitch.conf", encoding="utf-8")
            assert parser.has_section('target "flipr_test"')
