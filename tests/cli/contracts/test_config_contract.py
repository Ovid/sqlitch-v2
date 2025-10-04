"""Contract parity tests for ``sqlitch config``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for isolation."""

    return CliRunner()


def _write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_config_gets_value_from_local_scope(runner: CliRunner) -> None:
    """Retrieving a key should honour local scope precedence by default."""

    with runner.isolated_filesystem():
        _write_config(Path("sqlitch.conf"), "[core]\nengine = sqlite\n")

        env = {"SQLITCH_CONFIG_ROOT": str(Path("config-root"))}
        result = runner.invoke(main, ["config", "core.engine"], env=env)

        assert result.exit_code == 0, result.stderr
        assert result.stdout.strip() == "sqlite"


def test_config_user_scope_override(runner: CliRunner) -> None:
    """Explicit scope flags should select the requested configuration file."""

    with runner.isolated_filesystem():
        _write_config(Path("sqlitch.conf"), "[core]\nengine = sqlite\n")
        user_root = Path("config-root")
        _write_config(user_root / "sqlitch.conf", "[core]\nengine = postgres\n")

        env = {"SQLITCH_CONFIG_ROOT": str(user_root)}

        default_result = runner.invoke(main, ["config", "core.engine"], env=env)
        assert default_result.exit_code == 0, default_result.stderr
        assert default_result.stdout.strip() == "sqlite"

        user_result = runner.invoke(main, ["config", "--user", "core.engine"], env=env)
        assert user_result.exit_code == 0, user_result.stderr
        assert user_result.stdout.strip() == "postgres"


def test_config_set_local_updates_file(runner: CliRunner) -> None:
    """Setting a value should write to the targeted scope file."""

    with runner.isolated_filesystem():
        env = {"SQLITCH_CONFIG_ROOT": str(Path("config-root"))}

        result = runner.invoke(
            main,
            ["config", "--local", "core.engine", "sqlite"],
            env=env,
        )

        assert result.exit_code == 0, result.stderr
        assert "Set core.engine in local scope" in result.stdout
        content = Path("sqlitch.conf").read_text(encoding="utf-8")
        assert "engine = sqlite" in content


def test_config_unset_removes_value(runner: CliRunner) -> None:
    """Unsetting a value should remove it from the configuration file."""

    with runner.isolated_filesystem():
        _write_config(Path("sqlitch.conf"), "[core]\nengine = sqlite\n")
        env = {"SQLITCH_CONFIG_ROOT": str(Path("config-root"))}

        result = runner.invoke(
            main,
            ["config", "--unset", "core.engine"],
            env=env,
        )

        assert result.exit_code == 0, result.stderr
        assert "Unset core.engine in local scope" in result.stdout
        content = Path("sqlitch.conf").read_text(encoding="utf-8")
        assert "engine" not in content


def test_config_conflicting_scopes_error(runner: CliRunner) -> None:
    """Providing multiple scope modifiers should fail."""

    with runner.isolated_filesystem():
        env = {"SQLITCH_CONFIG_ROOT": str(Path("config-root"))}

        result = runner.invoke(
            main,
            ["config", "--local", "--user", "core.engine"],
            env=env,
        )

        assert result.exit_code != 0
        assert "Only one scope option may be specified" in result.stderr


def test_config_list_json_outputs_settings(runner: CliRunner) -> None:
    """Listing with --json should emit a JSON payload of merged settings."""

    with runner.isolated_filesystem():
        _write_config(Path("sqlitch.conf"), "[core]\nengine = sqlite\n")
        user_root = Path("config-root")
        _write_config(user_root / "sqlitch.conf", "[deploy]\nuri = sqlite.db\n")

        env = {"SQLITCH_CONFIG_ROOT": str(user_root)}
        result = runner.invoke(main, ["config", "--list", "--json"], env=env)

        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["core.engine"] == "sqlite"
        assert payload["deploy.uri"] == "sqlite.db"
