"""Edge case tests for identity module to reach 90%+ coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from sqlitch.utils.identity import (
    generate_change_id,
    get_hostname,
    get_system_fullname,
    resolve_email,
    resolve_fullname,
    resolve_planner_identity,
    resolve_username,
)


def test_generate_change_id_with_requires_and_conflicts() -> None:
    """Test change ID generation with requires and conflicts."""
    from datetime import datetime, timezone

    change_id = generate_change_id(
        project="testproj",
        change="testchange",
        timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        planner_name="Test User",
        planner_email="test@example.com",
        note="Test note",
        requires=("dep1", "dep2"),
        conflicts=("conflict1",),
    )

    assert len(change_id) == 40
    assert change_id.isalnum()


def test_generate_change_id_with_empty_note() -> None:
    """Test change ID generation with empty note."""
    from datetime import datetime, timezone

    change_id = generate_change_id(
        project="testproj",
        change="testchange",
        timestamp=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        planner_name="Test User",
        planner_email="test@example.com",
        note="",
    )

    assert len(change_id) == 40


def test_resolve_username_with_logname_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test username resolution with LOGNAME environment variable."""

    def raise_os_error() -> None:
        raise OSError("getlogin failed")

    monkeypatch.setattr("sqlitch.utils.identity.os.getlogin", raise_os_error)
    monkeypatch.setattr("sqlitch.utils.identity.pwd", None)

    result = resolve_username({"LOGNAME": "logname_user"})
    assert result == "logname_user"


def test_resolve_username_with_user_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test username resolution with USER environment variable."""

    def raise_os_error() -> None:
        raise OSError("getlogin failed")

    monkeypatch.setattr("sqlitch.utils.identity.os.getlogin", raise_os_error)
    monkeypatch.setattr("sqlitch.utils.identity.pwd", None)

    result = resolve_username({"USER": "user_env"})
    assert result == "user_env"


def test_resolve_username_with_username_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test username resolution with USERNAME environment variable."""

    def raise_os_error() -> None:
        raise OSError("getlogin failed")

    monkeypatch.setattr("sqlitch.utils.identity.os.getlogin", raise_os_error)
    monkeypatch.setattr("sqlitch.utils.identity.pwd", None)

    result = resolve_username({"USERNAME": "username_env"})
    assert result == "username_env"


