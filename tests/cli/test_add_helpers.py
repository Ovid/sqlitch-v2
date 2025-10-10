"""Unit coverage for helper utilities in ``sqlitch.cli.commands.add``."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands import add as add_module
from sqlitch.config.loader import ConfigProfile
from sqlitch.utils.identity import resolve_planner_identity
from sqlitch.utils.templates import default_template_body


def test_resolve_planner_prioritises_sqlitch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that SQLITCH_* env vars work (backward compatibility)."""
    env = {
        "SQLITCH_USER_NAME": "Ada",
        "SQLITCH_USER_EMAIL": "ada@example.com",
        "USER": "fallback",
    }

    # Mock system functions to prevent real system lookups
    monkeypatch.setattr("os.getlogin", lambda: "fallback")
    try:
        import collections
        import pwd

        MockPwRecord = collections.namedtuple("MockPwRecord", ["pw_name", "pw_gecos"])
        monkeypatch.setattr(
            "pwd.getpwuid", lambda uid: MockPwRecord(pw_name="fallback", pw_gecos="")
        )
    except ImportError:
        pass

    assert resolve_planner_identity(env, None) == "Ada <ada@example.com>"


def test_resolve_planner_fallbacks_when_no_email(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that email is always synthesized when not provided."""
    env = {
        "GIT_AUTHOR_NAME": "Ada",
        "USERNAME": "backup",
    }

    # Mock system functions to avoid using real user info
    monkeypatch.setattr("socket.gethostname", lambda: "testhost")
    monkeypatch.setattr("os.getlogin", lambda: "backup")

    # Mock pwd module if it exists (Unix/macOS)
    try:
        import collections
        import pwd

        MockPwRecord = collections.namedtuple("MockPwRecord", ["pw_name", "pw_gecos"])
        monkeypatch.setattr("pwd.getpwuid", lambda uid: MockPwRecord(pw_name="backup", pw_gecos=""))
    except ImportError:
        pass

    # Should synthesize email
    result = resolve_planner_identity(env, None)
    assert result == "Ada <backup@testhost>"


def test_resolve_planner_from_config() -> None:
    """Test that config file user.name and user.email are used."""
    # Mock config with user.name and user.email
    config = ConfigProfile(
        root_dir=Path("/tmp"),
        files=(),
        settings={
            "user": {
                "name": "Test User",
                "email": "test@example.com",
            }
        },
        active_engine=None,
    )

    env = {}  # No env vars

    result = resolve_planner_identity(env, config)
    assert result == "Test User <test@example.com>"


def test_resolve_script_path_prefers_absolute(tmp_path: Path) -> None:
    default = Path("deploy/default.sql")
    absolute = tmp_path / "custom.sql"

    resolved = add_module._resolve_script_path(tmp_path, str(absolute), default)

    assert resolved == absolute


def test_resolve_script_path_coerces_relative(tmp_path: Path) -> None:
    default = Path("deploy/default.sql")

    resolved = add_module._resolve_script_path(tmp_path, "scripts/run.sql", default)

    assert resolved == tmp_path / "scripts" / "run.sql"


def test_ensure_script_path_rejects_existing(tmp_path: Path) -> None:
    target = tmp_path / "deploy" / "exists.sql"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()

    with pytest.raises(CommandError, match="already exists"):
        add_module._ensure_script_path(target)


def test_format_display_path_relative(tmp_path: Path) -> None:
    target = tmp_path / "deploy" / "script.sql"

    assert add_module._format_display_path(target, tmp_path) == "deploy/script.sql"


def test_format_display_path_outside_root(tmp_path: Path) -> None:
    other = tmp_path.parent / "external.sql"
    other.touch()

    expected = os.path.relpath(other, tmp_path).replace(os.sep, "/")
    assert add_module._format_display_path(other, tmp_path) == expected


def test_discover_template_directories_orders_and_deduplicates(tmp_path: Path) -> None:
    config_root = tmp_path / "etc"

    directories = add_module._discover_template_directories(tmp_path, config_root)

    assert directories[0] == tmp_path
    assert directories[1] == tmp_path / "sqitch"
    assert config_root in directories
    assert (config_root / "sqitch") in directories
    # Ensure no duplicates appear
    assert len(directories) == len(set(directories))


def test_resolve_template_content_prefers_absolute_override(tmp_path: Path) -> None:
    template = tmp_path / "custom.sql"
    template.write_text("-- override", encoding="utf-8")

    content = add_module._resolve_template_content(
        kind="deploy",
        engine="sqlite",
        template_dirs=(tmp_path,),
        template_name=str(template),
    )

    assert content == "-- override"


def test_resolve_template_content_absolute_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.sql"

    with pytest.raises(CommandError, match="does not exist"):
        add_module._resolve_template_content(
            kind="deploy",
            engine="sqlite",
            template_dirs=(tmp_path,),
            template_name=str(missing),
        )


def test_resolve_template_content_raises_when_named_template_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(add_module, "resolve_template_path", lambda **_: None)

    with pytest.raises(CommandError, match="could not be located"):
        add_module._resolve_template_content(
            kind="deploy",
            engine="sqlite",
            template_dirs=(tmp_path,),
            template_name="custom",
        )


def test_resolve_template_content_uses_discovered_template(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    template = tmp_path / "custom.tmpl"
    template.write_text("-- template", encoding="utf-8")

    monkeypatch.setattr(add_module, "resolve_template_path", lambda **_: template)

    content = add_module._resolve_template_content(
        kind="deploy",
        engine="sqlite",
        template_dirs=(tmp_path,),
        template_name="custom",
    )

    assert content == "-- template"


def test_resolve_template_content_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(add_module, "resolve_template_path", lambda **_: None)

    content = add_module._resolve_template_content(
        kind="deploy",
        engine="sqlite",
        template_dirs=(tmp_path,),
        template_name=None,
    )

    assert content == default_template_body("deploy")
