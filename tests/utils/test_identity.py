"""Tests for identity helpers."""

from __future__ import annotations

import os
import sys
import pytest
import hashlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from sqlitch.utils.identity import (
    UserIdentity,
    generate_change_id,
    resolve_planner_identity,
    resolve_username,
    resolve_fullname,
    resolve_email,
    get_system_fullname,
    get_hostname,
)


class TestUserIdentity:
    """Test UserIdentity helper functions."""

    def test_creates_from_user_config(self) -> None:
        """Should create from user.name and user.email config."""
        identity = UserIdentity(name="Alice Smith", email="alice@example.com")
        assert identity.name == "Alice Smith"
        assert identity.email == "alice@example.com"

    def test_is_frozen_dataclass(self) -> None:
        """UserIdentity should be immutable."""
        identity = UserIdentity(name="Bob", email="bob@example.com")
        with pytest.raises(AttributeError):
            identity.name = "Changed"  # type: ignore[misc]

    def test_has_slots(self) -> None:
        """UserIdentity should use __slots__ for memory efficiency."""
        identity = UserIdentity(name="Carol", email="carol@example.com")
        assert not hasattr(identity, "__dict__")


class TestGenerateChangeId:
    """Test generate_change_id function."""

    def test_generates_sha1_hash(self) -> None:
        """Should return SHA1 hash hex digest."""
        change_id = generate_change_id(
            project="flipr",
            change="users",
            timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        # SHA1 produces 40-character hex string
        assert len(change_id) == 40
        assert all(c in "0123456789abcdef" for c in change_id)

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs should produce same output."""
        timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        id1 = generate_change_id("flipr", "users", timestamp)
        id2 = generate_change_id("flipr", "users", timestamp)

        assert id1 == id2

    def test_different_inputs_different_outputs(self) -> None:
        """Different inputs should produce different outputs."""
        timestamp = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        id1 = generate_change_id("flipr", "users", timestamp)
        id2 = generate_change_id("flipr", "schema", timestamp)

        assert id1 != id2

    def test_matches_sqitch_format(self) -> None:
        """Should match Sqitch's SHA1(project + change + timestamp) format."""
        project = "flipr"
        change = "users"
        timestamp = datetime(2025, 1, 1, 12, 30, 45, tzinfo=timezone.utc)

        # Sqitch uses ISO 8601 format: project:change:YYYY-MM-DDTHH:MM:SSZ
        expected_input = f"{project}:{change}:{timestamp.isoformat()}"
        expected_hash = hashlib.sha1(expected_input.encode("utf-8")).hexdigest()

        result = generate_change_id(project, change, timestamp)
        assert result == expected_hash


class TestResolvePlannerIdentity:
    """Test resolve_planner_identity function."""

    def test_formats_as_name_email(self) -> None:
        """Should format as 'Name <email>'."""
        env = {"SQITCH_FULLNAME": "Alice", "SQITCH_EMAIL": "alice@example.com"}
        result = resolve_planner_identity(env, None)
        assert result == "Alice <alice@example.com>"

    def test_uses_config_when_env_missing(self) -> None:
        """Should use config when environment variables missing."""
        config = MagicMock()
        config.settings = {"user": {"name": "Bob", "email": "bob@example.com"}}

        result = resolve_planner_identity({}, config)
        assert result == "Bob <bob@example.com>"

    def test_synthesizes_email_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should synthesize email from username@hostname."""
        monkeypatch.setattr("os.getlogin", lambda: "testuser")
        monkeypatch.setattr("socket.gethostname", lambda: "testhost")

        config = MagicMock()
        config.settings = {"user": {"name": "Test User"}}

        result = resolve_planner_identity({}, config)
        assert result == "Test User <testuser@testhost>"


class TestResolveUsername:
    """Test resolve_username function."""

    def test_prefers_sqitch_orig_sysuser(self) -> None:
        """Should prefer SQITCH_ORIG_SYSUSER over all other sources."""
        env = {
            "SQITCH_ORIG_SYSUSER": "override_user",
            "LOGNAME": "logname_user",
            "USER": "user_var",
        }
        result = resolve_username(env)
        assert result == "override_user"

    def test_uses_getlogin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use getlogin() when no env var set."""
        monkeypatch.setattr("os.getlogin", lambda: "login_user")
        result = resolve_username({})
        assert result == "login_user"

    def test_uses_getpwuid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use pwd.getpwuid() when getlogin() fails."""
        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        monkeypatch.setattr("os.getlogin", MagicMock(side_effect=OSError))
        mock_pw = MagicMock()
        mock_pw.pw_name = "pwuid_user"
        mock_pwd = MagicMock()
        mock_pwd.getpwuid.return_value = mock_pw
        monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = resolve_username({})
        assert result == "pwuid_user"

    def test_falls_back_to_logname(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use $LOGNAME when getlogin() fails."""
        monkeypatch.setattr("os.getlogin", MagicMock(side_effect=OSError))
        # Mock pwd.getpwuid to also fail
        if sys.platform != "win32":
            mock_pwd = MagicMock()
            mock_pwd.getpwuid.side_effect = KeyError("User not found")
            monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        env = {"LOGNAME": "logname_user"}
        result = resolve_username(env)
        assert result == "logname_user"

    def test_falls_back_to_user(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use $USER when $LOGNAME missing."""
        monkeypatch.setattr("os.getlogin", MagicMock(side_effect=OSError))
        # Mock pwd.getpwuid to also fail
        if sys.platform != "win32":
            mock_pwd = MagicMock()
            mock_pwd.getpwuid.side_effect = KeyError("User not found")
            monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        env = {"USER": "user_var"}
        result = resolve_username(env)
        assert result == "user_var"

    def test_falls_back_to_username(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use $USERNAME when $USER missing."""
        monkeypatch.setattr("os.getlogin", MagicMock(side_effect=OSError))
        # Mock pwd.getpwuid to also fail
        if sys.platform != "win32":
            mock_pwd = MagicMock()
            mock_pwd.getpwuid.side_effect = KeyError("User not found")
            monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        env = {"USERNAME": "username_var"}
        result = resolve_username(env)
        assert result == "username_var"

    def test_fallback_to_sqitch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should fallback to 'sqitch' when all else fails."""
        monkeypatch.setattr("os.getlogin", MagicMock(side_effect=OSError))
        # Mock pwd.getpwuid to also fail
        if sys.platform != "win32":
            mock_pwd = MagicMock()
            mock_pwd.getpwuid.side_effect = KeyError("User not found")
            monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = resolve_username({})
        assert result == "sqitch"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_uses_win32_api(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use Win32 API on Windows."""
        monkeypatch.setattr("os.getlogin", MagicMock(side_effect=OSError))
        mock_win32 = MagicMock()
        mock_win32.GetUserName.return_value = "win_user"
        monkeypatch.setattr("sqlitch.utils.identity.win32api", mock_win32)

        result = resolve_username({})
        assert result == "win_user"


class TestResolveFullname:
    """Test resolve_fullname function."""

    def test_prefers_sqitch_fullname(self) -> None:
        """Should prefer SQITCH_FULLNAME over all other sources."""
        env = {"SQITCH_FULLNAME": "Env Name"}
        config = MagicMock()
        config.settings = {"user": {"name": "Config Name"}}

        result = resolve_fullname(env, config, "fallback")
        assert result == "Env Name"

    def test_uses_config_user_name(self) -> None:
        """Should use config user.name when env missing."""
        config = MagicMock()
        config.settings = {"user": {"name": "Config Name"}}

        result = resolve_fullname({}, config, "fallback")
        assert result == "Config Name"

    def test_uses_sqitch_orig_fullname(self) -> None:
        """Should use SQITCH_ORIG_FULLNAME when config missing."""
        env = {"SQITCH_ORIG_FULLNAME": "Orig Name"}
        result = resolve_fullname(env, None, "fallback")
        assert result == "Orig Name"

    def test_uses_system_fullname(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use system full name when available."""
        # Mock pwd module if on Unix
        if sys.platform != "win32":
            mock_pw = MagicMock()
            mock_pw.pw_gecos = "System Name,Office,Phone,Home"
            mock_pwd = MagicMock()
            mock_pwd.getpwnam.return_value = mock_pw
            monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = resolve_fullname({}, None, "testuser")
        # Either system name or fallback depending on platform
        assert result in ("System Name", "testuser")

    def test_falls_back_to_sqlitch_user_name(self) -> None:
        """Should use legacy SQLITCH_USER_NAME."""
        env = {"SQLITCH_USER_NAME": "Legacy Name"}
        result = resolve_fullname(env, None, "fallback")
        assert result == "Legacy Name"

    def test_falls_back_to_git_author_name(self) -> None:
        """Should use legacy GIT_AUTHOR_NAME."""
        env = {"GIT_AUTHOR_NAME": "Git Name"}
        result = resolve_fullname(env, None, "fallback")
        assert result == "Git Name"

    def test_falls_back_to_username(self) -> None:
        """Should fallback to username when all else fails."""
        result = resolve_fullname({}, None, "fallback_user")
        assert result == "fallback_user"

    def test_handles_missing_user_section_in_config(self) -> None:
        """Should handle config with no user section."""
        config = MagicMock()
        config.settings = {}  # No user section

        result = resolve_fullname({}, config, "fallback_user")
        assert result == "fallback_user"

    def test_handles_empty_name_in_config(self) -> None:
        """Should handle config with empty name value."""
        config = MagicMock()
        config.settings = {"user": {"name": ""}}  # Empty name

        result = resolve_fullname({}, config, "fallback_user")
        assert result == "fallback_user"


class TestResolveEmail:
    """Test resolve_email function."""

    def test_prefers_sqitch_email(self) -> None:
        """Should prefer SQITCH_EMAIL over all other sources."""
        env = {"SQITCH_EMAIL": "env@example.com"}
        config = MagicMock()
        config.settings = {"user": {"email": "config@example.com"}}

        result = resolve_email(env, config, "testuser")
        assert result == "env@example.com"

    def test_uses_config_user_email(self) -> None:
        """Should use config user.email when env missing."""
        config = MagicMock()
        config.settings = {"user": {"email": "config@example.com"}}

        result = resolve_email({}, config, "testuser")
        assert result == "config@example.com"

    def test_uses_sqitch_orig_email(self) -> None:
        """Should use SQITCH_ORIG_EMAIL when config missing."""
        env = {"SQITCH_ORIG_EMAIL": "orig@example.com"}
        result = resolve_email(env, None, "testuser")
        assert result == "orig@example.com"

    def test_falls_back_to_sqlitch_user_email(self) -> None:
        """Should use legacy SQLITCH_USER_EMAIL."""
        env = {"SQLITCH_USER_EMAIL": "legacy@example.com"}
        result = resolve_email(env, None, "testuser")
        assert result == "legacy@example.com"

    def test_falls_back_to_git_author_email(self) -> None:
        """Should use legacy GIT_AUTHOR_EMAIL."""
        env = {"GIT_AUTHOR_EMAIL": "git@example.com"}
        result = resolve_email(env, None, "testuser")
        assert result == "git@example.com"

    def test_falls_back_to_email_var(self) -> None:
        """Should use legacy EMAIL env var."""
        env = {"EMAIL": "email@example.com"}
        result = resolve_email(env, None, "testuser")
        assert result == "email@example.com"

    def test_synthesizes_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should synthesize email from username@hostname."""
        monkeypatch.setattr("socket.gethostname", lambda: "testhost")
        result = resolve_email({}, None, "testuser")
        assert result == "testuser@testhost"

    def test_handles_missing_user_section_in_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should handle config with no user section."""
        monkeypatch.setattr("socket.gethostname", lambda: "testhost")
        config = MagicMock()
        config.settings = {}  # No user section

        result = resolve_email({}, config, "testuser")
        assert result == "testuser@testhost"  # Should synthesize

    def test_handles_empty_email_in_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should handle config with empty email value."""
        monkeypatch.setattr("socket.gethostname", lambda: "testhost")
        config = MagicMock()
        config.settings = {"user": {"email": ""}}  # Empty email

        result = resolve_email({}, config, "testuser")
        assert result == "testuser@testhost"


class TestGetSystemFullname:
    """Test get_system_fullname function."""

    def test_parses_gecos_field_unix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should parse GECOS field on Unix/macOS."""
        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        mock_pw = MagicMock()
        mock_pw.pw_gecos = "John Doe,Room 123,555-1234,555-5678"
        mock_pwd = MagicMock()
        mock_pwd.getpwnam.return_value = mock_pw
        monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = get_system_fullname("testuser")
        assert result == "John Doe"

    def test_parses_gecos_name_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should handle GECOS with just name."""
        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        mock_pw = MagicMock()
        mock_pw.pw_gecos = "Jane Smith"
        mock_pwd = MagicMock()
        mock_pwd.getpwnam.return_value = mock_pw
        monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = get_system_fullname("testuser")
        assert result == "Jane Smith"

    def test_handles_gecos_with_empty_first_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None when first GECOS field is empty."""
        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        mock_pw = MagicMock()
        mock_pw.pw_gecos = ",Room 123,555-1234"
        mock_pwd = MagicMock()
        mock_pwd.getpwnam.return_value = mock_pw
        monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = get_system_fullname("testuser")
        assert result is None

    def test_returns_none_when_gecos_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None when GECOS is empty."""
        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        mock_pw = MagicMock()
        mock_pw.pw_gecos = ""
        mock_pwd = MagicMock()
        mock_pwd.getpwnam.return_value = mock_pw
        monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = get_system_fullname("testuser")
        assert result is None

    def test_returns_none_when_user_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None when user lookup fails."""
        if sys.platform == "win32":
            pytest.skip("Unix-only test")

        mock_pwd = MagicMock()
        mock_pwd.getpwnam.side_effect = KeyError("User not found")
        monkeypatch.setattr("sqlitch.utils.identity.pwd", mock_pwd)

        result = get_system_fullname("nonexistent")
        assert result is None

    def test_returns_none_when_pwd_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None when pwd module unavailable."""
        monkeypatch.setattr("sqlitch.utils.identity.pwd", None)
        result = get_system_fullname("testuser")
        assert result is None

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_uses_win32_userinfo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use Win32 UserInfo on Windows."""
        mock_win32net = MagicMock()
        mock_win32net.NetUserGetInfo.return_value = {"full_name": "Windows User"}
        monkeypatch.setattr("sqlitch.utils.identity.win32net", mock_win32net)

        result = get_system_fullname("testuser")
        assert result == "Windows User"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    def test_returns_none_when_win32_full_name_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return None when Windows full_name is empty."""
        mock_win32net = MagicMock()
        mock_win32net.NetUserGetInfo.return_value = {"full_name": "  "}
        monkeypatch.setattr("sqlitch.utils.identity.win32net", mock_win32net)

        result = get_system_fullname("testuser")
        assert result is None


class TestGetHostname:
    """Test get_hostname function."""

    def test_returns_hostname(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return system hostname."""
        monkeypatch.setattr("socket.gethostname", lambda: "test.example.com")
        result = get_hostname()
        assert result == "test.example.com"
