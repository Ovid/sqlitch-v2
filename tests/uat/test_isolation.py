"""Test suite for UAT environment isolation.

This module validates that UAT scripts cannot pollute user configuration files
by ensuring all subprocess executions use properly isolated environments.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from uat.lib.isolation import create_isolated_environment


def test_create_isolated_environment_returns_copy_of_parent_env(tmp_path: Path):
    """Verify that isolated environment starts with parent environment variables."""
    # Set a unique test variable
    test_var = "SQLITCH_UAT_TEST_UNIQUE_VAR"
    test_value = "test_value_12345"
    os.environ[test_var] = test_value

    try:
        env = create_isolated_environment(tmp_path)

        # Should preserve parent environment
        assert test_var in env
        assert env[test_var] == test_value
    finally:
        os.environ.pop(test_var, None)


def test_create_isolated_environment_sets_all_sqlitch_vars(tmp_path: Path):
    """Verify all SQLITCH_* config variables are set to isolated locations."""
    env = create_isolated_environment(tmp_path)

    # All three SQLITCH_* variables must be set
    assert "SQLITCH_CONFIG" in env
    assert "SQLITCH_SYSTEM_CONFIG" in env
    assert "SQLITCH_USER_CONFIG" in env

    # All should point to isolated temp directories
    config_path = Path(env["SQLITCH_CONFIG"])
    system_path = Path(env["SQLITCH_SYSTEM_CONFIG"])
    user_path = Path(env["SQLITCH_USER_CONFIG"])

    # SQLITCH_CONFIG points to work_dir/sqitch.conf (shared with Sqitch)
    # This allows Sqitch and SQLitch to interoperate on the same project config
    assert config_path == tmp_path / "sqitch.conf"

    # System and user configs remain isolated
    isolated_root = tmp_path / ".isolated"
    assert system_path.parent == isolated_root / "system"
    assert user_path.parent == isolated_root / "user"

    # Verify filenames (with descriptive names for debugging)
    assert config_path.name == "sqitch.conf"
    assert system_path.name == "system.conf"
    assert user_path.name == "user.conf"


def test_create_isolated_environment_sets_all_sqitch_vars(tmp_path: Path):
    """Verify all SQITCH_* config variables are set to isolated locations.

    This is CRITICAL: Without these variables, sqitch will read/write to
    ~/.sqitch/sqitch.conf, potentially destroying user configuration!
    """
    env = create_isolated_environment(tmp_path)

    # All three SQITCH_* variables must be set
    assert "SQITCH_CONFIG" in env
    assert "SQITCH_SYSTEM_CONFIG" in env
    assert "SQITCH_USER_CONFIG" in env

    # All should point to isolated temp directories
    config_path = Path(env["SQITCH_CONFIG"])
    system_path = Path(env["SQITCH_SYSTEM_CONFIG"])
    user_path = Path(env["SQITCH_USER_CONFIG"])

    # SQITCH_CONFIG points to work_dir/sqitch.conf (shared with SQLitch)
    # This allows Sqitch and SQLitch to interoperate on the same project config
    assert config_path == tmp_path / "sqitch.conf"

    # System and user configs remain isolated
    isolated_root = tmp_path / ".isolated"
    assert system_path.parent == isolated_root / "system"
    assert user_path.parent == isolated_root / "user"

    # Verify filenames (with descriptive names for debugging)
    assert config_path.name == "sqitch.conf"
    assert system_path.name == "system.conf"
    assert user_path.name == "user.conf"


def test_create_isolated_environment_creates_directories(tmp_path: Path):
    """Verify that isolation directories are created automatically."""
    create_isolated_environment(tmp_path)

    isolated_root = tmp_path / ".isolated"
    assert isolated_root.exists()
    assert isolated_root.is_dir()

    # All three subdirectories should exist
    assert (isolated_root / "config").exists()
    assert (isolated_root / "system").exists()
    assert (isolated_root / "user").exists()


def test_create_isolated_environment_does_not_modify_parent_env(tmp_path: Path):
    """Verify that creating isolated env doesn't modify os.environ."""
    # Capture original environment
    original_keys = set(os.environ.keys())

    # Create isolated environment
    env = create_isolated_environment(tmp_path)

    # os.environ should be unchanged
    assert set(os.environ.keys()) == original_keys

    # But the returned env should have the isolation variables
    assert "SQITCH_CONFIG" in env
    assert "SQLITCH_CONFIG" in env


