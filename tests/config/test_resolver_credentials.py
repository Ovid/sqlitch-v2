"""Lockdown tests for credential resolution paths in resolver.py."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from sqlitch.config import resolver


def _env(**values: object) -> Mapping[str, str]:
    return {key: str(value) for key, value in values.items()}


def _write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@dataclass(frozen=True)
class MockCredentialOverrides:
    """Mock credential overrides for testing."""

    username: str | None = None
    password: str | None = None


def test_resolve_credentials_cli_overrides_take_precedence(tmp_path: Path) -> None:
    """CLI overrides should win over env and config."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        '[core]\nengine=pg\n[engine "pg"]\nusername=config_user\npassword=config_pass\n',
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(SQLITCH_USERNAME="env_user", SQLITCH_PASSWORD="env_pass"),
        cli_overrides=MockCredentialOverrides(username="cli_user", password="cli_pass"),
    )

    assert result.username == "cli_user"
    assert result.password == "cli_pass"
    assert result.sources["username"] == "cli"
    assert result.sources["password"] == "cli"


def test_resolve_credentials_env_overrides_config(tmp_path: Path) -> None:
    """Environment variables should override config values."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        '[core]\nengine=pg\n[engine "pg"]\nusername=config_user\npassword=config_pass\n',
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(SQLITCH_USERNAME="env_user", SQLITCH_PASSWORD="env_pass"),
        cli_overrides=None,
    )

    assert result.username == "env_user"
    assert result.password == "env_pass"
    assert result.sources["username"] == "env"
    assert result.sources["password"] == "env"


def test_resolve_credentials_config_as_fallback(tmp_path: Path) -> None:
    """Config values should be used when no CLI or env overrides."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        '[core]\nengine=pg\n[engine "pg"]\nusername=config_user\npassword=config_pass\n',
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(),
        cli_overrides=None,
    )

    assert result.username == "config_user"
    assert result.password == "config_pass"
    assert result.sources["username"] == "config"
    assert result.sources["password"] == "config"


def test_resolve_credentials_unset_when_all_missing(tmp_path: Path) -> None:
    """Should return None with 'unset' source when no credentials provided."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(),
        cli_overrides=None,
    )

    assert result.username is None
    assert result.password is None
    assert result.sources["username"] == "unset"
    assert result.sources["password"] == "unset"


def test_resolve_credentials_target_specific_env_vars(tmp_path: Path) -> None:
    """Target-specific environment variables should be recognized."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=pg\n")

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target="production",
        profile=profile,
        env=_env(SQLITCH_PRODUCTION_USERNAME="prod_user", SQLITCH_PRODUCTION_PASSWORD="prod_pass"),
        cli_overrides=None,
    )

    assert result.username == "prod_user"
    assert result.password == "prod_pass"
    assert result.sources["username"] == "env"
    assert result.sources["password"] == "env"


def test_resolve_credentials_sqitch_legacy_env_vars(tmp_path: Path) -> None:
    """SQITCH_ prefixed environment variables should work."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=pg\n")

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(SQITCH_USERNAME="sqitch_user", SQITCH_PASSWORD="sqitch_pass"),
        cli_overrides=None,
    )

    assert result.username == "sqitch_user"
    assert result.password == "sqitch_pass"


def test_resolve_credentials_env_field_aliases(tmp_path: Path) -> None:
    """Environment variable aliases (USER, PASS, PWD) should work."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=pg\n")

    profile = resolver.resolve_config(root_dir=project_dir)

    # Test USER alias for username
    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(SQLITCH_USER="alias_user", SQLITCH_PWD="alias_pwd"),
        cli_overrides=None,
    )

    assert result.username == "alias_user"
    assert result.password == "alias_pwd"


def test_resolve_credentials_config_field_aliases(tmp_path: Path) -> None:
    """Config field aliases (user, pass) should work."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        '[core]\nengine=pg\n[engine "pg"]\nuser=config_user\npass=config_pass\n',
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(),
        cli_overrides=None,
    )

    assert result.username == "config_user"
    assert result.password == "config_pass"


def test_resolve_credentials_target_config_section(tmp_path: Path) -> None:
    """Target-specific config section should be checked."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        '[core]\nengine=pg\n[target "prod"]\nusername=prod_user\npassword=prod_pass\n',
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target="prod",
        profile=profile,
        env=_env(),
        cli_overrides=None,
    )

    assert result.username == "prod_user"
    assert result.password == "prod_pass"


def test_resolve_credentials_engine_config_section(tmp_path: Path) -> None:
    """Engine-specific config section should be checked."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        '[core]\nengine=mysql\n[engine "mysql"]\nusername=mysql_user\npassword=mysql_pass\n',
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(),
        cli_overrides=None,
    )

    assert result.username == "mysql_user"
    assert result.password == "mysql_pass"


def test_resolve_credentials_core_config_section(tmp_path: Path) -> None:
    """Core config section should be checked as fallback."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        "[core]\nengine=pg\nusername=core_user\npassword=core_pass\n",
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(),
        cli_overrides=None,
    )

    assert result.username == "core_user"
    assert result.password == "core_pass"


def test_resolve_credentials_with_none_profile() -> None:
    """Should handle None profile gracefully."""
    result = resolver.resolve_credentials(
        target=None,
        profile=None,
        env=_env(SQLITCH_USERNAME="env_user"),
        cli_overrides=None,
    )

    assert result.username == "env_user"
    assert result.password is None
    assert result.sources["username"] == "env"
    assert result.sources["password"] == "unset"


