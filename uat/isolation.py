"""Environment isolation utilities for UAT scripts.

This module provides helpers to ensure that UAT scripts executing sqitch/sqlitch
commands cannot pollute user configuration files. All subprocess executions must
use isolated environment variables pointing to temporary test directories.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["create_isolated_environment"]


def create_isolated_environment(work_dir: Path) -> dict[str, Any]:
    """Create an isolated environment for subprocess execution.

    This function creates environment variables that prevent sqitch and sqlitch
    from reading or writing to user configuration files. All config/data directories
    are pointed to isolated temporary locations within the test working directory.

    Args:
        work_dir: The working directory for the test (e.g., uat/forward_compat_results)

    Returns:
        A dictionary of environment variables safe for subprocess execution

    Security:
        This is CRITICAL for preventing UAT scripts from polluting user config files.
        Both SQITCH_* and SQLITCH_* variables must be set to override default
        config/data directory discovery.
    """
    # Start with parent environment
    env = os.environ.copy()

    # Resolve work_dir to absolute path to ensure environment variables are absolute
    work_dir = work_dir.resolve()

    # Create isolated temp directories within work_dir
    isolated_root = work_dir / ".isolated"
    isolated_root.mkdir(parents=True, exist_ok=True)

    config_dir = isolated_root / "config"
    system_dir = isolated_root / "system"
    user_dir = isolated_root / "user"

    config_dir.mkdir(exist_ok=True)
    system_dir.mkdir(exist_ok=True)
    user_dir.mkdir(exist_ok=True)

    # Set SQLITCH_* environment variables (SQLitch config isolation)
    env["SQLITCH_CONFIG"] = str(config_dir / "sqlitch.conf")
    env["SQLITCH_SYSTEM_CONFIG"] = str(system_dir / "sqlitch.conf")
    env["SQLITCH_USER_CONFIG"] = str(user_dir / "sqlitch.conf")

    # Set SQITCH_* environment variables (Sqitch config isolation)
    # This prevents pollution of ~/.sqitch/sqitch.conf and /etc/sqitch/sqitch.conf
    env["SQITCH_CONFIG"] = str(config_dir / "sqitch.conf")
    env["SQITCH_SYSTEM_CONFIG"] = str(system_dir / "sqitch.conf")
    env["SQITCH_USER_CONFIG"] = str(user_dir / "sqitch.conf")

    return env
