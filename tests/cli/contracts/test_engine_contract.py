"""Contract parity tests for ``sqlitch engine``."""

from __future__ import annotations

import configparser
from pathlib import Path

from click.testing import CliRunner

from sqlitch.cli.main import main


def _read_engine_section(path: Path, name: str) -> dict[str, str]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return dict(parser[f'engine "{name}"'])


def _write_engine_section(path: Path, name: str, **values: str) -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if path.exists():
        parser.read(path, encoding="utf-8")
    section = f'engine "{name}"'
    if not parser.has_section(section):
        parser.add_section(section)
    for key, value in values.items():
        parser.set(section, key, value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def _runner() -> CliRunner:
    return CliRunner()


def test_engine_add_writes_definition(tmp_path: Path) -> None:
    """Adding an engine should persist the definition to the config root."""

    runner = _runner()
    config_root = tmp_path / "config-root"

    with runner.isolated_filesystem():
        env = {"SQLITCH_CONFIG_ROOT": str(config_root)}
        result = runner.invoke(
            main,
            ["engine", "add", "widgets", "db:sqlite:widgets.db"],
            env=env,
        )

        assert result.exit_code == 0, result.output

        config_path = config_root / "sqitch.conf"
        contents = _read_engine_section(config_path, "widgets")
        assert contents["uri"] == "db:sqlite:widgets.db"
        assert "registry" not in contents


def test_engine_add_rejects_duplicate(tmp_path: Path) -> None:
    """Adding an engine twice should raise a parity-preserving error."""

    runner = _runner()
    config_root = tmp_path / "config-root"

    with runner.isolated_filesystem():
        env = {"SQLITCH_CONFIG_ROOT": str(config_root)}
        first = runner.invoke(
            main,
            ["engine", "add", "widgets", "db:sqlite:widgets.db"],
            env=env,
        )
        assert first.exit_code == 0, first.output

        duplicate = runner.invoke(
            main,
            ["engine", "add", "widgets", "db:sqlite:widgets.db"],
            env=env,
        )
        assert duplicate.exit_code != 0
        assert "Engine 'widgets' already exists" in duplicate.output


def test_engine_update_overwrites_existing_values(tmp_path: Path) -> None:
    """Updating an engine should mutate only the supplied values."""

    runner = _runner()
    config_root = tmp_path / "config-root"
    config_path = config_root / "sqitch.conf"
    _write_engine_section(config_path, "widgets", uri="db:sqlite:widgets.db")

    with runner.isolated_filesystem():
        env = {"SQLITCH_CONFIG_ROOT": str(config_root)}
        result = runner.invoke(
            main,
            [
                "engine",
                "update",
                "widgets",
                "db:mysql://example.com/widgets",
                "--registry",
                "db:mysql://example.com/registry",
                "--client",
                "mysql",
                "--verify",
            ],
            env=env,
        )

        assert result.exit_code == 0, result.output

        contents = _read_engine_section(config_path, "widgets")
        assert contents["uri"] == "db:mysql://example.com/widgets"
        assert contents["registry"] == "db:mysql://example.com/registry"
        assert contents["client"] == "mysql"
        assert contents["verify"] == "true"


def test_engine_remove_deletes_definition(tmp_path: Path) -> None:
    """Removing an engine should delete the section from the config file."""

    runner = _runner()
    config_root = tmp_path / "config-root"
    config_path = config_root / "sqitch.conf"
    _write_engine_section(config_path, "widgets", uri="db:sqlite:widgets.db")

    with runner.isolated_filesystem():
        env = {"SQLITCH_CONFIG_ROOT": str(config_root)}
        result = runner.invoke(
            main,
            ["engine", "remove", "widgets", "--yes"],
            env=env,
        )

        assert result.exit_code == 0, result.output

        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(config_path, encoding="utf-8")
        assert not parser.has_section('engine "widgets"')


def test_engine_list_outputs_table(tmp_path: Path) -> None:
    """Listing engines should report columnar output compatible with Sqitch."""

    runner = _runner()
    config_root = tmp_path / "config-root"
    config_path = config_root / "sqitch.conf"
    _write_engine_section(config_path, "widgets", uri="db:sqlite:widgets.db")
    _write_engine_section(
        config_path,
        "analytics",
        uri="db:pg://example.com/analytics",
        registry="db:pg://example.com/registry",
        client="psql",
        verify="false",
        plan="analytics.plan",
    )

    with runner.isolated_filesystem():
        env = {"SQLITCH_CONFIG_ROOT": str(config_root)}
        result = runner.invoke(main, ["engine", "list"], env=env)

        assert result.exit_code == 0, result.output
        output = result.output.strip().splitlines()
        assert output[0].startswith("NAME")
        assert "widgets" in output[1]
        assert "db:sqlite:widgets.db" in output[1]
        assert "analytics" in output[2]
        assert "db:pg://example.com/analytics" in output[2]
