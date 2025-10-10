"""Test helpers for isolated filesystem and configuration testing.

This module provides utilities to ensure test isolation by preventing tests from
polluting the user's actual configuration directories. All configuration-related
environment variables are automatically redirected to temporary directories within
the test's isolated filesystem context.

Constitutional Compliance:
    - Constitution I: Test Isolation and Cleanup (MANDATORY)
    - FR-001b: 100% Configuration Compatibility (CRITICAL)
    - NFR-007: Test Isolation and Configuration Compatibility (MANDATORY)

The primary issue this solves:
    Without proper isolation, tests invoking `sqlitch config --user` would write to
    the actual user's home directory (~/.sqitch/ or worse ~/.config/sqlitch/),
    violating test isolation and potentially destroying user configuration files.

Example Usage:
    >>> from click.testing import CliRunner
    >>> from tests.support.test_helpers import isolated_test_context
    >>>
    >>> def test_config_commands():
    ...     runner = CliRunner()
    ...     with isolated_test_context(runner) as (runner, temp_dir):
    ...         # Config commands now write to temp_dir/.sqitch/sqitch.conf
    ...         result = runner.invoke(cli, ['config', '--user', 'user.name', 'Test'])
    ...         assert result.exit_code == 0
    ...         # Config file is created in isolated temp directory
    ...         user_config = temp_dir / '.sqitch' / 'sqitch.conf'
    ...         assert user_config.exists()
    ...     # After context exits, environment is restored, temp files are cleaned up

Extending this module:
    Future test utilities can be added here following the same patterns:
    - with_mock_time(): Override datetime.now() for deterministic timestamps
    - with_test_database(): Create temporary database for integration tests
    - with_git_repo(): Initialize temporary git repository for VCS tests
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    from click.testing import CliRunner

__all__ = ["isolated_test_context"]


@contextmanager
def isolated_test_context(
    runner: CliRunner,
    base_dir: Path | None = None,
) -> Generator[tuple[CliRunner, Path], None, None]:
    """Create an isolated filesystem context with configuration environment variables.

    This context manager wraps Click's `runner.isolated_filesystem()` and automatically
    sets the SQLITCH_* environment variables to point to subdirectories within the
    isolated temporary directory. This ensures that tests cannot pollute the user's
    actual configuration files.

    Environment Variables Set:
        - SQLITCH_SYSTEM_CONFIG: Points to {temp_dir}/etc/sqitch/sqitch.conf
        - SQLITCH_USER_CONFIG: Points to {temp_dir}/.sqitch/sqitch.conf
        - SQLITCH_CONFIG: Points to {temp_dir}/sqitch.conf (local/project config)

    These variables take precedence over the default configuration file discovery,
    ensuring all config operations during tests are isolated to the temporary directory.

    Args:
        runner: A Click CliRunner instance for invoking CLI commands
        base_dir: Optional base directory to use (e.g., pytest's tmp_path fixture).
                 If provided, creates config directories inside this path.
                 If None, uses runner.isolated_filesystem() to create a temp directory.

    Yields:
        tuple[CliRunner, Path]: The same runner instance and the temp directory path

    Example:
        >>> runner = CliRunner()
        >>> with isolated_test_context(runner) as (runner, temp_dir):
        ...     # All config operations are isolated to temp_dir
        ...     result = runner.invoke(cli, ['init', 'myproject', '--engine', 'sqlite'])
        ...     result = runner.invoke(cli, ['config', '--user', 'user.name', 'Tester'])
        ...
        ...     # Verify config was written to isolated location
        ...     user_config = temp_dir / '.sqitch' / 'sqitch.conf'
        ...     assert user_config.exists()
        ...     assert 'Tester' in user_config.read_text()

    Example with pytest tmp_path fixture:
        >>> def test_with_tmp_path(runner, tmp_path):
        ...     with isolated_test_context(runner, base_dir=tmp_path) as (runner, temp_dir):
        ...         # temp_dir will be tmp_path
        ...         result = runner.invoke(main, ["init", "myproject"])
        ...         assert result.exit_code == 0

    Constitutional Compliance:
        This function is **MANDATORY** for any test that invokes SQLitch commands
        which may read or write configuration files. Using this helper ensures:

        1. Test Isolation: No side effects on the user's actual filesystem
        2. Configuration Compatibility: Respects Sqitch's config file locations
        3. Deterministic Testing: Tests run in predictable, clean environments
        4. Safety: Eliminates risk of destroying user's existing configuration

    See Also:
        - Constitution I: Test Isolation and Cleanup (MANDATORY)
        - FR-001b: 100% Configuration Compatibility
        - NFR-007: Test Isolation and Configuration Compatibility
        - tests/support/README.md: Comprehensive testing patterns documentation
    """
    # Save original environment to restore later
    original_env = {
        "SQLITCH_SYSTEM_CONFIG": os.environ.get("SQLITCH_SYSTEM_CONFIG"),
        "SQLITCH_USER_CONFIG": os.environ.get("SQLITCH_USER_CONFIG"),
        "SQLITCH_CONFIG": os.environ.get("SQLITCH_CONFIG"),
    }

    try:
        if base_dir is not None:
            # Use provided base directory with Click's isolated_filesystem to change cwd
            # This provides both env isolation AND directory change behavior
            with runner.isolated_filesystem(temp_dir=base_dir) as temp_dir_str:
                temp_dir = Path(temp_dir_str)

                # Set up isolated config paths within the base directory
                system_config_dir = temp_dir / "etc" / "sqitch"
                user_config_dir = temp_dir / ".sqitch"
                local_config = temp_dir / "sqitch.conf"

                # Create the directory structure
                system_config_dir.mkdir(parents=True, exist_ok=True)
                user_config_dir.mkdir(parents=True, exist_ok=True)

                # Set environment variables to point to isolated locations
                os.environ["SQLITCH_SYSTEM_CONFIG"] = str(system_config_dir / "sqitch.conf")
                os.environ["SQLITCH_USER_CONFIG"] = str(user_config_dir / "sqitch.conf")
                os.environ["SQLITCH_CONFIG"] = str(local_config)

                # Yield control to the test
                yield runner, temp_dir
        else:
            # Use Click's isolated_filesystem() to create temp directory
            with runner.isolated_filesystem() as temp_dir_str:
                temp_dir = Path(temp_dir_str)

                # Set up isolated config paths within the temporary directory
                # These mirror the standard Sqitch config hierarchy but isolated
                system_config_dir = temp_dir / "etc" / "sqitch"
                user_config_dir = temp_dir / ".sqitch"
                local_config = temp_dir / "sqitch.conf"

                # Create the directory structure
                system_config_dir.mkdir(parents=True, exist_ok=True)
                user_config_dir.mkdir(parents=True, exist_ok=True)

                # Set environment variables to point to isolated locations
                os.environ["SQLITCH_SYSTEM_CONFIG"] = str(system_config_dir / "sqitch.conf")
                os.environ["SQLITCH_USER_CONFIG"] = str(user_config_dir / "sqitch.conf")
                os.environ["SQLITCH_CONFIG"] = str(local_config)

                # Yield control to the test
                yield runner, temp_dir

    finally:
        # Restore original environment variables
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