def test_resolve_username_fallback_to_sqitch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test username resolution fallback to 'sqitch' when all else fails."""

    def raise_os_error() -> None:
        raise OSError("getlogin failed")

    monkeypatch.setattr("sqlitch.utils.identity.os.getlogin", raise_os_error)
    monkeypatch.setattr("sqlitch.utils.identity.pwd", None)

    result = resolve_username({})
    assert result == "sqitch"


def test_resolve_username_with_sqitch_orig_sysuser() -> None:
    """Test username resolution with SQITCH_ORIG_SYSUSER."""
    result = resolve_username({"SQITCH_ORIG_SYSUSER": "orig_user", "LOGNAME": "logname"})
    assert result == "orig_user"


def test_resolve_fullname_with_sqlitch_fullname_env() -> None:
    """Test fullname resolution with SQLITCH_FULLNAME."""
    result = resolve_fullname({"SQLITCH_FULLNAME": "SQLitch User"}, None, "fallback")
    assert result == "SQLitch User"


def test_resolve_fullname_with_sqitch_fullname_env() -> None:
    """Test fullname resolution with SQITCH_FULLNAME."""
    result = resolve_fullname({"SQITCH_FULLNAME": "Sqitch User"}, None, "fallback")
    assert result == "Sqitch User"


def test_resolve_fullname_with_sqlitch_user_name() -> None:
    """Test fullname resolution with SQLITCH_USER_NAME."""
    result = resolve_fullname({"SQLITCH_USER_NAME": "SQLitch Name"}, None, "fallback")
    assert result == "SQLitch Name"


def test_resolve_fullname_with_sqitch_orig_fullname() -> None:
    """Test fullname resolution with SQITCH_ORIG_FULLNAME."""
    result = resolve_fullname({"SQITCH_ORIG_FULLNAME": "Orig Name"}, None, "fallback")
    assert result == "Orig Name"


def test_resolve_fullname_precedence() -> None:
    """Test that SQLITCH_FULLNAME takes precedence over SQITCH_FULLNAME."""
    env = {
        "SQLITCH_FULLNAME": "SQLitch Name",
        "SQITCH_FULLNAME": "Sqitch Name",
    }
    result = resolve_fullname(env, None, "fallback")
    assert result == "SQLitch Name"


def test_resolve_fullname_fallback_to_username() -> None:
    """Test fullname resolution falls back to username when nothing else available."""
    result = resolve_fullname({}, None, "testuser")
    assert result == "testuser"


def test_resolve_fullname_with_config_user_name() -> None:
    """Test fullname resolution from config user.name."""
    config = MagicMock()
    config.settings = {"user": {"name": "Config User"}}

    result = resolve_fullname({}, config, "fallback")
    assert result == "Config User"


def test_resolve_email_with_sqlitch_email() -> None:
    """Test email resolution with SQLITCH_EMAIL."""
    result = resolve_email({"SQLITCH_EMAIL": "sqlitch@example.com"}, None, "user")
    assert result == "sqlitch@example.com"


def test_resolve_email_with_sqitch_email() -> None:
    """Test email resolution with SQITCH_EMAIL."""
    result = resolve_email({"SQITCH_EMAIL": "sqitch@example.com"}, None, "user")
    assert result == "sqitch@example.com"


def test_resolve_email_with_sqlitch_user_email() -> None:
    """Test email resolution with SQLITCH_USER_EMAIL."""
    result = resolve_email({"SQLITCH_USER_EMAIL": "sqlitchuser@example.com"}, None, "user")
    assert result == "sqlitchuser@example.com"


def test_resolve_email_with_sqitch_orig_email() -> None:
    """Test email resolution with SQITCH_ORIG_EMAIL."""
    result = resolve_email({"SQITCH_ORIG_EMAIL": "orig@example.com"}, None, "user")
    assert result == "orig@example.com"


def test_resolve_email_with_email_env() -> None:
    """Test email resolution with EMAIL environment variable."""
    result = resolve_email({"EMAIL": "email@example.com"}, None, "user")
    assert result == "email@example.com"


def test_resolve_email_precedence() -> None:
    """Test that SQLITCH_EMAIL takes precedence over SQITCH_EMAIL."""
    env = {
        "SQLITCH_EMAIL": "sqlitch@example.com",
        "SQITCH_EMAIL": "sqitch@example.com",
    }
    result = resolve_email(env, None, "user")
    assert result == "sqlitch@example.com"


def test_resolve_email_synthesizes_from_username(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test email synthesis when no configuration available."""
    monkeypatch.setattr("sqlitch.utils.identity.get_hostname", lambda: "testhost")

    result = resolve_email({}, None, "testuser")
    assert result == "testuser@testhost"


def test_resolve_email_with_config() -> None:
    """Test email resolution from config user.email."""
    config = MagicMock()
    config.settings = {"user": {"email": "config@example.com"}}

    result = resolve_email({}, config, "user")
    assert result == "config@example.com"


def test_resolve_planner_identity_formats_correctly() -> None:
    """Test planner identity formatting."""
    env = {
        "SQITCH_FULLNAME": "Test User",
        "SQITCH_EMAIL": "test@example.com",
    }

    result = resolve_planner_identity(env, None)
    assert result == "Test User <test@example.com>"


