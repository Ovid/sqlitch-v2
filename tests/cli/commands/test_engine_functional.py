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


class TestEngineAliasResolution:
    """Functional tests for engine alias resolution (T010c)."""

    def test_engine_add_resolves_target_alias(self, runner: CliRunner) -> None:
        """Engine add should resolve target aliases to their stored URIs."""

        with runner.isolated_filesystem():
            env = os.environ.copy()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())
            env.pop("XDG_CONFIG_HOME", None)

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            target_result = runner.invoke(
                main,
                ["target", "add", "flipr_test", "db:sqlite:flipr_test.db"],
                env=env,
            )
            assert target_result.exit_code == 0, f"Target add failed: {target_result.output}"

            engine_result = runner.invoke(main, ["engine", "add", "sqlite", "flipr_test"], env=env)
            assert engine_result.exit_code == 0, f"Engine add failed: {engine_result.output}"
            assert "Created engine 'sqlite'" in engine_result.output

            config_path = Path("sqitch.conf")
            assert config_path.exists(), "sqitch.conf should exist after engine add"

            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(config_path, encoding="utf-8")

            section = 'engine "sqlite"'
            assert parser.has_section(section), "Engine section should be created"
            assert (
                parser.get(section, "target") == "flipr_test"
            ), "Engine target should store the target alias name"

    def test_engine_add_errors_for_unknown_target_alias(self, runner: CliRunner) -> None:
        """Engine add should emit Sqitch-parity error when alias is unknown."""

        with runner.isolated_filesystem():
            env = os.environ.copy()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())
            env.pop("XDG_CONFIG_HOME", None)

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            engine_result = runner.invoke(
                main, ["engine", "add", "sqlite", "missing_alias"], env=env
            )
            assert engine_result.exit_code != 0
            assert 'Unknown target "missing_alias"' in engine_result.output

            config_path = Path("sqitch.conf")
            if config_path.exists():
                parser = configparser.ConfigParser(interpolation=None)
                parser.optionxform = str
                parser.read(config_path, encoding="utf-8")
                assert not parser.has_section(
                    'engine "sqlite"'
                ), "Engine section should not be persisted on failure"
