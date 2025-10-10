"""Unit tests for test_helpers module.

These tests verify that the isolated_test_context() helper properly isolates
configuration environments and restores state correctly.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.support.test_helpers import isolated_test_context


def test_isolated_test_context_sets_environment_variables():
    """Test that environment variables are set within the context."""
    runner = CliRunner()

    with isolated_test_context(runner) as (runner_out, temp_dir):
        # Verify environment variables are set
        assert "SQLITCH_SYSTEM_CONFIG" in os.environ
        assert "SQLITCH_USER_CONFIG" in os.environ
        assert "SQLITCH_CONFIG" in os.environ

        # Verify they point to paths within temp_dir
        system_config = Path(os.environ["SQLITCH_SYSTEM_CONFIG"])
        user_config = Path(os.environ["SQLITCH_USER_CONFIG"])
        local_config = Path(os.environ["SQLITCH_CONFIG"])

        assert system_config.parent == temp_dir / "etc" / "sqitch"
        assert user_config.parent == temp_dir / ".sqitch"
        assert local_config.parent == temp_dir

        # Verify runner is returned
        assert runner_out is runner


def test_isolated_test_context_creates_directories():
    """Test that required directories are created."""
    runner = CliRunner()

    with isolated_test_context(runner) as (_, temp_dir):
        # Verify directories exist
        assert (temp_dir / "etc" / "sqitch").exists()
        assert (temp_dir / "etc" / "sqitch").is_dir()
        assert (temp_dir / ".sqitch").exists()
        assert (temp_dir / ".sqitch").is_dir()


def test_isolated_test_context_points_inside_temp_dir():
    """Test that all config paths point inside the isolated temp directory."""
    runner = CliRunner()

    with isolated_test_context(runner) as (_, temp_dir):
        system_config = Path(os.environ["SQLITCH_SYSTEM_CONFIG"])
        user_config = Path(os.environ["SQLITCH_USER_CONFIG"])
        local_config = Path(os.environ["SQLITCH_CONFIG"])

        # All paths should be within temp_dir
        assert system_config.is_relative_to(temp_dir)
        assert user_config.is_relative_to(temp_dir)
        assert local_config.is_relative_to(temp_dir)

        # Verify expected paths
        assert system_config == temp_dir / "etc" / "sqitch" / "sqitch.conf"
        assert user_config == temp_dir / ".sqitch" / "sqitch.conf"
        assert local_config == temp_dir / "sqitch.conf"


def test_isolated_test_context_restores_environment():
    """Test that original environment is restored after context exits."""
    runner = CliRunner()

    # Save original state
    original_system = os.environ.get("SQLITCH_SYSTEM_CONFIG")
    original_user = os.environ.get("SQLITCH_USER_CONFIG")
    original_local = os.environ.get("SQLITCH_CONFIG")

    with isolated_test_context(runner) as (_, temp_dir):
        # Modify environment within context
        os.environ["SQLITCH_SYSTEM_CONFIG"] = "/some/other/path"

    # After context exits, original state should be restored
    assert os.environ.get("SQLITCH_SYSTEM_CONFIG") == original_system
    assert os.environ.get("SQLITCH_USER_CONFIG") == original_user
    assert os.environ.get("SQLITCH_CONFIG") == original_local


def test_isolated_test_context_no_pollution_of_user_home():
    """Test that no files are created in user's actual home directory."""
    runner = CliRunner()
    home = Path.home()

    # Check state before test
    sqlitch_config_before = (home / ".config" / "sqlitch").exists()
    sqitch_config_before = (home / ".sqitch" / "sqitch.conf").exists()

    with isolated_test_context(runner) as (_, temp_dir):
        # Create a config file in the isolated location
        user_config = temp_dir / ".sqitch" / "sqitch.conf"
        user_config.write_text("[user]\nname = Test User\n")

        # Verify it exists in temp, not in home
        assert user_config.exists()
        assert not (home / ".config" / "sqlitch").exists() or sqlitch_config_before
        # Note: we can't guarantee ~/.sqitch doesn't exist if user has sqitch installed
        # but we can verify our test didn't modify it

    # After context exits, verify state unchanged
    sqlitch_config_after = (home / ".config" / "sqlitch").exists()
    sqitch_config_after = (home / ".sqitch" / "sqitch.conf").exists()

    assert sqlitch_config_after == sqlitch_config_before
    # Can't assert on sqitch_config since it may legitimately exist


