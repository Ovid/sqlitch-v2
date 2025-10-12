# UAT Environment Isolation Requirements

## Critical Security Requirement

**ALL UAT scripts that execute `sqitch` or `sqlitch` commands via subprocess MUST use isolated environment variables to prevent pollution of user configuration files.**

## The Problem

When UAT scripts execute `sqitch` commands via `subprocess.Popen()` or similar functions, those child processes inherit the parent process's environment variables by default. This causes sqitch to read from and write to:

- `~/.sqitch/sqitch.conf` (user configuration)
- `/etc/sqitch/sqitch.conf` (system configuration)
- Other user-specific sqitch data directories

**This can destroy user configuration files and corrupt user databases.**

## The Solution

The `uat/isolation.py` module provides `create_isolated_environment()` which:

1. Creates isolated temporary directories under the test working directory
2. Sets both `SQITCH_*` and `SQLITCH_*` environment variables to point to those isolated locations
3. Returns a safe environment dict that can be passed to subprocess functions

### Example Usage

```python
from uat.isolation import create_isolated_environment

def run_command(cmd: list[str], cwd: Path) -> tuple[str, int]:
    """Run command with isolated environment."""
    # CRITICAL: Create isolated environment
    env = create_isolated_environment(cwd)
    
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,  # MUST pass isolated env
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # ... rest of implementation
```

## Required Environment Variables

The isolation helper sets **six critical environment variables**:

### SQLitch Variables (Python implementation)
- `SQLITCH_CONFIG` - Local project config file path
- `SQLITCH_SYSTEM_CONFIG` - System-wide config file path
- `SQLITCH_USER_CONFIG` - User config file path (~/.sqitch equivalent)

### Sqitch Variables (Perl implementation)
- `SQITCH_CONFIG` - Local project config file path
- `SQITCH_SYSTEM_CONFIG` - System-wide config file path  
- `SQITCH_USER_CONFIG` - User config file path (~/.sqitch/sqitch.conf)

**All six variables must be set** because UAT scripts test interoperability between SQLitch (Python) and Sqitch (Perl).

## Files Modified

The following UAT scripts have been fixed to use isolated environments:

1. **uat/side-by-side.py** - Side-by-side comparison of Sqitch vs SQLitch
2. **uat/scripts/forward-compat.py** - SQLitch→Sqitch forward compatibility tests
3. **uat/scripts/backward-compat.py** - Sqitch→SQLitch backward compatibility tests

Each script now:
- Imports `create_isolated_environment` from `uat.isolation`
- Calls `create_isolated_environment(work_dir)` before subprocess execution
- Passes the isolated `env` dict to `subprocess.Popen(..., env=env)`

## Testing

The `tests/uat/test_isolation.py` module validates that:

1. All six environment variables are set correctly
2. Config paths point to isolated temp directories under work_dir
3. No paths point to user's home directory or `/etc`
4. The isolation is idempotent and doesn't modify `os.environ`
5. Different work directories get different isolated environments

Run tests with:
```bash
python -m pytest tests/uat/test_isolation.py -v
```

## Developer Checklist

When creating new UAT scripts that execute sqitch/sqlitch commands:

- [ ] Import `create_isolated_environment` from `uat.isolation`
- [ ] Call `env = create_isolated_environment(work_dir)` before subprocess calls
- [ ] Pass `env=env` to all `subprocess.Popen()`, `subprocess.run()`, etc.
- [ ] Add tests to verify the script uses isolation correctly
- [ ] Document the security requirement in the script's docstring

## History

- **2025-01-11**: Initial implementation of environment isolation
  - Created `uat/isolation.py` module
  - Fixed side-by-side.py, forward-compat.py, backward-compat.py
  - Added comprehensive test coverage in test_isolation.py
  
- **Context**: This fix was discovered during Phase 3.3b (Mypy Type Safety) work when auditing test helpers revealed that `tests/support/test_helpers.py` had the same vulnerability. The fix was extended to all UAT scripts to prevent production usage from polluting user configs.

## References

- Security Issue: Config pollution vulnerability in test helpers (fixed 2025-01-11)
- Test Helper Fix: `tests/support/test_helpers.py::isolated_test_context()`
- Architecture Doc: `.github/copilot-instructions.md` - Testing Playbook section
