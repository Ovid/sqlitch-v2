from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pytest

from sqlitch.config import resolver
from sqlitch.config.loader import ConfigConflictError


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
