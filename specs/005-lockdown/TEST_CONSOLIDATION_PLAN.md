# Test Suite Consolidation Plan

**Date**: 2025-10-12  
**Branch**: 005-lockdown  
**Reference**: Phase 3.7 in `tasks.md` (T130a–T134d)

## Overview

This document details the plan to consolidate the test suite from 121 files to ~84-87 files, reducing duplication and improving maintainability while preserving all 1,182 tests and 92%+ coverage.

## Analysis Summary

See the detailed analysis report in the previous conversation for full findings. Key opportunities:

| Category | Files to Remove | Priority | Estimated Impact |
|----------|----------------|----------|------------------|
| Contract duplication | 19 files | HIGH | ⭐⭐⭐⭐⭐ |
| Lockdown files | 6 files | MEDIUM | ⭐⭐⭐⭐ |
| Helper files | 6 files | MEDIUM | ⭐⭐⭐⭐ |
| Identity fragmentation | 2 files | MEDIUM | ⭐⭐⭐ |
| **Total** | **33 files** | - | **High** |

## Phase 3.7a: Contract Test Duplication (T130a–T130t)

### Problem
19 commands have duplicate contract test files in both locations:
- `tests/cli/commands/test_*_contract.py` (older location)
- `tests/cli/contracts/test_*_contract.py` (canonical location)

### Solution
Merge all contract tests into `tests/cli/contracts/` and delete duplicates from `tests/cli/commands/`.

### Tasks Breakdown

Each task follows this pattern:
1. Read both files to understand test coverage
2. Identify unique tests in commands version
3. Add unique tests to contracts version (if any)
4. Delete the commands version
5. Run tests to verify: `pytest tests/cli/contracts/test_X_contract.py -v`

**19 Individual Tasks**: T130a (add), T130b (bundle), T130c (checkout), T130d (config), T130e (deploy), T130f (engine), T130g (help), T130h (init), T130i (log), T130j (plan), T130k (rebase), T130l (revert), T130m (rework), T130n (show), T130o (status), T130p (tag), T130q (target), T130r (upgrade), T130s (verify)

**Validation Task**: T130t - Run full suite to verify all merges successful

**Expected Outcome**: 
- Remove 19 duplicate files from `tests/cli/commands/`
- All contract tests in canonical `tests/cli/contracts/` location
- `tests/cli/commands/` contains only `test_*_functional.py` files

## Phase 3.7b: Lockdown Test Files (T131a–T131g)

### Problem
6 "_lockdown" suffixed files exist as separate files when they should be test classes within the base test file.

### Solution
Merge each lockdown file into its corresponding base file as a test class.

### Tasks Breakdown

Each task follows this pattern:
1. Read the lockdown file
2. Wrap all tests in a test class: `class TestModuleLockdown:`
3. Add the class to the base test file
4. Delete the lockdown file
5. Run tests to verify: `pytest tests/path/to/test_base.py -v`

**6 Individual Tasks**:
- T131a: `test_main_lockdown.py` → `test_main_module.py`
- T131b: `test_resolver_lockdown.py` → `test_resolver.py`
- T131c: `test_quickstart_lockdown.py` → keep or merge into docs test
- T131d: `test_sqlite_lockdown.py` → `test_sqlite.py`
- T131e: `test_state_lockdown.py` → `test_state.py`
- T131f: `test_identity_lockdown.py` → `test_identity.py`

**Validation Task**: T131g - Run full suite to verify all merges successful

**Expected Outcome**:
- Remove 6 "_lockdown" files
- Better organization using test classes
- Single source of truth per module

## Phase 3.7c: Helper Test Files (T132a–T132h)

### Problem
7 helper test files exist when helper tests should be co-located with command functional tests.

### Solution
Merge 6 command-specific helper files into their corresponding functional test files as test classes. Keep 1 shared helper file.

### Tasks Breakdown

Each task follows this pattern:
1. Read the helper file
2. Wrap tests in a test class: `class TestCommandHelpers:`
3. Add the class to the functional test file
4. Delete the helper file
5. Run tests to verify: `pytest tests/cli/commands/test_X_functional.py -v`

