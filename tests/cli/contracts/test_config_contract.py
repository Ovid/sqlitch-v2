"""Contract parity tests for ``sqlitch config``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from sqlitch.cli.main import main
from tests.support.test_helpers import isolated_test_context


@pytest.fixture()
def runner() -> CliRunner:
    """Return a Click CLI runner configured for isolation."""

    return CliRunner()


def _write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_config_gets_value_from_local_scope(runner: CliRunner) -> None:
    """Retrieving a key should honour local scope precedence by default."""

    with isolated_test_context(runner) as (runner, temp_dir):
        _write_config((temp_dir / "sqitch.conf"), "[core]\nengine = sqlite\n")

        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}
        result = runner.invoke(main, ["config", "core.engine"], env=env)

        assert result.exit_code == 0, result.stderr
        assert result.stdout.strip() == "sqlite"


def test_config_user_scope_override(runner: CliRunner) -> None:
    """Explicit scope flags should select the requested configuration file."""

    with isolated_test_context(runner, set_env=False) as (runner, temp_dir):
        _write_config((temp_dir / "sqitch.conf"), "[core]\nengine = sqlite\n")
        user_root = temp_dir / "config-root"
        _write_config(user_root / "sqitch.conf", "[core]\nengine = postgres\n")

        env = {"SQLITCH_CONFIG_ROOT": str(user_root)}

        default_result = runner.invoke(main, ["config", "core.engine"], env=env)
        assert default_result.exit_code == 0, default_result.stderr
        assert default_result.stdout.strip() == "sqlite"

        user_result = runner.invoke(main, ["config", "--user", "core.engine"], env=env)
        assert user_result.exit_code == 0, user_result.stderr
        assert user_result.stdout.strip() == "postgres"


def test_config_set_local_updates_file(runner: CliRunner) -> None:
    """Setting a value should write to the targeted scope file."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(
            main,
            ["config", "--local", "core.engine", "sqlite"],
            env=env,
        )

        assert result.exit_code == 0, result.stderr
        assert "Set core.engine in local scope" in result.stdout
        content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert "engine = sqlite" in content


def test_config_unset_removes_value(runner: CliRunner) -> None:
    """Unsetting a value should remove it from the configuration file."""

    with isolated_test_context(runner) as (runner, temp_dir):
        _write_config((temp_dir / "sqitch.conf"), "[core]\nengine = sqlite\n")
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(
            main,
            ["config", "--unset", "core.engine"],
            env=env,
        )

        assert result.exit_code == 0, result.stderr
        assert "Unset core.engine in local scope" in result.stdout
        content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert "engine" not in content


def test_config_conflicting_scopes_error(runner: CliRunner) -> None:
    """Providing multiple scope modifiers should fail."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(
            main,
            ["config", "--local", "--user", "core.engine"],
            env=env,
        )

        assert result.exit_code != 0
        assert "Only one scope option may be specified" in result.stderr


def test_config_list_json_outputs_settings(runner: CliRunner) -> None:
    """Listing with --json should emit a JSON payload of merged settings."""

    with isolated_test_context(runner, set_env=False) as (runner, temp_dir):
        _write_config((temp_dir / "sqitch.conf"), "[core]\nengine = sqlite\n")
        user_root = temp_dir / "config-root"
        _write_config(user_root / "sqitch.conf", "[deploy]\nuri = sqlite.db\n")

        env = {"SQLITCH_CONFIG_ROOT": str(user_root)}
        result = runner.invoke(main, ["config", "--list", "--json"], env=env)

        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["core.engine"] == "sqlite"
        assert payload["deploy.uri"] == "sqlite.db"


def test_config_list_plain_outputs_lines(runner: CliRunner) -> None:
    """Plain --list should emit key=value pairs sorted alphabetically."""

    with isolated_test_context(runner) as (runner, temp_dir):
        _write_config(
            (temp_dir / "sqitch.conf"), "[DEFAULT]\ncolor = blue\n[core]\nengine = sqlite\n"
        )
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--list"], env=env)

    assert result.exit_code == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert "color=blue" in lines
    assert "core.engine=sqlite" in lines


def test_config_list_rejects_arguments(runner: CliRunner) -> None:
    """--list must not accept positional arguments or --unset flag."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--list", "core.engine"], env=env)

        assert result.exit_code != 0
        assert "--list cannot be combined" in result.stderr


def test_config_json_without_list_errors(runner: CliRunner) -> None:
    """--json on its own should raise an informative error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--json", "core.engine"], env=env)

        assert result.exit_code != 0
        assert "--json may only be used together with --list" in result.stderr


def test_config_unset_missing_file_errors(runner: CliRunner) -> None:
    """Unsetting a value without a config file should fail fast."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--unset", "core.engine"], env=env)

        assert result.exit_code != 0
        assert "is not set in local scope" in result.stderr