def test_resolve_credentials_as_dict() -> None:
    """Test as_dict() method filters None values."""
    result = resolver.resolve_credentials(
        target=None,
        profile=None,
        env=_env(SQLITCH_USERNAME="test_user"),
        cli_overrides=None,
    )

    creds_dict = result.as_dict()
    assert creds_dict == {"username": "test_user"}
    assert "password" not in creds_dict


def test_resolve_credentials_special_characters_in_target() -> None:
    """Target names with special characters should be normalized."""
    result = resolver.resolve_credentials(
        target="prod-db.example.com",
        profile=None,
        env=_env(SQLITCH_PROD_DB_EXAMPLE_COM_USERNAME="normalized_user"),
        cli_overrides=None,
    )

    assert result.username == "normalized_user"


def test_resolve_registry_uri_sqlite_engine(tmp_path: Path) -> None:
    """Test registry URI resolution for SQLite engine."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()

    uri = resolver.resolve_registry_uri(
        engine="sqlite",
        workspace_uri="db:sqlite:./flipr.db",
        project_root=project_dir,
        registry_override=None,
    )

    # Should derive a registry URI
    assert "sqitch.db" in uri or "sqlite" in uri


def test_resolve_registry_uri_non_sqlite_with_override() -> None:
    """Test registry URI resolution for non-SQLite with override."""
    uri = resolver.resolve_registry_uri(
        engine="pg",
        workspace_uri="db:pg://localhost/mydb",
        project_root=Path("/tmp"),
        registry_override="db:pg://localhost/registry",
    )

    assert uri == "db:pg://localhost/registry"


def test_resolve_registry_uri_non_sqlite_no_override() -> None:
    """Test registry URI resolution for non-SQLite without override."""
    workspace = "db:pg://localhost/mydb"
    uri = resolver.resolve_registry_uri(
        engine="pg",
        workspace_uri=workspace,
        project_root=Path("/tmp"),
        registry_override=None,
    )

    assert uri == workspace


def test_cli_override_value_with_non_string() -> None:
    """Test CLI override handling of non-string values."""
    result = resolver.resolve_credentials(
        target=None,
        profile=None,
        env=_env(),
        cli_overrides=MockCredentialOverrides(username=123, password=456),  # type: ignore[arg-type]
    )

    # Should convert to string
    assert result.username == "123"
    assert result.password == "456"


def test_config_without_active_engine(tmp_path: Path) -> None:
    """Test credential resolution when profile has no active_engine."""
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(
        project_dir / "sqitch.conf",
        "[core]\nusername=core_user\n",  # No engine specified
    )

    profile = resolver.resolve_config(root_dir=project_dir)

    result = resolver.resolve_credentials(
        target=None,
        profile=profile,
        env=_env(),
        cli_overrides=None,
    )

    # Should still find credentials in core section
    assert result.username == "core_user"


def test_resolve_user_scope_with_sqitch_user_config_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test _resolve_user_scope_root with SQITCH_USER_CONFIG environment variable."""
    custom_user_dir = tmp_path / "custom_user"
    custom_user_dir.mkdir()
    _write_config(custom_user_dir / "sqitch.conf", "[core]\nengine=pg\n")

    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(SQITCH_USER_CONFIG=custom_user_dir),
    )

    # Should use the custom user config directory
    assert custom_user_dir / "sqitch.conf" in profile.files


def test_determine_system_root_with_sqitch_system_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test system root determination with SQITCH_SYSTEM_CONFIG."""
    custom_system = tmp_path / "custom_system"
    custom_system.mkdir()
    _write_config(custom_system / "sqitch.conf", "[core]\nengine=pg\n")

    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    # Ensure default paths don't exist
    monkeypatch.setattr(resolver, "_DEFAULT_SYSTEM_PATH", tmp_path / "nonexistent_default")
    monkeypatch.setattr(resolver, "_FALLBACK_SYSTEM_PATH", tmp_path / "nonexistent_fallback")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(SQITCH_SYSTEM_CONFIG=custom_system),
    )

    assert custom_system / "sqitch.conf" in profile.files


def test_determine_system_root_uses_fallback_when_default_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that fallback system path is used when default doesn't exist."""
    fallback_system = tmp_path / "etc_sqitch"
    fallback_system.mkdir()
    _write_config(fallback_system / "sqitch.conf", "[core]\nengine=pg\n")

    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    # Make default not exist, but fallback exists
    default_path = tmp_path / "etc_sqlitch"
    monkeypatch.setattr(resolver, "_DEFAULT_SYSTEM_PATH", default_path)
    monkeypatch.setattr(resolver, "_FALLBACK_SYSTEM_PATH", fallback_system)

    profile = resolver.resolve_config(root_dir=project_dir, env=_env())

    assert fallback_system / "sqitch.conf" in profile.files


def test_resolve_config_with_sqitch_config_env(tmp_path: Path) -> None:
    """Test local scope override with SQITCH_CONFIG environment variable."""
    custom_local = tmp_path / "custom_local"
    custom_local.mkdir()
    _write_config(custom_local / "sqitch.conf", "[core]\nengine=pg\n")

    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(SQITCH_CONFIG=custom_local / "sqitch.conf"),
    )

    assert custom_local / "sqitch.conf" in profile.files
