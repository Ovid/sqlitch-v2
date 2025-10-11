# UAT Compatibility Testing Architecture

**Status**: Active (2025-10-11)  
**Scope**: SQLite tutorial workflow only  
**Purpose**: Manual validation of Sqitch behavioral parity before releases

## Overview

The UAT (User Acceptance Testing) compatibility framework validates that SQLitch produces byte-identical database states and behaviorally equivalent outputs compared to Sqitch across the canonical SQLite tutorial workflow. This framework consists of three Python scripts plus shared helper modules that enable reusable sanitization, comparison, and test step execution.

## Design Principles

1. **Manual Execution**: UAT scripts run manually before releases, not in CI
2. **SQLite Only**: All scripts target the Sqitch SQLite tutorial workflow
3. **Behavioral Equivalence**: Focus on user-visible behavior, ignore internal implementation
4. **Evidence-Based**: Capture and share sanitized logs in release PRs
5. **Helper Reuse**: Extract common functionality into shared modules

## Architecture Components

### UAT Scripts

#### 1. `uat/side-by-side.py`
**Purpose**: Run identical tutorial steps in parallel with both tools

- Executes each tutorial step with sqitch and sqlitch simultaneously
- Compares command outputs after sanitizing timestamps/SHA1s
- Validates final database states are byte-identical
- Supports `--continue` flag to complete run even after failures
- Supports `--ignore` to skip specific problematic steps
- Outputs sanitized transcript suitable for PR evidence

**Exit Codes:**
- 0: All steps passed, databases match
- 1: One or more steps had behavioral differences

#### 2. `uat/forward-compat.py`
**Purpose**: Validate sqlitch → sqitch interoperability

- SQLitch deploys changes first
- Sqitch repeats each subsequent tutorial step
- Verifies sqitch can understand and work with sqlitch-created registries
- Confirms no corruption or incompatibility in forward direction

**Exit Codes:**
- 0: Sqitch successfully operated on sqlitch-created state
- 1: Sqitch failed to understand sqlitch artifacts

#### 3. `uat/backward-compat.py`
**Purpose**: Validate sqitch → sqlitch interoperability

- Sqitch deploys changes first
- SQLitch repeats each subsequent tutorial step
- Verifies sqlitch can understand and work with sqitch-created registries
- Confirms no corruption or incompatibility in backward direction

**Exit Codes:**
- 0: SQLitch successfully operated on sqitch-created state
- 1: SQLitch failed to understand sqitch artifacts

### Shared Helper Modules

Located in `uat/` directory:

#### `uat/sanitization.py`
**Purpose**: Normalize outputs for comparison

Functions:
- `sanitize_timestamps(text)`: Replace ISO8601 timestamps with `<TIMESTAMP>`
- `sanitize_sha1(text)`: Replace 40-char hex SHA1s with `<CHANGE_ID>`
- `sanitize_output(text)`: Apply all sanitization rules
- `strip_ansi_codes(text)`: Remove color/formatting codes

Rationale: Timestamps and change IDs vary by execution time but don't indicate behavioral differences.

#### `uat/comparison.py`
**Purpose**: Compare command outputs and database states

Functions:
- `compare_command_output(sqitch_out, sqlitch_out)`: Diff sanitized outputs
- `compare_sqlite_tables(db1_path, db2_path, tables)`: Validate data equivalence
- `format_diff(diff_result)`: Human-readable diff formatting
- `is_cosmetic_difference(diff)`: Classify diffs as cosmetic vs behavioral

Rationale: Centralize comparison logic to ensure consistent diff interpretation.

#### `uat/test_steps.py`
**Purpose**: Canonical list of tutorial steps

Data Structure:
```python
TUTORIAL_STEPS = [
    {"name": "init", "command": ["init", "flipr", ...]},
    {"name": "add_users", "command": ["add", "users", ...]},
    # ... all tutorial steps
]
```

Functions:
- `get_tutorial_steps()`: Return ordered step list
- `get_step_by_name(name)`: Retrieve specific step
- `skip_step(name)`: Mark step as skipped

Rationale: Single source of truth for tutorial sequence prevents drift between scripts.

#### `uat/__init__.py`
**Purpose**: Package initialization and exports

Exports:
- All functions from sanitization, comparison, test_steps modules
- Common constants (database names, table lists, etc.)

## Data Flow

### Side-by-Side Execution Flow
```
1. Clean workspace
2. For each tutorial step:
   a. Run sqitch command → capture output → sanitize
   b. Run sqlitch command → capture output → sanitize
   c. Compare sanitized outputs
   d. If mismatch: record failure, optionally continue
3. Compare final database states (user tables only)
4. Report results and exit with appropriate code
```

### Forward/Backward Compatibility Flow
```
1. Clean workspace
2. First tool deploys initial state
3. For each remaining step:
   a. Second tool executes step → capture output
   b. Validate no errors from second tool
   c. Check database state consistency
4. Report results and exit with appropriate code
```

## Testing Strategy

### Unit Tests
Located in `tests/uat/`:
- `test_uat_helpers.py`: Unit tests for all helper functions
- `test_forward_compat.py`: CLI and exit code validation
- `test_backward_compat.py`: CLI and exit code validation

### Integration Tests
Manual execution as documented in release checklist:
- Run all three scripts before each release
- Upload sanitized logs to release PR
- Review for behavioral differences

## Usage Patterns

### Standard Release Validation
```bash
# Execute all three scripts
python uat/side-by-side.py --out artifacts/side-by-side.log
python uat/forward-compat.py --out artifacts/forward-compat.log
python uat/backward-compat.py --out artifacts/backward-compat.log

# Check all exit codes are 0
echo $?  # Must be 0 for each script
```

### Debugging Failures
```bash
# Run side-by-side with --continue to see all failures
python uat/side-by-side.py --continue --out debug.log

# Ignore known cosmetic differences
python uat/side-by-side.py --ignore "step_name" --out filtered.log

# Inspect working directories (not cleaned up on failure)
ls -la sqitch_results/
ls -la sqlitch_results/
```

## Acceptance Criteria

Scripts pass when:
1. Exit code is 0
2. All command outputs are behaviorally equivalent (after sanitization)
3. Final database states match for user-visible tables
4. Only cosmetic differences allowed (whitespace, case formatting)

## Limitations and Future Work

**Current Limitations:**
- SQLite only (MySQL/PostgreSQL deferred post-1.0)
- Manual execution (no CI automation)
- Tutorial workflow only (not full command coverage)
- No performance benchmarking

**Post-1.0 Enhancements:**
- Multi-engine support (requires Docker orchestration)
- Automated nightly runs with flake detection
- Expanded command coverage beyond tutorial
- Performance regression detection

## References

- Sqitch Tutorial: https://sqitch.org/docs/manual/sqitchtutorial-sqlite/
- Implementation Spec: `specs/005-lockdown/spec.md`
- Contract Definition: `specs/005-lockdown/contracts/cli-uat-compatibility.md`
- Quickstart Guide: `specs/005-lockdown/quickstart.md`
