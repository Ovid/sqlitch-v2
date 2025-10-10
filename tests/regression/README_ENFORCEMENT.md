# Test Isolation Enforcement

## Overview

SQLitch enforces test isolation at **two levels**:

1. **Session-level**: Pytest hook in `tests/conftest.py` that runs **before any tests**
2. **Test-level**: Regression test in `test_test_isolation_enforcement.py` that runs as part of the suite

Both mechanisms ensure that no test files use `runner.isolated_filesystem()` directly, which would violate Constitution I: Test Isolation and Cleanup (MANDATORY).

## How It Works

### Session-Level Enforcement (Primary)

The `pytest_sessionstart()` hook in `tests/conftest.py`:
- ✅ Runs **before any test collection or execution**
- ✅ Uses `git grep` to find all files containing `isolated_filesystem` in `tests/`
- ✅ Filters out allowed exceptions (helper definitions, documentation)
- ✅ **Aborts the entire test session** if violations are found
- ✅ Provides clear, actionable error messages with fix instructions

**Why this matters**: If a test file has `isolated_filesystem()`, running the test suite would pollute the user's `~/.config/sqlitch/` or `~/.sqitch/` directories. The session hook prevents this from happening by failing fast.

### Test-Level Enforcement (Secondary)

The `test_no_direct_isolated_filesystem_usage()` test:
- ✅ Runs as a normal test in the regression suite
- ✅ Performs the same check as the session hook
- ✅ Provides detailed documentation in its docstring
- ✅ Serves as a permanent regression guard

**Why both?**: The session hook catches violations immediately, while the test provides documentation and can be run standalone.

## Allowed Exceptions

The following files are **allowed** to reference `isolated_filesystem`:

- `tests/support/test_helpers.py` - Defines the `isolated_test_context()` helper
- `tests/support/test_test_helpers.py` - Tests the helper implementation
- `tests/support/README.md` - Documentation
- `tests/conftest.py` - Session hook that checks for violations
- `tests/regression/test_test_isolation_enforcement.py` - Enforcement test

## What Happens on Violation

If a test file uses `isolated_filesystem()` directly:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                   ❌ CONSTITUTION VIOLATION DETECTED                          ║
║                   TEST SESSION ABORTED                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Found 1 test file(s) using isolated_filesystem() directly:

  - tests/cli/commands/test_example.py

This violates Constitution I: Test Isolation and Cleanup (MANDATORY)

WHY THIS IS CRITICAL:
━━━━━━━━━━━━━━━━━━
Direct use of isolated_filesystem() does NOT isolate environment variables.
Tests can write config files to ~/.config/sqlitch/ or ~/.sqitch/, polluting
the user's home directory and potentially DESTROYING existing Sqitch/SQLitch
configuration.

The test suite will NOT run until this is fixed.

HOW TO FIX:
━━━━━━━━━━━
1. Import the helper:
   from tests.support.test_helpers import isolated_test_context

2. Replace:
   with runner.isolated_filesystem():
       # test code

   With:
   with isolated_test_context(runner) as (runner, temp_dir):
       # test code

3. Update paths:
   Change Path('file.txt') to (temp_dir / 'file.txt')

4. For batch processing:
   python scripts/migrate_test_isolation.py <test_file>
```

## Migration

### Automated Migration

Use the migration script for batch processing:

```bash
python scripts/migrate_test_isolation.py tests/path/to/test_file.py
```

The script handles:
- `runner.isolated_filesystem()` → `isolated_test_context(runner)`
- `runner.isolated_filesystem(temp_dir=var)` → `isolated_test_context(runner, base_dir=var)`
- Automatic import addition
- Path reference updates

### Manual Migration

If the script doesn't handle your case:

**Before**:
```python
from click.testing import CliRunner

def test_example():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["config", "--user", "user.name", "Test"])
        config_file = Path(".sqitch/sqitch.conf")
        assert config_file.exists()
```

**After**:
```python
from click.testing import CliRunner
from tests.support.test_helpers import isolated_test_context

def test_example():
    runner = CliRunner()
    with isolated_test_context(runner) as (runner, temp_dir):
        result = runner.invoke(cli, ["config", "--user", "user.name", "Test"])
        config_file = temp_dir / ".sqitch/sqitch.conf"
        assert config_file.exists()
```

### With pytest tmp_path Fixture

**Before**:
```python
def test_example(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # test code
```

**After**:
```python
from tests.support.test_helpers import isolated_test_context

def test_example(tmp_path):
    runner = CliRunner()
    with isolated_test_context(runner, base_dir=tmp_path) as (runner, temp_dir):
        # test code
```

## Constitutional Compliance

This enforcement mechanism ensures:

- ✅ **Constitution I**: Test Isolation and Cleanup (MANDATORY)
- ✅ **FR-001b**: 100% Configuration Compatibility (CRITICAL)
- ✅ **NFR-007**: Test Isolation and Configuration Compatibility (MANDATORY)

## See Also

- `tests/support/README.md` - Comprehensive test isolation patterns
- `tests/support/test_helpers.py` - Helper implementation
- `scripts/migrate_test_isolation.py` - Automated migration tool
- `.specify/memory/constitution.md` - Project constitution