**6 Individual Merge Tasks**:
- T132a: `test_add_helpers.py` → `test_add_functional.py`
- T132b: `test_config_helpers.py` → `test_config_functional.py`
- T132c: `test_deploy_helpers.py` → `test_deploy_functional.py`
- T132d: `test_init_helpers.py` → `test_init_functional.py`
- T132e: `test_plan_helpers.py` → appropriate plan test file
- T132f: `test_rework_helpers.py` → `test_rework_functional.py`

**Keep As-Is**: T132g - `test_cli_context_helpers.py` (tests shared context)

**Validation Task**: T132h - Run full suite to verify all merges successful

**Expected Outcome**:
- Remove 6 helper files
- Helper tests co-located with command tests
- Improved discoverability

## Phase 3.7d: Identity Test Fragmentation (T133a–T133c)

### Problem
Identity tests split across 3 files for a single module (`sqlitch.utils.identity`).

### Solution
Merge edge cases into main identity test file. Lockdown file handled in Phase 3.7b.

### Tasks Breakdown

- T133a: Merge `test_identity_edge_cases.py` into `test_identity.py` as `class TestIdentityEdgeCases:`
- T133b: Note that lockdown file handled by T131f
- T133c: Validation - run `pytest tests/utils/test_identity.py -v`

**Expected Outcome**:
- Remove 1 edge_cases file (lockdown file removed in Phase 3.7b)
- Single comprehensive identity test file

## Phase 3.7e: Final Validation (T134a–T134d)

### Validation Tasks

- T134a: Run full test suite: `pytest tests/ -v`
- T134b: Verify metrics unchanged:
  - Test count: ~1,182 tests (should be same)
  - Coverage: 92%+ (should be same or higher)
  - Skipped: 21 tests (should be same)
- T134c: Update migration document with consolidation summary
- T134d: Verify file count: `find tests -type f -name "test_*.py" | wc -l` should show ~84-87 files

**Expected Outcome**:
- All tests passing
- Coverage maintained
- Significant file count reduction
- Documentation updated

## Success Criteria

### Before Consolidation
- **Files**: 121 test files
- **Tests**: 1,182 tests passing, 21 skipped
- **Coverage**: 92.20%
- **Organization**: Scattered, duplicated

### After Consolidation
- **Files**: ~84-87 test files (**~34-37 fewer**)
- **Tests**: 1,182 tests passing, 21 skipped (**unchanged**)
- **Coverage**: ≥92.20% (**maintained or improved**)
- **Organization**: Consolidated, logical, discoverable

## Execution Strategy

1. **Work in phases**: Complete all tasks in one phase before moving to next
2. **Small commits**: Commit after each successful merge
3. **Frequent validation**: Run tests after each task
4. **Document changes**: Update migration doc as you go

## Testing Protocol

After each task:
```bash
# Activate environment
source .venv/bin/activate

# Run specific test file
pytest tests/path/to/test_file.py -v

# Verify full suite still passes
pytest tests/ -q
```

After each phase:
```bash
# Run full suite with coverage
pytest tests/ --cov=sqlitch --cov-report=term

# Verify coverage maintained
# Should see: "Required test coverage of 90.0% reached. Total coverage: 92.XX%"
```

## Rollback Plan

If a merge causes issues:
1. Git revert the commit
2. Investigate the conflict
3. Fix the issue
4. Try again

Each task is small and independent, so rollbacks are straightforward.

## Benefits

1. **Reduced Maintenance**: 28-30% fewer files to maintain
2. **Better Discoverability**: Tests in logical locations
3. **Clearer Organization**: Contract vs functional separation
4. **Easier Navigation**: Less file switching
5. **No Duplication**: Single source of truth for each test

## Constitutional Compliance

✅ **Test-First Development**: All tests preserved, no functionality lost  
✅ **Simplicity-First**: Fewer files, clearer structure  
✅ **Documented Interfaces**: Migration document tracks changes  
✅ **Quality Gates**: Coverage maintained at 92%+

---

**Next Steps**: Begin with Phase 3.7a (Contract duplication - highest priority)
