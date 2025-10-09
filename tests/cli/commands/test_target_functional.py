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


def _read_project_config(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser

@pytest.mark.skip(reason="Pending target URI normalization and registry defaults (T012i)")
class TestTargetUriParsing:
    """Functional tests for target URI parsing and normalization (T010i)."""

    def test_target_add_normalizes_relative_uri(self, runner: CliRunner) -> None:
        """Relative SQLite URIs should resolve to absolute paths with sibling registries."""

        with runner.isolated_filesystem():
            env = _build_isolated_env()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            target_dir = Path("db")
            target_dir.mkdir()
            relative_uri = "db:sqlite:./db/flipr_local.db"

            add_result = runner.invoke(
                main,
                ["target", "add", "flipr_local", relative_uri],
                env=env,
            )
            assert add_result.exit_code == 0, f"Target add failed: {add_result.output}"

            config = _read_project_config(Path("sqitch.conf"))
            section = 'target "flipr_local"'
            assert config.has_section(section), "Target section should exist"

            resolved_db = (Path.cwd() / "db" / "flipr_local.db").resolve().as_posix()
            expected_uri = f"db:sqlite:{resolved_db}"
            assert config.get(section, "uri") == expected_uri

            resolved_registry = (Path.cwd() / "db" / "sqitch.db").resolve().as_posix()
            expected_registry = f"db:sqlite:{resolved_registry}"
            assert config.get(section, "registry") == expected_registry

    def test_target_add_supports_in_memory_database(self, runner: CliRunner) -> None:
        """In-memory SQLite targets should be preserved verbatim and assign a sibling registry."""

        with runner.isolated_filesystem():
            env = _build_isolated_env()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            in_memory_uri = "db:sqlite::memory:"
            add_result = runner.invoke(
                main,
                ["target", "add", "flipr_memory", in_memory_uri],
                env=env,
            )
            assert add_result.exit_code == 0, f"Target add failed: {add_result.output}"

            config = _read_project_config(Path("sqitch.conf"))
            section = 'target "flipr_memory"'
            assert config.has_section(section), "Target section should exist"

            assert config.get(section, "uri") == in_memory_uri

            resolved_registry = (Path.cwd() / "sqitch.db").resolve().as_posix()
            expected_registry = f"db:sqlite:{resolved_registry}"
            assert config.get(section, "registry") == expected_registry

    def test_status_uses_sqlitch_target_environment_override(self, runner: CliRunner) -> None:
        """Status should honor SQLITCH_TARGET while normalizing filesystem paths."""

        with runner.isolated_filesystem():
            env = _build_isolated_env()
            env["SQLITCH_CONFIG_ROOT"] = str(Path.cwd())
            env["HOME"] = str(Path.cwd())

            init_result = runner.invoke(main, ["init", "flipr", "--engine", "sqlite"], env=env)
            assert init_result.exit_code == 0, f"Init failed: {init_result.output}"

            target_dir = Path("db")
            target_dir.mkdir()
            env_target_uri = "db:sqlite:./db/env_target.db"
            env["SQLITCH_TARGET"] = env_target_uri

            status_result = runner.invoke(main, ["status"], env=env)
            assert status_result.exit_code == 0, f"Status failed: {status_result.output}"

            resolved_display = (Path.cwd() / "db" / "env_target.db").resolve().as_posix()
            expected_snippet = f"db:sqlite:{resolved_display}"
            assert expected_snippet in status_result.output
