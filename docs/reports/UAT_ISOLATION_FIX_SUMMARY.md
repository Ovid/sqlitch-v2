# UAT Environment Isolation Security Fix - Summary

## Issue Overview

**CRITICAL SECURITY VULNERABILITY**: UAT scripts in `uat/` directory executed `sqitch` commands via `subprocess.Popen()` without passing an `env` parameter, causing child processes to inherit parent environment variables and potentially pollute user configuration files at `~/.sqitch/sqitch.conf` and `/etc/sqitch/sqitch.conf`.

## Root Cause

When executing external commands via subprocess without specifying an `env` parameter, the child process inherits all environment variables from the parent. For sqitch/sqlitch tools, this means:

1. Sqitch reads config from `~/.sqitch/sqitch.conf` (via `SQITCH_USER_CONFIG`)
2. Sqitch reads system config from `/etc/sqitch/sqitch.conf` (via `SQITCH_SYSTEM_CONFIG`)
3. SQLitch reads config from `~/.sqitch/sqlitch.conf` (via `SQLITCH_USER_CONFIG`)

Running UAT scripts could therefore **overwrite user configuration files**, potentially destroying weeks or months of user work.

## Discovery Context

This vulnerability was discovered during Phase 3.3b (Mypy Type Safety) implementation when auditing `tests/support/test_helpers.py` revealed that `isolated_test_context()` only set `SQLITCH_*` variables, not `SQITCH_*` variables. The audit was extended to all UAT scripts and found the same pattern: subprocess execution without environment isolation.

## Files Created

### 1. `uat/isolation.py`
**Purpose**: Centralized environment isolation utility for UAT scripts

**Key Function**: `create_isolated_environment(work_dir: Path) -> dict[str, Any]`

**What it does**:
- Creates isolated temp directories under `work_dir/.isolated/`
- Sets 6 critical environment variables pointing to isolated locations:
  - `SQLITCH_CONFIG`, `SQLITCH_SYSTEM_CONFIG`, `SQLITCH_USER_CONFIG`
  - `SQITCH_CONFIG`, `SQITCH_SYSTEM_CONFIG`, `SQITCH_USER_CONFIG`
- Returns a safe environment dict for subprocess execution

**Type Safety**: Passes `mypy --strict` with 0 errors

### 2. `tests/uat/test_isolation.py`
**Purpose**: Comprehensive validation of environment isolation

**Test Coverage** (9 tests, all passing):
- ✅ All SQLITCH_* variables are set correctly
- ✅ All SQITCH_* variables are set correctly
- ✅ Isolation directories are created automatically
- ✅ Config paths don't point to user's home directory
- ✅ Config paths don't point to `/etc`
- ✅ Different work directories get unique isolated environments
- ✅ Isolation is idempotent (can be called multiple times safely)
- ✅ Parent `os.environ` is never modified
- ✅ Parent environment variables are preserved in isolated env

### 3. `docs/UAT_ISOLATION.md`
**Purpose**: Security requirements documentation

**Contents**:
- Explanation of the vulnerability and fix
- Example usage patterns
- Developer checklist for new UAT scripts
- Testing instructions
- Historical context and references

## Files Modified

### 1. `uat/side-by-side.py`
**Changes**:
- Added import: `from uat.isolation import create_isolated_environment`
- Modified `run_and_stream()` to call `create_isolated_environment(cwd)`
- Added `env=env` parameter to `subprocess.Popen()` call
- Added security comment: `# CRITICAL: Use isolated environment`

**Impact**: Side-by-side comparison tests now safe from config pollution

### 2. `uat/scripts/forward-compat.py`
**Changes**:
- Added import: `from uat.isolation import create_isolated_environment`
- Modified `run_command()` to call `create_isolated_environment(cwd)`
- Added `env=env` parameter to `subprocess.Popen()` call
- Added security comment: `# CRITICAL: Use isolated environment`

**Impact**: Forward compatibility tests (SQLitch→Sqitch) now safe

### 3. `uat/scripts/backward-compat.py`
**Changes**:
- Added import: `from uat.isolation import create_isolated_environment`
- Modified `run_command()` to call `create_isolated_environment(cwd)`
- Added `env=env` parameter to `subprocess.Popen()` call
- Added security comment: `# CRITICAL: Use isolated environment`

**Impact**: Backward compatibility tests (Sqitch→SQLitch) now safe

## Validation Results

### Test Suite
```bash
$ python -m pytest tests/uat/test_isolation.py -v
================================ 9 passed in 0.84s =================================
```

All 9 isolation tests pass, validating:
- Environment variable isolation is complete
- No user config files can be accessed
- Isolation is idempotent and safe

