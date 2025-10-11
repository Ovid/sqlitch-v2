"""Lockdown-specific tests for identity fallbacks and OS variance."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sqlitch.utils.identity import (
    resolve_email,
    resolve_fullname,
    resolve_username,
)


@pytest.fixture(name="config_profile")
def _config_profile() -> MagicMock:
    """Provide a config profile stub with mutable settings."""
    config = MagicMock()
    config.settings = {}
    return config


def test_resolve_fullname_prefers_git_author_over_config(config_profile: MagicMock) -> None:
    """Legacy Git author name should outrank config user.name."""
    config_profile.settings = {"user": {"name": "Config Name"}}
    env = {"GIT_AUTHOR_NAME": "Git Author"}

    result = resolve_fullname(env, config_profile, "fallback")

    assert result == "Git Author"


def test_resolve_email_prefers_git_author_over_config(config_profile: MagicMock) -> None:
    """Legacy Git author email should outrank config user.email."""
    config_profile.settings = {"user": {"email": "config@example.com"}}
    env = {"GIT_AUTHOR_EMAIL": "git@example.com"}

    result = resolve_email(env, config_profile, "fallback")

    assert result == "git@example.com"


def test_resolve_username_uses_win32_api_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """On Windows, win32api should be used when standard sources are unavailable."""

    def raise_os_error() -> None:
        raise OSError("login unavailable")

    monkeypatch.setattr("sqlitch.utils.identity.os.getlogin", raise_os_error)
    monkeypatch.setattr("sqlitch.utils.identity.pwd", None)
    monkeypatch.setattr("sqlitch.utils.identity.sys.platform", "win32")

    mock_win32api = MagicMock()
    mock_win32api.GetUserName.return_value = "win32user"
    monkeypatch.setattr("sqlitch.utils.identity.win32api", mock_win32api, raising=False)

    result = resolve_username({})

    assert result == "win32user"
