"""Identity and change ID generation helpers."""

from __future__ import annotations

import hashlib
import os
import socket
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from sqlitch.config.loader import ConfigProfile

# Platform-specific imports
if sys.platform != "win32":
    try:
        import pwd
    except ImportError:  # pragma: no cover
        pwd = None  # type: ignore[assignment]
else:
    pwd = None  # type: ignore[assignment]
    try:
        import win32api  # type: ignore[import-not-found]
        import win32net  # type: ignore[import-not-found]
        import win32netcon  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover
        win32api = None  # type: ignore[assignment]
        win32net = None  # type: ignore[assignment]
        win32netcon = None  # type: ignore[assignment]

__all__ = [
    "UserIdentity",
    "generate_change_id",
    "resolve_planner_identity",
    "resolve_username",
    "resolve_fullname",
    "resolve_email",
    "get_system_fullname",
    "get_hostname",
]


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Represents user identity from configuration.

    Used to track who planned/committed changes.
    """

    name: str
    email: str


def generate_change_id(
    project: str,
    change: str,
    timestamp: datetime,
    planner_name: str,
    planner_email: str,
    note: str = "",
    requires: tuple[str, ...] = (),
    conflicts: tuple[str, ...] = (),
    uri: str | None = None,
    parent_id: str | None = None,
) -> str:
    r"""Generate a unique change ID using Git-style SHA1 hash.

    Follows Sqitch's format: SHA1 of Git object containing change metadata.
    Sqitch uses Git's object format: 'change <length>\0<content>'

    Args:
        project: Project name
        change: Change name
        timestamp: Timestamp when change was planned (must be timezone-aware)
        planner_name: Name of person who planned the change
        planner_email: Email of person who planned the change
        note: Optional note/description
        requires: Tuple of required change names
        conflicts: Tuple of conflicting change names
        uri: Optional project URI (REQUIRED for Sqitch compatibility)
        parent_id: Optional parent change ID (set for changes with dependencies or rework)

    Returns:
        40-character SHA1 hex digest string

    Examples:
        >>> from datetime import datetime, timezone
        >>> generate_change_id(
        ...     "flipr", "users", datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     "Test User", "test@example.com", "Add users table",
        ...     uri="https://example.com/project/"
        ... )
        'a1b2c3...'  # 40-character hex string
    """
    from sqlitch.utils.time import isoformat_utc

    # Format timestamp in Sqitch format (ISO 8601 with Z suffix)
    timestamp_str = isoformat_utc(timestamp, drop_microseconds=True, use_z_suffix=True)

    # Build info string in Sqitch's format
    # CRITICAL: Field order must match Sqitch exactly for compatibility
    info_parts = [
        f"project {project}",
    ]

    # Add URI if present (Sqitch includes this when available)
    if uri:
        info_parts.append(f"uri {uri}")

    info_parts.append(f"change {change}")

    # Add parent if present (for changes with dependencies or rework)
    if parent_id:
        info_parts.append(f"parent {parent_id}")

    info_parts.extend(
        [
            f"planner {planner_name} <{planner_email}>",
            f"date {timestamp_str}",
        ]
    )

    # Add requires/conflicts if present
    if requires:
        info_parts.append("requires")
        for req in requires:
            info_parts.append(f"  + {req}")

    if conflicts:
        info_parts.append("conflicts")
        for conf in conflicts:
            info_parts.append(f"  - {conf}")

    # Add note if present (empty line before note)
    if note:
        info_parts.append("")
        info_parts.append(note)

    info = "\n".join(info_parts)

    # Use Git's object format: 'change <length>\0<content>'
    info_bytes = info.encode("utf-8")
    git_object = f"change {len(info_bytes)}\x00".encode("utf-8") + info_bytes

    # SHA1 is used for Git-compatible change IDs (matching Sqitch behavior)
    # NOT for cryptographic security - flagged with usedforsecurity=False
    # to suppress security scanner warnings while maintaining Sqitch parity
    return hashlib.sha1(git_object, usedforsecurity=False).hexdigest()


def resolve_planner_identity(
    env: Mapping[str, str],
    config: ConfigProfile | None,
) -> str:
    """Resolve planner identity following Sqitch's exact precedence rules.

    Returns a formatted planner string in the format ``Name <email>``, where
    both components are resolved through cascading fallback chains.

    Args:
        env: Environment variable mapping.
        config: Loaded configuration profile (may be None).

    Returns:
        Formatted string: ``Name <email>``

    Examples:
        >>> resolve_planner_identity(
        ...     {"SQITCH_FULLNAME": "Ada", "SQITCH_EMAIL": "ada@example.com"},
        ...     None
        ... )
        'Ada <ada@example.com>'

        >>> # With config file containing user.name and user.email
        >>> resolve_planner_identity({}, config)
        'Test User <test@example.com>'

        >>> # System defaults with synthesized email
        >>> resolve_planner_identity({}, None)
        'John Smith <john@hostname>'
    """
    username = resolve_username(env)
    fullname = resolve_fullname(env, config, username)
    email = resolve_email(env, config, username)

    return f"{fullname} <{email}>"


def resolve_username(env: Mapping[str, str]) -> str:
    """Resolve username for fallback scenarios.

    Precedence (highest to lowest):
        1. ``$SQITCH_ORIG_SYSUSER`` (internal)
        2. ``getlogin()`` - current login name
        3. ``getpwuid()`` - username from real user ID (Unix/macOS)
        4. ``$LOGNAME`` environment variable
        5. ``$USER`` environment variable
        6. ``$USERNAME`` environment variable
        7. ``Win32::LoginName()`` on Windows
        8. ``"sqitch"`` as last resort

    Args:
        env: Environment variable mapping.

    Returns:
        Username string (never None).
    """
    # Check SQITCH_ORIG_SYSUSER (internal)
    if env.get("SQITCH_ORIG_SYSUSER"):
        return env["SQITCH_ORIG_SYSUSER"]

    # Try getlogin()
    try:
        login = os.getlogin()
        if login:
            return login
    except (OSError, AttributeError):  # pragma: no cover
        pass

    # Try getpwuid() on Unix/macOS
    if pwd is not None:
        try:
            return pwd.getpwuid(os.getuid()).pw_name
        except (KeyError, AttributeError):  # pragma: no cover
            pass

    # Check environment variables in order
    for var in ("LOGNAME", "USER", "USERNAME"):
        value = env.get(var)
        if value:
            return value

    # Windows-specific
    if sys.platform == "win32" and win32api is not None:
        try:
            # pylint: disable=possibly-used-before-assignment  # Guarded by sys.platform check
            return win32api.GetUserName()
        except Exception:  # pragma: no cover - Windows-specific
            pass

    # Last resort fallback
    return "sqitch"


def resolve_fullname(
    env: Mapping[str, str],
    config: ConfigProfile | None,
    username_fallback: str,
) -> str:
    """Resolve full name for planner identity.

    Precedence (highest to lowest):
        1. ``$SQITCH_FULLNAME`` environment variable
        2. Legacy ``$SQLITCH_USER_NAME`` (backward compatibility)
        3. ``$SQITCH_ORIG_FULLNAME`` (internal)
        4. Legacy ``$GIT_AUTHOR_NAME`` (backward compatibility)
        5. ``user.name`` from config
        6. Full name from system (GECOS field on Unix/macOS, UserInfo on Windows)
        7. ``username_fallback``

    Args:
        env: Environment variable mapping.
        config: Loaded configuration profile (may be None).
        username_fallback: Username to use if no other source available.

    Returns:
        Full name string (never None).
    """
    value = env.get("SQLITCH_FULLNAME")
    if value:
        return value

    # Check SQITCH_FULLNAME
    value = env.get("SQITCH_FULLNAME")
    if value:
        return value

    # BACKWARD COMPATIBILITY: Prefer SQLITCH_USER_NAME if supplied
    value = env.get("SQLITCH_USER_NAME")
    if value:
        return value

    # Check SQITCH_ORIG_FULLNAME (internal)
    value = env.get("SQITCH_ORIG_FULLNAME")
    if value:
        return value

    value = env.get("GIT_AUTHOR_NAME")
    if value:
        return value

    if config is not None:
        user_section = config.settings.get("user", {})
        value = user_section.get("name")
        if value:
            return value

    # Try system full name
    system_name = get_system_fullname(username_fallback)
    if system_name:
        return system_name

    # Fallback to username
    return username_fallback


def resolve_email(
    env: Mapping[str, str],
    config: ConfigProfile | None,
    username: str,
) -> str:
    """Resolve email for planner identity.

    Precedence (highest to lowest):
        1. ``$SQITCH_EMAIL`` environment variable
        2. Legacy ``$SQLITCH_USER_EMAIL`` (backward compatibility)
        3. ``$SQITCH_ORIG_EMAIL`` (internal)
        4. Legacy ``$GIT_AUTHOR_EMAIL`` (backward compatibility)
        5. ``user.email`` from config
        6. Legacy ``$EMAIL`` (backward compatibility)
        7. Synthesized as ``<username>@<hostname>``

    Args:
        env: Environment variable mapping.
        config: Loaded configuration profile (may be None).
        username: Username to use for email synthesis.

    Returns:
        Email string (never None).
    """
    # Prefer SQLITCH_EMAIL overrides
    value = env.get("SQLITCH_EMAIL")
    if value:
        return value

    # Check SQITCH_EMAIL
    value = env.get("SQITCH_EMAIL")
    if value:
        return value

    # BACKWARD COMPATIBILITY: Prefer SQLITCH_USER_EMAIL before older fallbacks
    value = env.get("SQLITCH_USER_EMAIL")
    if value:
        return value

    # Check SQITCH_ORIG_EMAIL (internal)
    value = env.get("SQITCH_ORIG_EMAIL")
    if value:
        return value

    value = env.get("GIT_AUTHOR_EMAIL")
    if value:
        return value

    if config is not None:
        user_section = config.settings.get("user", {})
        value = user_section.get("email")
        if value:
            return value

    value = env.get("EMAIL")
    if value:
        return value

    # Synthesize email
    hostname = get_hostname()
    return f"{username}@{hostname}"


def get_system_fullname(username: str) -> str | None:
    """Get full name from system user database.

    On Unix/macOS: Parse GECOS field from passwd database.
    On Windows: Use Win32::UserInfo if available.

    Args:
        username: Username to look up.

    Returns:
        Full name if found, None otherwise.
    """
    if sys.platform == "win32" and win32net is not None:
        try:
            # pylint: disable=possibly-used-before-assignment  # Guarded by sys.platform check
            user_info = win32net.NetUserGetInfo(None, username, 2)
            full_name = user_info.get("full_name", "").strip()
            if full_name:
                return full_name
        except Exception:  # pragma: no cover - Windows-specific
            pass
    elif pwd is not None:
        try:
            pw_record = pwd.getpwnam(username)
            gecos = pw_record.pw_gecos

            # GECOS format: Full Name,Office,Office Phone,Home Phone
            # We want just the first field
            if gecos:
                parts = gecos.split(",")
                full_name = parts[0].strip()
                if full_name:
                    return full_name
        except (KeyError, AttributeError):  # pragma: no cover
            pass

    return None


def get_hostname() -> str:
    """Get the system hostname.

    Returns:
        Hostname string (defaults to "localhost" on error).
    """
    try:
        return socket.gethostname()
    except Exception:  # pragma: no cover
        return "localhost"