def test_isolated_test_context_with_existing_environment():
    """Test behavior when environment variables already set."""
    runner = CliRunner()

    # Set some environment variables before context
    os.environ["SQLITCH_SYSTEM_CONFIG"] = "/original/system/config"
    os.environ["SQLITCH_USER_CONFIG"] = "/original/user/config"
    os.environ["SQLITCH_CONFIG"] = "/original/local/config"

    try:
        with isolated_test_context(runner) as (_, temp_dir):
            # Within context, should point to temp directory
            assert os.environ["SQLITCH_SYSTEM_CONFIG"] != "/original/system/config"
            assert temp_dir.as_posix() in os.environ["SQLITCH_SYSTEM_CONFIG"]

        # After context, should be restored
        assert os.environ["SQLITCH_SYSTEM_CONFIG"] == "/original/system/config"
        assert os.environ["SQLITCH_USER_CONFIG"] == "/original/user/config"
        assert os.environ["SQLITCH_CONFIG"] == "/original/local/config"

    finally:
        # Clean up
        for key in ["SQLITCH_SYSTEM_CONFIG", "SQLITCH_USER_CONFIG", "SQLITCH_CONFIG"]:
            os.environ.pop(key, None)


def test_isolated_test_context_nested_calls():
    """Test that context can be nested (though not typically needed)."""
    runner = CliRunner()

    with isolated_test_context(runner) as (_, temp_dir1):
        config1 = os.environ["SQLITCH_USER_CONFIG"]

        # Nest another context (unusual but should work)
        with isolated_test_context(runner) as (_, temp_dir2):
            config2 = os.environ["SQLITCH_USER_CONFIG"]

            # Inner context should have different temp dir
            assert temp_dir1 != temp_dir2
            assert config1 != config2
            assert temp_dir2.as_posix() in config2

        # After inner context exits, outer context restored
        assert os.environ["SQLITCH_USER_CONFIG"] == config1


def test_isolated_test_context_exception_handling():
    """Test that environment is restored even if exception occurs."""
    runner = CliRunner()

    # Set initial state
    os.environ["SQLITCH_USER_CONFIG"] = "/original/config"

    try:
        with isolated_test_context(runner) as (_, temp_dir):
            # Verify changed
            assert os.environ["SQLITCH_USER_CONFIG"] != "/original/config"

            # Raise an exception
            raise ValueError("Test exception")

    except ValueError:
        pass

    # Environment should still be restored
    assert os.environ["SQLITCH_USER_CONFIG"] == "/original/config"

    # Clean up
    os.environ.pop("SQLITCH_USER_CONFIG", None)


def test_isolated_test_context_config_file_creation():
    """Test that config files created within context are isolated."""
    runner = CliRunner()

    with isolated_test_context(runner) as (_, temp_dir):
        # Create a config file at the user config location
        user_config_path = Path(os.environ["SQLITCH_USER_CONFIG"])
        user_config_path.write_text("[user]\nname = Test\nemail = test@example.com\n")

        # Verify it exists and is within temp_dir
        assert user_config_path.exists()
        assert user_config_path.is_relative_to(temp_dir)
        assert "Test" in user_config_path.read_text()

    # After context, file should be gone (temp dir cleaned up)
    assert not user_config_path.exists()


def test_isolated_test_context_system_user_local_hierarchy():
    """Test that all three config levels are properly set up."""
    runner = CliRunner()

    with isolated_test_context(runner) as (_, temp_dir):
        system_config = Path(os.environ["SQLITCH_SYSTEM_CONFIG"])
        user_config = Path(os.environ["SQLITCH_USER_CONFIG"])
        local_config = Path(os.environ["SQLITCH_CONFIG"])

        # Create files at each level
        system_config.write_text("[core]\nengine = pg\n")
        user_config.write_text("[user]\nname = System User\n")
        local_config.write_text("[core]\nengine = sqlite\n")

        # All should exist
        assert system_config.exists()
        assert user_config.exists()
        assert local_config.exists()

        # All should be in temp directory
        assert system_config.is_relative_to(temp_dir)
        assert user_config.is_relative_to(temp_dir)
        assert local_config.is_relative_to(temp_dir)

        # Verify content
        assert "pg" in system_config.read_text()
        assert "System User" in user_config.read_text()
        assert "sqlite" in local_config.read_text()
