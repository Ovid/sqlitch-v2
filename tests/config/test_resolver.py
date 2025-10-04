from __future__ import annotations

from pathlib import Path

from sqlitch.config import resolver


def _write_config(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _env(**values: object) -> dict[str, str]:
    return {key: str(value) for key, value in values.items()}


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


def test_determine_config_root_prefers_existing_config_directory(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".config" / "sqlitch").mkdir(parents=True)

    root = resolver.determine_config_root(env={}, home=home)

    assert root == home / ".config" / "sqlitch"


def test_determine_config_root_defaults_to_xdg(tmp_path: Path) -> None:
    env = _env(XDG_CONFIG_HOME=tmp_path / "xdg")

    root = resolver.determine_config_root(env=env, home=tmp_path / "home")

    assert root == tmp_path / "xdg" / "sqlitch"


def test_resolve_config_uses_environment_overrides(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    system_dir = tmp_path / "system"
    _write_config(system_dir / "sqlitch.conf", "[core]\nengine=pg\n")

    override_root = tmp_path / "override"
    _write_config(override_root / "sqlitch.conf", "[core]\nengine=mysql\n")

    _write_config(project_dir / "sqlitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        env=_env(
            SQLITCH_CONFIG_ROOT=override_root,
            SQLITCH_SYSTEM_CONFIG=system_dir,
        ),
    )

    assert profile.root_dir == project_dir
    assert profile.files == (
        system_dir / "sqlitch.conf",
        override_root / "sqlitch.conf",
        project_dir / "sqlitch.conf",
    )
    assert profile.settings["core"]["engine"] == "sqlite"
    assert profile.active_engine == "sqlite"


def test_resolve_config_honours_explicit_root_override(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    explicit_root = tmp_path / "explicit"
    _write_config(explicit_root / "sqlitch.conf", "[core]\nengine=pg\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        config_root=explicit_root,
        env=_env(
            SQLITCH_CONFIG_ROOT=tmp_path / "ignored",
            SQLITCH_SYSTEM_CONFIG=tmp_path / "system",
        ),
    )

    assert explicit_root / "sqlitch.conf" in profile.files
    assert profile.settings.get("core", {}).get("engine") == "pg"


def test_resolve_config_accepts_system_path_override(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    user_root = tmp_path / "user"
    _write_config(user_root / "sqlitch.conf", "[core]\nengine=mysql\n")

    system_dir = tmp_path / "system"
    _write_config(system_dir / "sqlitch.conf", "[core]\nengine=pg\n")

    _write_config(project_dir / "sqlitch.conf", "[core]\nengine=sqlite\n")

    profile = resolver.resolve_config(
        root_dir=project_dir,
        config_root=user_root,
        system_path=system_dir,
    )

    assert profile.files[0] == system_dir / "sqlitch.conf"


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
