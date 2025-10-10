# Contributing to SQLitch

Thanks for helping build the SQLitch Python parity fork! The guidelines below document the day-to-day developer workflow so you can land changes smoothly and keep the project healthy.

## 1. Environment Setup

⚠️ **CRITICAL SAFETY NOTICE**: Before running tests or developing SQLitch, please read this carefully.

### Test Suite Safety

The SQLitch test suite extensively exercises configuration file operations. While we have implemented comprehensive test isolation measures (using isolated filesystem contexts and environment variable overrides), **we strongly recommend running tests in an isolated environment** to protect your existing Sqitch/SQLitch configurations.

**Recommended Safe Environments:**
- **Docker container** (safest option)
- Dedicated VM or cloud instance
- Separate user account with its own home directory
- Fresh development machine without existing Sqitch projects

**Why This Matters:**
If you have existing Sqitch projects with configurations in `~/.sqitch/sqitch.conf` or are actively using Sqitch/SQLitch, a bug in the test isolation layer could potentially modify or overwrite these files. Losing production database configuration could be catastrophic.

**Before Running Tests Locally:**
1. Back up your `~/.sqitch/` directory if it exists
2. Consider whether you have any critical Sqitch configurations
3. If in doubt, use Docker (see example below)

### Safe Docker Testing (Recommended)

```bash
# Build and run tests in complete isolation
docker run -v $(pwd):/workspace -w /workspace python:3.11 bash -c "
  python3 -m venv .venv && 
  source .venv/bin/activate && 
  pip install -e .[dev] && 
  python -m pytest
"
```

### Local Setup (Use with Caution)

1. Create and activate a virtual environment (Python 3.11+).
2. Install runtime and tooling dependencies (includes pytest, coverage plugins, linters, tox, etc.).

```bash
pip install ".[dev]"
```

3. All commands below assume the virtual environment remains active.

## 2. Working on Tasks (Red → Green Flow)

1. Each tracked task (e.g., `T052`) must start with a failing test.
2. Add or update tests in `tests/` referencing the task ID inside the skip reason (for example `pytest.mark.skip(reason="Pending T052")`).
3. Immediately before implementing the feature:
   - Remove the skip marker.
   - Run the test to confirm it now fails (Red).
   - Begin implementation and iterate until the test passes (Green).

This workflow is enforced automatically by the skip-check script and CI gates (FR-012).

## 3. Skip-Check Automation (`scripts/check-skips.py`)

The skip checker fails fast when skip markers referencing active tasks remain in the codebase.

### Basic usage

```bash
python scripts/check-skips.py T052 T055
```

### Environment-driven usage

Set `SQLITCH_ACTIVE_TASKS` to let the script (and CI) know which tasks are in flight:

```bash
export SQLITCH_ACTIVE_TASKS="T052,T055"
python scripts/check-skips.py
```

The `tox -e lint` environment runs the script automatically, so the lint job fails if any targeted skips survive.

### When the script fails

You’ll see output like:

```
Detected skip markers referencing active tasks:
  - tests/cli/contracts/test_plan_contract.py:12 -> T052: Pending T052
Remove these skip markers (or update the active task list) before proceeding with implementation.
```

Fix the offending tests by removing—or intentionally keeping—the skip markers and re-running the script until it passes.

## 3a. Writing Tests - Isolation Requirements (MANDATORY)

**All new tests MUST use isolated test contexts to prevent configuration pollution.**

### The Rule

When writing tests that invoke CLI commands or perform configuration operations:

1. **ALWAYS** import and use `isolated_test_context()` from `tests/support/test_helpers.py`
2. **NEVER** use bare `runner.isolated_filesystem()` for tests that create config files
3. **VERIFY** your test doesn't create artifacts in `~/.sqitch/` or `~/.config/sqlitch/`

### Why This Matters

The Constitution mandates: **"Test Isolation and Cleanup (MANDATORY)"** - tests must not leave artifacts in the repository or user directories. The spec requirement **FR-001b** mandates 100% Sqitch compatibility, which means never creating SQLitch-specific paths like `~/.config/sqlitch/`.

### Correct Pattern

```python
from tests.support.test_helpers import isolated_test_context

def test_config_operation():
    with isolated_test_context() as (runner, temp_dir):
        # All config operations are now isolated to temp_dir
        result = runner.invoke(main, ["config", "--user", "user.name", "Test User"])
        assert result.exit_code == 0
        
        # Config file created inside temp_dir, not ~/.sqitch/
        config_path = temp_dir / ".sqitch" / "sqitch.conf"
        assert config_path.exists()
```

### What `isolated_test_context()` Does

- Wraps Click's `runner.isolated_filesystem()` 
- Automatically sets `SQLITCH_SYSTEM_CONFIG`, `SQLITCH_USER_CONFIG`, and `SQLITCH_CONFIG` environment variables
- Points these variables to subdirectories INSIDE the isolated temp directory
- Restores original environment after test completes
- Ensures zero pollution of your actual home directory

### Verification

Before committing new tests, manually verify:

```bash
# Check for config pollution
ls -la ~/.sqitch/          # Should be unchanged or non-existent
ls -la ~/.config/sqlitch/  # Should NEVER exist

# Run your specific test
pytest tests/path/to/test_yourtest.py -v

# Verify again - no new files should appear
ls -la ~/.sqitch/
```

## 4. Local Quality Gates

Before opening a pull request, make sure these commands succeed:

```bash
# Unit tests with coverage (≥90% enforced automatically)
pytest -q

# Static analysis, formatting, lint, security
tox -e lint type security
```

Additional tox environments may be added as features land; check `tox.ini` for the latest list.

## 5. Pull Request Checklist

Every PR must check the boxes in `.github/pull_request_template.md`, which cover:

- Skip removal and confirmation that `scripts/check-skips.py` was executed (or the active task environment variable is set).
- Updated/added tests with passing `pytest`.
- Successful `tox -e lint type security` runs.
- Documentation, examples, and fixtures updated when applicable.

## 6. Troubleshooting Tips

- **Coverage failures:** The project enforces `fail_under = 90`. Add targeted tests or expand existing ones to raise coverage before rerunning `pytest`.
- **PyMySQL import errors:** The optional dev install (`pip install ".[dev]"`) bundles the pure-Python adapter. If `ModuleNotFoundError: pymysql` appears, ensure your virtual environment is active and rerun `pip install --upgrade --force-reinstall pymysql`.
- **Skip removal noise in lint:** If lint fails due to skip markers for tasks you’re *not* working on, double-check that `SQLITCH_ACTIVE_TASKS` only lists your active task IDs.

## 7. Need Help?

- Review the feature plan and task list under `specs/001-we-re-going/` for sequencing and dependencies.
- File issues or start a discussion if you find gaps in these docs; keeping contributor docs current is part of the MVP goals.

Happy hacking! 🎉