def test_resolve_planner_identity_with_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test planner identity with config."""
    config = MagicMock()
    config.settings = {"user": {"name": "Config User", "email": "config@example.com"}}

    monkeypatch.setattr("sqlitch.utils.identity.resolve_username", lambda env: "testuser")

    result = resolve_planner_identity({}, config)
    assert result == "Config User <config@example.com>"


def test_get_hostname_returns_value() -> None:
    """Test get_hostname returns a valid hostname."""
    hostname = get_hostname()
    assert isinstance(hostname, str)
    assert len(hostname) > 0


def test_get_hostname_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_hostname fallback on exception."""

    def raise_error() -> None:
        raise OSError("socket error")

    monkeypatch.setattr("socket.gethostname", raise_error)

    hostname = get_hostname()
    assert hostname == "localhost"


def test_get_system_fullname_returns_none_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_system_fullname returns None when system info unavailable."""
    monkeypatch.setattr("sqlitch.utils.identity.pwd", None)
    monkeypatch.setattr("sqlitch.utils.identity.win32net", None, raising=False)

    result = get_system_fullname("testuser")
    assert result is None


def test_get_system_fullname_handles_pwd_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_system_fullname handles pwd.getpwnam error."""
    mock_pwd = MagicMock()
    mock_pwd.getpwnam.side_effect = KeyError("user not found")
    monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

    result = get_system_fullname("nonexistent")
    assert result is None


def test_get_system_fullname_parses_gecos_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_system_fullname parses GECOS field correctly."""
    mock_pwd = MagicMock()
    mock_record = MagicMock()
    mock_record.pw_gecos = "Full Name,Office,1234,5678"
    mock_pwd.getpwnam.return_value = mock_record
    monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

    result = get_system_fullname("testuser")
    assert result == "Full Name"


def test_get_system_fullname_handles_empty_gecos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_system_fullname handles empty GECOS field."""
    mock_pwd = MagicMock()
    mock_record = MagicMock()
    mock_record.pw_gecos = ""
    mock_pwd.getpwnam.return_value = mock_record
    monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

    result = get_system_fullname("testuser")
    assert result is None


def test_get_system_fullname_handles_whitespace_gecos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_system_fullname handles whitespace-only GECOS field."""
    mock_pwd = MagicMock()
    mock_record = MagicMock()
    mock_record.pw_gecos = "   ,Office,1234,5678"
    mock_pwd.getpwnam.return_value = mock_record
    monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

    result = get_system_fullname("testuser")
    assert result is None


@pytest.mark.skipif(
    "sys.platform != 'win32'",
    reason="Windows-specific test",
)
def test_get_system_fullname_uses_win32net() -> None:
    """Test get_system_fullname uses Win32 API on Windows."""
    # This test will only run on Windows platforms
    # On non-Windows, it will be skipped
    result = get_system_fullname("testuser")
    # Just verify it doesn't crash; actual behavior depends on Windows system
    assert result is None or isinstance(result, str)


def test_resolve_username_getpwuid_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test resolve_username handles getpwuid KeyError."""

    def raise_os_error() -> None:
        raise OSError("getlogin failed")

    mock_pwd = MagicMock()
    mock_pwd.getpwuid.side_effect = KeyError("uid not found")

    monkeypatch.setattr("sqlitch.utils.identity.os.getlogin", raise_os_error)
    monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

    result = resolve_username({"LOGNAME": "testuser"})
    assert result == "testuser"


def test_resolve_username_handles_attribute_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test resolve_username handles AttributeError from getlogin."""

    def raise_attr_error() -> None:
        raise AttributeError("no getlogin")

    monkeypatch.setattr("sqlitch.utils.identity.os.getlogin", raise_attr_error)
    monkeypatch.setattr("sqlitch.utils.identity.pwd", None)

    result = resolve_username({"USER": "testuser"})
    assert result == "testuser"


def test_get_system_fullname_handles_attribute_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_system_fullname handles AttributeError from pwd."""
    mock_pwd = MagicMock()
    mock_pwd.getpwnam.side_effect = AttributeError("no pw_gecos")
    monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

    result = get_system_fullname("testuser")
    assert result is None
