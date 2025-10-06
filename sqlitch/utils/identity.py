"""Identity and change ID generation helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

__all__ = ["UserIdentity", "generate_change_id"]


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Represents user identity from configuration.
    
    Used to track who planned/committed changes.
    """
    
    name: str
    email: str


def generate_change_id(project: str, change: str, timestamp: datetime) -> str:
    """Generate a unique change ID using SHA1 hash.
    
    Follows Sqitch's format: SHA1(project:change:ISO8601_timestamp)
    
    Args:
        project: Project name
        change: Change name
        timestamp: Timestamp when change was planned (must be timezone-aware)
        
    Returns:
        40-character SHA1 hex digest string
        
    Examples:
        >>> from datetime import datetime, timezone
        >>> generate_change_id("flipr", "users", datetime(2025, 1, 1, tzinfo=timezone.utc))
        'a1b2c3...'  # 40-character hex string
    """
    # Sqitch format: project:change:ISO8601_timestamp
    input_string = f"{project}:{change}:{timestamp.isoformat()}"
    return hashlib.sha1(input_string.encode("utf-8")).hexdigest()