def test_create_isolated_environment_prevents_home_config_access(tmp_path: Path):
    """Verify that isolated env prevents access to ~/.sqitch/sqitch.conf."""
    env = create_isolated_environment(tmp_path)

    # None of the config paths should point to user's home directory
    home = Path.home()

    sqitch_config = Path(env["SQITCH_CONFIG"])
    sqitch_system = Path(env["SQITCH_SYSTEM_CONFIG"])
    sqitch_user = Path(env["SQITCH_USER_CONFIG"])

    assert not str(sqitch_config).startswith(str(home))
    assert not str(sqitch_system).startswith(str(home))
    assert not str(sqitch_user).startswith(str(home))

    sqlitch_config = Path(env["SQLITCH_CONFIG"])
    sqlitch_system = Path(env["SQLITCH_SYSTEM_CONFIG"])
    sqlitch_user = Path(env["SQLITCH_USER_CONFIG"])

    assert not str(sqlitch_config).startswith(str(home))
    assert not str(sqlitch_system).startswith(str(home))
    assert not str(sqlitch_user).startswith(str(home))


def test_create_isolated_environment_prevents_etc_config_access(tmp_path: Path):
    """Verify that isolated env prevents access to /etc/sqitch/sqitch.conf."""
    env = create_isolated_environment(tmp_path)

    # None of the config paths should point to /etc
    etc = Path("/etc")

    sqitch_config = Path(env["SQITCH_CONFIG"])
    sqitch_system = Path(env["SQITCH_SYSTEM_CONFIG"])
    sqitch_user = Path(env["SQITCH_USER_CONFIG"])

    assert not str(sqitch_config).startswith(str(etc))
    assert not str(sqitch_system).startswith(str(etc))
    assert not str(sqitch_user).startswith(str(etc))

    sqlitch_config = Path(env["SQLITCH_CONFIG"])
    sqlitch_system = Path(env["SQLITCH_SYSTEM_CONFIG"])
    sqlitch_user = Path(env["SQLITCH_USER_CONFIG"])

    assert not str(sqlitch_config).startswith(str(etc))
    assert not str(sqlitch_system).startswith(str(etc))
    assert not str(sqlitch_user).startswith(str(etc))


def test_create_isolated_environment_uses_unique_locations_per_work_dir():
    """Verify that different work directories get different isolated environments."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        path1 = Path(tmp1).resolve()
        path2 = Path(tmp2).resolve()

        env1 = create_isolated_environment(Path(tmp1))
        env2 = create_isolated_environment(Path(tmp2))

        # Config paths should be different
        assert env1["SQITCH_CONFIG"] != env2["SQITCH_CONFIG"]
        assert env1["SQLITCH_CONFIG"] != env2["SQLITCH_CONFIG"]

        # But both should be valid paths under their respective work dirs
        assert env1["SQITCH_CONFIG"].startswith(str(path1))
        assert env2["SQITCH_CONFIG"].startswith(str(path2))


def test_create_isolated_environment_is_idempotent(tmp_path: Path):
    """Verify that calling create_isolated_environment multiple times is safe."""
    env1 = create_isolated_environment(tmp_path)
    env2 = create_isolated_environment(tmp_path)

    # Should return the same paths
    assert env1["SQITCH_CONFIG"] == env2["SQITCH_CONFIG"]
    assert env1["SQLITCH_CONFIG"] == env2["SQLITCH_CONFIG"]

    # Directories should exist
    isolated_root = tmp_path / ".isolated"
    assert isolated_root.exists()
