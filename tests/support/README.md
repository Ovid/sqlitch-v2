# Test Support Utilities

This directory contains shared testing utilities and helpers for the SQLitch test suite.

## Table of Contents

- [Test Isolation with `isolated_test_context()`](#test-isolation-with-isolated_test_context)
- [Constitutional Requirements](#constitutional-requirements)
- [Usage Examples](#usage-examples)
- [Extending Test Helpers](#extending-test-helpers)
- [Troubleshooting](#troubleshooting)

---

## Test Isolation with `isolated_test_context()`

### Overview

The `isolated_test_context()` helper in `test_helpers.py` is **MANDATORY** for any test that invokes SQLitch CLI commands which may read or write configuration files.

### Problem Statement

Without proper test isolation, tests that invoke `sqlitch config --user` or similar commands would write to the user's actual home directory (`~/.sqitch/sqitch.conf` or `~/.config/sqlitch/sqitch.conf`), causing:

1. **Constitutional Violation**: Violates "Test Isolation and Cleanup (MANDATORY)"
2. **Compatibility Break**: Creates SQLitch-specific paths, breaking FR-001b compatibility
3. **Data Loss Risk**: Could overwrite or destroy user's existing Sqitch configuration
4. **Non-Deterministic Tests**: Tests may fail differently depending on user's config

### Solution

The `isolated_test_context()` context manager:

1. Wraps Click's `runner.isolated_filesystem()` to create a temporary directory
2. Automatically sets environment variables to point config files **inside** the temp directory:
   - `SQLITCH_SYSTEM_CONFIG` → `{temp_dir}/etc/sqitch/sqitch.conf`
   - `SQLITCH_USER_CONFIG` → `{temp_dir}/.sqitch/sqitch.conf`
   - `SQLITCH_CONFIG` → `{temp_dir}/sqitch.conf`
3. Restores original environment when context exits
4. Temp directory and all contents are automatically cleaned up

---

## Constitutional Requirements

This helper addresses the following requirements:

### Constitution I: Test Isolation and Cleanup (MANDATORY)

> Tests MUST NOT leave artifacts on the filesystem or modify user configuration.

**Compliance**: All config operations are redirected to temporary directories that are automatically cleaned up.

### FR-001b: 100% Configuration Compatibility (CRITICAL)

> SQLitch MUST NOT create SQLitch-specific config paths like `~/.config/sqlitch/`.
> Users must be able to seamlessly switch between `sqitch` and `sqlitch` commands.

**Compliance**: Environment variables force all config operations to use standard Sqitch paths (`~/.sqitch/`) even in test environments.

### NFR-007: Test Isolation and Configuration Compatibility (MANDATORY)

> Test helper module MUST automatically set SQLITCH_* environment variables to point inside isolated filesystem contexts.

**Compliance**: This is the implementation of NFR-007.

---

## Usage Examples

### Basic Usage

```python
from click.testing import CliRunner
from tests.support.test_helpers import isolated_test_context
from sqlitch.cli.main import cli

def test_config_set_user_name():
    """Test setting user name in config."""
    runner = CliRunner()
    
    with isolated_test_context(runner) as (runner, temp_dir):
        # This writes to temp_dir/.sqitch/sqitch.conf, not ~/.sqitch/
        result = runner.invoke(cli, ['config', '--user', 'user.name', 'Test User'])
        
        assert result.exit_code == 0
        
        # Verify config was written to isolated location
        user_config = temp_dir / '.sqitch' / 'sqitch.conf'
        assert user_config.exists()
        assert 'Test User' in user_config.read_text()
```

### Testing Init Command

```python
def test_init_creates_config():
    """Test that init command creates local config."""
    runner = CliRunner()
    
    with isolated_test_context(runner) as (runner, temp_dir):
        # Initialize project
        result = runner.invoke(cli, ['init', 'myproject', '--engine', 'sqlite'])
        assert result.exit_code == 0
        
        # Local config is created in temp_dir
        local_config = temp_dir / 'sqitch.conf'
        assert local_config.exists()
        
        # Verify engine setting
        config_content = local_config.read_text()
        assert '[core]' in config_content
        assert 'engine = sqlite' in config_content
```

### Testing Config Hierarchy

```python
def test_config_hierarchy():
    """Test system → user → local config precedence."""
    runner = CliRunner()
    
    with isolated_test_context(runner) as (runner, temp_dir):
        # Set up configs at each level
        system_config = temp_dir / 'etc' / 'sqitch' / 'sqitch.conf'
        user_config = temp_dir / '.sqitch' / 'sqitch.conf'
        local_config = temp_dir / 'sqitch.conf'
        
        system_config.write_text('[core]\nengine = pg\n')
        user_config.write_text('[user]\nname = Test User\n')
        local_config.write_text('[core]\nengine = sqlite\n')
        
        # Test that local overrides system
        result = runner.invoke(cli, ['config', 'core.engine'])
        assert result.exit_code == 0
        assert 'sqlite' in result.output  # local wins
```

### Testing Multiple Projects

```python
def test_multiple_projects():
    """Test working with multiple isolated projects."""
    runner = CliRunner()
    
    with isolated_test_context(runner) as (runner, temp_dir):
        # Create first project
        proj1 = temp_dir / 'project1'
        proj1.mkdir()
        result = runner.invoke(cli, ['init', 'proj1', '--engine', 'sqlite'], 
                               obj={'root': proj1})
        assert result.exit_code == 0
        
        # Create second project
        proj2 = temp_dir / 'project2'
        proj2.mkdir()
        result = runner.invoke(cli, ['init', 'proj2', '--engine', 'pg'],
                               obj={'root': proj2})
        assert result.exit_code == 0
        
        # Both configs are isolated
        assert (proj1 / 'sqitch.conf').exists()
        assert (proj2 / 'sqitch.conf').exists()
        assert 'sqlite' in (proj1 / 'sqitch.conf').read_text()
        assert 'pg' in (proj2 / 'sqitch.conf').read_text()
```

### Integration with Pytest Fixtures

```python
import pytest
from click.testing import CliRunner
from tests.support.test_helpers import isolated_test_context

@pytest.fixture
def isolated_runner():
    """Fixture providing isolated CLI runner."""
    runner = CliRunner()
    with isolated_test_context(runner) as (runner, temp_dir):
        yield runner, temp_dir

def test_with_fixture(isolated_runner):
    """Test using fixture for isolation."""
    runner, temp_dir = isolated_runner
    result = runner.invoke(cli, ['init', 'test', '--engine', 'sqlite'])
    assert result.exit_code == 0
    assert (temp_dir / 'sqitch.conf').exists()
```

---

## Extending Test Helpers

The `test_helpers.py` module is designed for extensibility. Future test utilities should follow the same patterns:

### Example: Mock Time Helper

```python
@contextmanager
def with_mock_time(fixed_time: datetime) -> Generator[None, None, None]:
    """Override datetime.now() for deterministic timestamps.
    
    Example:
        >>> with with_mock_time(datetime(2025, 1, 1, 12, 0, 0)):
        ...     # All calls to datetime.now() return fixed_time
        ...     result = runner.invoke(cli, ['add', 'test_change'])
    """
    original_now = datetime.now
    datetime.now = lambda: fixed_time
    try:
        yield
    finally:
        datetime.now = original_now
```

### Example: Test Database Helper

```python
@contextmanager
def with_test_database(engine: str = 'sqlite') -> Generator[str, None, None]:
    """Create temporary database for integration tests.
    
    Example:
        >>> with with_test_database('sqlite') as db_uri:
        ...     result = runner.invoke(cli, ['deploy', db_uri])
        ...     # Database is automatically cleaned up after test
    """
    # Implementation details...
```

### Guidelines for New Helpers

1. **Use context managers** (`@contextmanager` decorator)
2. **Restore state** in `finally` blocks
3. **Document usage** with comprehensive docstrings
4. **Include examples** in docstrings
5. **Reference constitutional requirements**
6. **Write unit tests** in `test_test_helpers.py`

---

## Troubleshooting

### Tests Still Creating Files in Home Directory

**Symptom**: Tests create `~/.config/sqlitch/` or modify `~/.sqitch/`

**Solution**: Ensure you're using `isolated_test_context()` instead of `runner.isolated_filesystem()`:

```python
# ❌ WRONG - bypasses isolation
with runner.isolated_filesystem():
    result = runner.invoke(cli, ['config', '--user', 'user.name', 'Test'])

# ✅ CORRECT - provides full isolation
with isolated_test_context(runner) as (runner, temp_dir):
    result = runner.invoke(cli, ['config', '--user', 'user.name', 'Test'])
```

### Environment Variables Not Set

**Symptom**: `SQLITCH_USER_CONFIG` is `None` within test

**Solution**: Verify you're using the context manager correctly and checking within the `with` block:

```python
with isolated_test_context(runner) as (runner, temp_dir):
    # ✅ Variables are set here
    assert os.environ.get('SQLITCH_USER_CONFIG') is not None
    
# ❌ Variables are restored here
assert os.environ.get('SQLITCH_USER_CONFIG') is None  # May be None
```

### Config Files Not Found

**Symptom**: Test expects config file but it doesn't exist

**Solution**: The helper creates directories but not files. Create files explicitly:

```python
with isolated_test_context(runner) as (runner, temp_dir):
    # Create config file explicitly
    user_config = temp_dir / '.sqitch' / 'sqitch.conf'
    user_config.write_text('[user]\nname = Test\n')
    
    # Now it exists
    assert user_config.exists()
```

### Nested Context Issues

**Symptom**: Inner context doesn't properly restore outer context

**Solution**: Avoid nesting `isolated_test_context()` calls. Each test should use one context:

```python
# ❌ WRONG - unnecessary nesting
with isolated_test_context(runner) as (runner, temp_dir1):
    with isolated_test_context(runner) as (runner, temp_dir2):
        # This works but is confusing
        pass

# ✅ CORRECT - one context per test
def test_scenario_1():
    with isolated_test_context(runner) as (runner, temp_dir):
        # Test scenario 1
        pass

def test_scenario_2():
    with isolated_test_context(runner) as (runner, temp_dir):
        # Test scenario 2 with fresh isolation
        pass
```

---

## Migration Checklist

When migrating existing tests to use `isolated_test_context()`:

- [ ] Import `isolated_test_context` from `tests.support.test_helpers`
- [ ] Replace `runner.isolated_filesystem()` with `isolated_test_context(runner)`
- [ ] Update context unpacking: `(runner, temp_dir)` instead of `temp_dir_str`
- [ ] Convert `Path(temp_dir_str)` to just `temp_dir` (already a Path)
- [ ] Remove any manual environment variable management
- [ ] Remove any manual cleanup of config files
- [ ] Run the test to verify isolation works
- [ ] Check that no files created in `~/.config/sqlitch/` or modified in `~/.sqitch/`

---

## References

- **Constitution**: `.specify/memory/constitution.md` (Test Isolation and Cleanup)
- **Feature Spec**: `specs/004-sqlitch-tutorial-parity/spec.md` (FR-001b, NFR-007)
- **Implementation**: `tests/support/test_helpers.py`
- **Unit Tests**: `tests/support/test_test_helpers.py`
- **Tasks**: `specs/004-sqlitch-tutorial-parity/tasks.md`

---

**Last Updated**: 2025-10-10  
**Status**: Active  
**Maintainer**: SQLitch Core Team
