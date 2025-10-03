from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.config import loader


def _write_config(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_config_merges_scopes(tmp_path: Path) -> None:
    system_dir = tmp_path / "system"
    user_dir = tmp_path / "user"
    local_dir = tmp_path / "project"
    for directory in (system_dir, user_dir, local_dir):
        directory.mkdir()

    system_file = system_dir / "sqitch.conf"
    _write_config(
        system_file,
        """[core]\nengine=pg\n[deploy]\nregistry_only=1\n""",
    )
    user_file = user_dir / "sqlitch.conf"
    _write_config(
        user_file,
        """[core]\nengine=mysql\n[env]\nPATH=/usr/local/bin\n""",
    )
    local_file = local_dir / "sqlitch.conf"
    _write_config(
        local_file,
        """[core]\nengine=sqlite\n[deploy]\nregistry_only=0\n""",
    )

    profile = loader.load_config(
        root_dir=local_dir,
        scope_dirs={
            loader.ConfigScope.SYSTEM: system_dir,
            loader.ConfigScope.USER: user_dir,
            loader.ConfigScope.LOCAL: local_dir,
        },
    )

    assert profile.root_dir == local_dir
    assert profile.files == (system_file, user_file, local_file)

    assert profile.settings["core"]["engine"] == "sqlite"
    assert profile.settings["deploy"]["registry_only"] == "0"
    assert profile.settings["env"]["PATH"] == "/usr/local/bin"
    assert profile.active_engine == "sqlite"


def test_load_config_detects_conflicting_files(tmp_path: Path) -> None:
    system_dir = tmp_path / "system"
    user_dir = tmp_path / "user"
    local_dir = tmp_path / "project"
    for directory in (system_dir, user_dir, local_dir):
        directory.mkdir()

    _write_config(local_dir / "sqlitch.conf", "[core]\nengine=sqlite\n")
    _write_config(local_dir / "sqitch.conf", "[core]\nengine=sqlite\n")

    with pytest.raises(loader.ConfigConflictError, match="local"):
        loader.load_config(
            root_dir=local_dir,
            scope_dirs={
                loader.ConfigScope.SYSTEM: system_dir,
                loader.ConfigScope.USER: user_dir,
                loader.ConfigScope.LOCAL: local_dir,
            },
        )


def test_load_config_includes_defaults_and_handles_missing_scopes(tmp_path: Path) -> None:
    local_dir = tmp_path / "project"
    local_dir.mkdir()

    _write_config(
        local_dir / "sqitch.conf",
        """[DEFAULT]\neditor=vim\n[deploy]\nverify=1\n""",
    )

    profile = loader.load_config(
        root_dir=local_dir,
        scope_dirs={loader.ConfigScope.LOCAL: local_dir},
    )

    assert profile.files == (local_dir / "sqitch.conf",)
    assert profile.settings["DEFAULT"]["editor"] == "vim"
    assert profile.settings["deploy"]["verify"] == "1"
    assert profile.active_engine is None