### Full UAT Test Suite
```bash
$ python -m pytest tests/uat/ -v
================================ 16 passed in 0.74s ================================
```

All 16 UAT tests pass, including:
- 9 new isolation tests
- 3 forward compatibility tests
- 2 backward compatibility tests
- 2 UAT helper tests

### Type Safety
```bash
$ mypy --strict uat/isolation.py
No errors in uat/isolation.py
```

The new isolation module passes mypy strict type checking with 0 errors.

## Security Impact

### Before Fix (CRITICAL VULNERABILITY)
- ❌ Running `uat/side-by-side.py` could overwrite `~/.sqitch/sqitch.conf`
- ❌ Running `uat/scripts/forward-compat.py` could corrupt user sqitch config
- ❌ Running `uat/scripts/backward-compat.py` could destroy user sqlitch config
- ❌ No way to safely run UAT scripts without backing up configs first
- ❌ Risk of data loss for developers and users

### After Fix (SECURE)
- ✅ All subprocess executions use isolated environments
- ✅ User config files (`~/.sqitch/sqitch.conf`) cannot be accessed
- ✅ System config files (`/etc/sqitch/sqitch.conf`) cannot be accessed
- ✅ UAT scripts can be run safely at any time
- ✅ Comprehensive test coverage validates security properties
- ✅ Pattern is reusable for future UAT scripts

## Implementation Pattern

The fix establishes a security pattern for all UAT scripts:

```python
from uat.isolation import create_isolated_environment

def run_command(cmd: list[str], cwd: Path) -> tuple[str, int]:
    """Run command with isolated environment to prevent config pollution."""
    # CRITICAL: Create isolated environment
    env = create_isolated_environment(cwd)
    
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,  # CRITICAL: Use isolated environment
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # ... rest of implementation
```

This pattern MUST be followed for any new UAT scripts that execute sqitch/sqlitch commands.

## Developer Guidelines

### Checklist for New UAT Scripts

When creating new UAT scripts that execute sqitch/sqlitch commands:

- [ ] Import `create_isolated_environment` from `uat.isolation`
- [ ] Call `env = create_isolated_environment(work_dir)` before subprocess
- [ ] Pass `env=env` to ALL subprocess calls (`Popen`, `run`, `call`, etc.)
- [ ] Add security comment: `# CRITICAL: Use isolated environment`
- [ ] Add tests validating the script uses isolation correctly
- [ ] Document the security requirement in the script's docstring

### Testing Requirements

All UAT scripts must have tests that verify:
1. Commands execute successfully with isolation
2. No user config files are accessed (can be tested with file access monitoring)
3. Isolated directories are created in expected locations

## Related Changes

This fix is part of a broader security audit that also fixed:

- `tests/support/test_helpers.py::isolated_test_context()` (fixed in same session)
- Test helpers now set both SQITCH_* and SQLITCH_* variables
- Added validation tests in `tests/support/test_test_helpers.py`

## References

- Security Issue: Config pollution in test helpers (2025-01-11)
- Implementation Context: Phase 3.3b (Mypy Type Safety) work
- Architecture Doc: `.github/copilot-instructions.md` - Testing Playbook
- Documentation: `docs/UAT_ISOLATION.md`

## Commit Message Template

```
fix(uat): Add environment isolation to prevent config pollution

CRITICAL: UAT scripts executed sqitch commands without environment
isolation, risking destruction of user config files at ~/.sqitch/sqitch.conf

Changes:
- Created uat/isolation.py with create_isolated_environment() helper
- Fixed uat/side-by-side.py to use isolated environment
- Fixed uat/scripts/forward-compat.py to use isolated environment  
- Fixed uat/scripts/backward-compat.py to use isolated environment
- Added tests/uat/test_isolation.py with 9 comprehensive tests
- Added docs/UAT_ISOLATION.md documenting security requirements

All 16 UAT tests pass. Isolation module passes mypy --strict.

Security Impact: UAT scripts can now be safely run without risk of
overwriting user configuration files.
```

## Timeline

- **2025-01-11**: Vulnerability discovered during Phase 3.3b mypy work
- **2025-01-11**: Fix implemented and tested (same day)
- **Status**: RESOLVED - All UAT scripts now use environment isolation

## Lessons Learned

1. **Subprocess execution is security-critical**: Any script that executes external commands must explicitly control the environment
2. **Both tool families need isolation**: For interoperability tests, both SQITCH_* and SQLITCH_* variables must be set
3. **Test the tests**: Security-critical test helpers themselves need validation tests
4. **Comprehensive audits pay off**: Extending the audit from test helpers to UAT scripts prevented future incidents
5. **Documentation prevents regression**: Clear documentation helps future developers maintain security properties
