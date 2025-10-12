from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.config import resolver
from sqlitch.config.loader import ConfigConflictError

# Migrated from tests/regression/test_config_root_override.py
pytestmark_config_root = pytest.mark.skip(
    reason="Pending T034: configuration root override regression"
)


def _write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _env(**values: object) -> dict[str, str]:
    return {key: str(value) for key, value in values.items()}


def test_resolve_config_applies_scope_precedence(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    system_dir = tmp_path / "system"
    _write_config(system_dir / "sqitch.conf", "[core]\nengine=pg\n")

    user_dir = tmp_path / "user"
    _write_config(
        user_dir / "sqitch.conf",
        """[core]\nplan_file=sqitch.plan\n""",
    )

    _write_config(
        project_dir / "sqitch.conf",
        """[core]\nengine=sqlite\n""",
    )

    profile = resolver.resolve_config(
        root_dir=project_dir,
        config_root=user_dir,
        system_path=system_dir,
    )

    assert profile.files == (
        system_dir / "sqitch.conf",
        user_dir / "sqitch.conf",
        project_dir / "sqitch.conf",
    )
    core_settings = profile.settings["core"]
    assert core_settings["engine"] == "sqlite"
    assert core_settings["plan_file"] == "sqitch.plan"


def test_resolve_config_rejects_duplicate_files_within_scope(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    system_dir = tmp_path / "system"
    system_dir.mkdir()
    _write_config(system_dir / "sqitch.conf", "[core]\nengine=pg\n")
    _write_config(system_dir / "sqlitch.conf", "[core]\nengine=pg\n")

    with pytest.raises(ConfigConflictError) as excinfo:
        resolver.resolve_config(root_dir=project_dir, system_path=system_dir)

    assert "system" in str(excinfo.value)


def test_determine_config_root_prioritises_sqlitch_env(tmp_path: Path) -> None:
    env = _env(
        SQLITCH_CONFIG_ROOT=tmp_path / "sqlitch",  # highest precedence
        SQITCH_CONFIG_ROOT=tmp_path / "sqitch",
        XDG_CONFIG_HOME=tmp_path / "xdg",
    )

    root = resolver.determine_config_root(env=env, home=tmp_path / "home")

    assert root == tmp_path / "sqlitch"


def test_determine_config_root_falls_back_to_sqitch_env(tmp_path: Path) -> None:
    env = _env(SQITCH_CONFIG_ROOT=tmp_path / "sqitch")

    root = resolver.determine_config_root(env=env, home=tmp_path / "home")

    assert root == tmp_path / "sqitch"


def test_determine_config_root_prefers_existing_sqitch_directory(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".sqitch").mkdir(parents=True)
    env: dict[str, str] = {}

    root = resolver.determine_config_root(env=env, home=home)

    assert root == home / ".sqitch"


def test_determine_config_root_uses_sqitch_for_compatibility(tmp_path: Path) -> None:
    """FR-001b: Always use ~/.sqitch/ for Sqitch compatibility, not ~/.config/sqlitch/.

    Even if ~/.config/sqlitch/ exists, we must use ~/.sqitch/ to maintain
    100% compatibility with Sqitch. Users must be able to seamlessly switch
    between sqitch and sqlitch commands.
    """
    home = tmp_path / "home"
    # Even if .config/sqlitch exists, we should use .sqitch for compatibility
    (home / ".config" / "sqlitch").mkdir(parents=True)

    root = resolver.determine_config_root(env={}, home=home)

    # FR-001b: Must use .sqitch, not .config/sqlitch
    assert root == home / ".sqitch"


def test_determine_config_root_defaults_to_xdg(tmp_path: Path) -> None:
    env = _env(XDG_CONFIG_HOME=tmp_path / "xdg")

    root = resolver.determine_config_root(env=env, home=tmp_path / "home")

    assert root == tmp_path / "xdg" / "sqlitch"


def test_resolve_config_uses_environment_overrides(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    system_dir = tmp_path / "system"
    _write_config(system_dir / "sqitch.conf", "[core]\nengine=pg\n")

    override_root = tmp_path / "override"
    _write_config(override_root / "sqitch.conf", "[core]\nengine=mysql\n")

    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(
            SQLITCH_CONFIG_ROOT=override_root,
            SQLITCH_SYSTEM_CONFIG=system_dir,
        ),
    )

    assert profile.root_dir == project_dir
    assert profile.files == (
        system_dir / "sqitch.conf",
        override_root / "sqitch.conf",
        project_dir / "sqitch.conf",
    )
    assert profile.settings["core"]["engine"] == "sqlite"
    assert profile.active_engine == "sqlite"


def test_resolve_config_honours_explicit_root_override(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    explicit_root = tmp_path / "explicit"
    _write_config(explicit_root / "sqitch.conf", "[core]\nengine=pg\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        config_root=explicit_root,
        env=_env(
            SQLITCH_CONFIG_ROOT=tmp_path / "ignored",
            SQLITCH_SYSTEM_CONFIG=tmp_path / "system",
        ),
    )

    assert explicit_root / "sqitch.conf" in profile.files
    assert profile.settings.get("core", {}).get("engine") == "pg"


def test_resolve_config_accepts_system_path_override(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    user_root = tmp_path / "user"
    _write_config(user_root / "sqitch.conf", "[core]\nengine=mysql\n")

    system_dir = tmp_path / "system"
    _write_config(system_dir / "sqitch.conf", "[core]\nengine=pg\n")

    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        config_root=user_root,
        system_path=system_dir,
    )

    assert profile.files[0] == system_dir / "sqitch.conf"


def test_resolve_config_uses_legacy_system_env(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    user_root = tmp_path / "user"
    _write_config(user_root / "sqlitch.conf", "[core]\nengine=mysql\n")

    legacy_system = tmp_path / "sqitch-system"
    _write_config(legacy_system / "sqlitch.conf", "[core]\nengine=pg\n")

    _write_config(project_dir / "sqlitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(
            SQLITCH_CONFIG_ROOT=user_root,
            SQITCH_SYSTEM_CONFIG=legacy_system,
        ),
    )

    assert profile.files[0] == legacy_system / "sqlitch.conf"


def test_resolve_config_falls_back_to_default_paths(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    user_root = tmp_path / "user"
    _write_config(user_root / "sqlitch.conf", "[core]\nengine=mysql\n")
    _write_config(project_dir / "sqlitch.conf", "[core]\nengine=sqlite\n")

    default_dir = tmp_path / "default-system"
    fallback_dir = tmp_path / "fallback-system"
    _write_config(fallback_dir / "sqlitch.conf", "[core]\nengine=pg\n")

    monkeypatch.setattr(resolver, "_DEFAULT_SYSTEM_PATH", default_dir)
    monkeypatch.setattr(resolver, "_FALLBACK_SYSTEM_PATH", fallback_dir)

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(SQLITCH_CONFIG_ROOT=user_root),
    )

    assert profile.files[0] == fallback_dir / "sqlitch.conf"


def test_resolve_config_prefers_existing_default_system_path(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    user_root = tmp_path / "user"
    _write_config(user_root / "sqlitch.conf", "[core]\nengine=mysql\n")
    _write_config(project_dir / "sqlitch.conf", "[core]\nengine=sqlite\n")

    default_dir = tmp_path / "default-system"
    fallback_dir = tmp_path / "fallback-system"
    _write_config(default_dir / "sqlitch.conf", "[core]\nengine=pg\n")

    monkeypatch.setattr(resolver, "_DEFAULT_SYSTEM_PATH", default_dir)
    monkeypatch.setattr(resolver, "_FALLBACK_SYSTEM_PATH", fallback_dir)

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(SQLITCH_CONFIG_ROOT=user_root),
    )

    assert profile.files[0] == default_dir / "sqlitch.conf"


def test_determine_system_root_returns_default_when_no_paths_exist(
    tmp_path: Path, monkeypatch
) -> None:
    default_dir = tmp_path / "default-system"
    fallback_dir = tmp_path / "fallback-system"

    monkeypatch.setattr(resolver, "_DEFAULT_SYSTEM_PATH", default_dir)
    monkeypatch.setattr(resolver, "_FALLBACK_SYSTEM_PATH", fallback_dir)

    result = resolver._determine_system_root(env={}, system_path=None)
    assert result == default_dir


def test_resolve_registry_uri_sqlite_defaults_to_sibling(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace.db"
    workspace_uri = f"db:sqlite:{workspace.as_posix()}"

    registry_uri = resolver.resolve_registry_uri(
        engine="sqlite",
        workspace_uri=workspace_uri,
        project_root=tmp_path,
    )

    expected = f"db:sqlite:{(workspace.parent / 'sqitch.db').as_posix()}"
    assert registry_uri == expected


def test_resolve_registry_uri_sqlite_honours_override(tmp_path: Path) -> None:
    workspace_uri = f"db:sqlite:{(tmp_path / 'workspace.db').as_posix()}"
    override = (tmp_path / "custom" / "registry.db").as_posix()

    registry_uri = resolver.resolve_registry_uri(
        engine="sqlite",
        workspace_uri=workspace_uri,
        project_root=tmp_path,
        registry_override=override,
    )

    expected = f"db:sqlite:{(tmp_path / 'custom' / 'registry.db').as_posix()}"
    assert registry_uri == expected


def test_resolve_registry_uri_sqlite_in_memory(tmp_path: Path) -> None:
    workspace_uri = "db:sqlite::memory:"

    registry_uri = resolver.resolve_registry_uri(
        engine="sqlite",
        workspace_uri=workspace_uri,
        project_root=tmp_path,
    )

    expected = f"db:sqlite:{(tmp_path / 'sqitch.db').as_posix()}"
    assert registry_uri == expected


def test_resolve_registry_uri_non_sqlite_defaults_to_workspace() -> None:
    workspace_uri = "db:pg://example"

    registry_uri = resolver.resolve_registry_uri(
        engine="pg",
        workspace_uri=workspace_uri,
        project_root=Path("."),
    )

    assert registry_uri == workspace_uri

    override = "db:pg://registry"
    overridden = resolver.resolve_registry_uri(
        engine="pg",
        workspace_uri=workspace_uri,
        project_root=Path("."),
        registry_override=override,
    )

    assert overridden == override


# Migrated from tests/regression/test_config_root_override.py
@pytest.mark.skip(reason="Pending T034: configuration root override regression")
def test_config_root_override_isolation() -> None:
    """Placeholder regression test for T034 - config root override isolation.

    When implemented, this should test that SQLITCH_CONFIG_ROOT environment
    variable properly isolates configuration lookups without polluting other
    scopes or causing conflicts with system/user configs.
    """
    ...


# =============================================================================
# Lockdown Tests (merged from test_resolver_lockdown.py)
# =============================================================================


def _write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _env(**values: object) -> Mapping[str, str]:
    return {key: str(value) for key, value in values.items()}


def test_resolve_config_rejects_duplicate_local_files(tmp_path: Path) -> None:
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=pg\n")
    _write_config(project_dir / "sqlitch.conf", "[core]\nengine=sqlite\n")

    with pytest.raises(ConfigConflictError) as excinfo:
        resolver.resolve_config(root_dir=project_dir)

    assert "local" in str(excinfo.value)


def test_resolve_config_missing_scopes_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    default_dir = tmp_path / "etc_sqlitch"
    fallback_dir = tmp_path / "etc_sqitch"
    _write_config(default_dir / "sqitch.conf", "[core]\nengine=pg\n")

    monkeypatch.setattr(resolver, "_DEFAULT_SYSTEM_PATH", default_dir)
    monkeypatch.setattr(resolver, "_FALLBACK_SYSTEM_PATH", fallback_dir)

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(SQLITCH_CONFIG_ROOT=tmp_path / "missing-user"),
    )

    assert profile.files == (
        default_dir / "sqitch.conf",
        project_dir / "sqitch.conf",
    )


def test_determine_config_root_rejects_empty_env_values(tmp_path: Path) -> None:
    env = _env(
        SQLITCH_CONFIG_ROOT="",
        SQITCH_CONFIG_ROOT="",
        XDG_CONFIG_HOME="",
    )

    home = tmp_path / "home"
    (home / ".sqitch").mkdir(parents=True)

    root = resolver.determine_config_root(env=env, home=home)

    assert root == home / ".sqitch"


def test_resolve_config_ignores_empty_environment_overrides(tmp_path: Path) -> None:
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(
            SQLITCH_CONFIG_ROOT="",
            SQLITCH_SYSTEM_CONFIG="",
            SQLITCH_CONFIG="",
        ),
    )

    assert project_dir / "sqitch.conf" in profile.files
    assert profile.files[-1] == project_dir / "sqitch.conf"


def test_resolve_config_supports_parent_directory_overrides(tmp_path: Path) -> None:
    project_dir = tmp_path / "workspace"
    project_dir.mkdir()
    _write_config(project_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    custom_root = tmp_path / "custom-root"
    _write_config(custom_root / "sqitch.conf", "[core]\nengine=pg\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(SQLITCH_CONFIG_ROOT=project_dir / ".." / "custom-root"),
    )

    # Sqitch accepts parent-directory overrides via environment variables; ensure parity.
    resolved_files = tuple(path.resolve() for path in profile.files)
    custom_path = (custom_root / "sqitch.conf").resolve()
    project_path = (project_dir / "sqitch.conf").resolve()

    assert custom_path in resolved_files
    assert project_path in resolved_files
    assert resolved_files.index(custom_path) < resolved_files.index(project_path)