def test_config_requires_section_and_option(runner: CliRunner) -> None:
    """Configuration names must include a section and option component."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "invalid"], env=env)

        assert result.exit_code != 0
        assert "must use section.option" in result.stderr


def test_config_registry_scope_rejected(runner: CliRunner) -> None:
    """Registry scope is not implemented yet and should raise an error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--registry", "core.engine"], env=env)

        assert result.exit_code != 0
        assert "Registry scope operations are not supported" in result.stderr


def test_config_explicit_scope_missing_option_errors(runner: CliRunner) -> None:
    """Explicit scope lookups must report missing options."""

    with isolated_test_context(runner, set_env=False) as (runner, temp_dir):
        user_root = temp_dir / "config-root"
        env = {"SQLITCH_CONFIG_ROOT": str(user_root)}

        result = runner.invoke(main, ["config", "--user", "core.engine"], env=env)

        assert result.exit_code != 0
        assert "No such option: core.engine" in result.stderr


def test_config_set_default_section(runner: CliRunner) -> None:
    """Setting DEFAULT.section values should persist to the config file."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "DEFAULT.color", "blue"], env=env)

        assert result.exit_code == 0, result.stderr
        assert "Set DEFAULT.color in local scope" in result.stdout
        content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert "color = blue" in content


def test_config_get_missing_option_errors(runner: CliRunner) -> None:
    """Looking up a missing option without an explicit scope should raise an error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        _write_config((temp_dir / "sqitch.conf"), "[core]\nengine = sqlite\n")
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "core.uri"], env=env)

        assert result.exit_code != 0
        assert "No such option: core.uri" in result.stderr


def test_config_requires_name_when_no_arguments(runner: CliRunner) -> None:
    """Invoking config without positional arguments should error."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config"], env=env)

        assert result.exit_code != 0
        assert "A configuration name must be provided." in result.stderr


def test_config_unset_requires_name(runner: CliRunner) -> None:
    """--unset requires the name argument to be present."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--unset"], env=env)

        assert result.exit_code != 0
        assert "must be provided when using --unset" in result.stderr


def test_config_unset_rejects_value_argument(runner: CliRunner) -> None:
    """Providing a value together with --unset should fail."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--unset", "core.engine", "extra"], env=env)

        assert result.exit_code != 0
        assert "--unset cannot be combined with a value argument" in result.stderr


def test_config_set_requires_name_with_value(runner: CliRunner) -> None:
    """Setting a value without a name should error before writing."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "", "postgres"], env=env)

        assert result.exit_code != 0
        assert "must be provided when setting a value" in result.stderr


def test_config_unset_default_section(runner: CliRunner) -> None:
    """Unsetting a DEFAULT.* key should remove it from the defaults mapping."""

    with isolated_test_context(runner) as (runner, temp_dir):
        _write_config((temp_dir / "sqitch.conf"), "[DEFAULT]\ncolor = blue\n")
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "--unset", "DEFAULT.color"], env=env)

        assert result.exit_code == 0, result.stderr
        assert "Unset DEFAULT.color in local scope" in result.stdout
        content = (temp_dir / "sqitch.conf").read_text(encoding="utf-8")
        assert "color" not in content


def test_config_gets_default_value(runner: CliRunner) -> None:
    """DEFAULT section lookups should succeed without explicit scope flags."""

    with isolated_test_context(runner) as (runner, temp_dir):
        _write_config((temp_dir / "sqitch.conf"), "[DEFAULT]\ncolor = blue\n")
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", "DEFAULT.color"], env=env)

        assert result.exit_code == 0, result.stderr
        assert result.stdout.strip() == "blue"


def test_config_gets_default_value_from_explicit_scope(runner: CliRunner) -> None:
    """Explicit scope lookups should read DEFAULT values from that config file."""

    with isolated_test_context(runner, set_env=False) as (runner, temp_dir):
        user_root = temp_dir / "config-root"
        _write_config(user_root / "sqitch.conf", "[DEFAULT]\ncolor = blue\n")
        env = {"SQLITCH_CONFIG_ROOT": str(user_root)}

        result = runner.invoke(main, ["config", "--user", "DEFAULT.color"], env=env)

        assert result.exit_code == 0, result.stderr
        assert result.stdout.strip() == "blue"


def test_config_requires_section_and_option_components(runner: CliRunner) -> None:
    """Partially specified names should raise formatting errors."""

    with isolated_test_context(runner) as (runner, temp_dir):
        env = {"SQLITCH_CONFIG_ROOT": str((temp_dir / "config-root"))}

        result = runner.invoke(main, ["config", ".engine"], env=env)

        assert result.exit_code != 0
        assert "must include both section and option components" in result.stderr
