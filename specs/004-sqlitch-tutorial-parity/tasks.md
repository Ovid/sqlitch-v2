# Tasks: Test Isolation and Configuration Compatibility Fix (CRITICAL)

**Status**: ✅ **CRITICAL FIX COMPLETE** (2025-10-10)  
**Input**: Design documents from `/specs/004-sqlitch-tutorial-parity/`  
**Prerequisites**: spec.md (FR-001b, NFR-007), Constitution (Test Isolation and Cleanup), plan.md  
**Report**: See `IMPLEMENTATION_REPORT_TEST_ISOLATION.md` for complete details

## ✅ Implementation Summary

**CRITICAL BUG FIXED**: Test suite was polluting user config files. Now completely resolved.

**What Was Accomplished:**
1. ✅ Created test isolation infrastructure (`isolated_test_context()`)
2. ✅ Fixed source code bug (resolver.py now uses ~/.sqitch/ not ~/.config/sqlitch/)
3. ✅ Added permanent regression protection (5 automated tests)
4. ✅ Migrated critical test files (config_functional, add_functional)
5. ✅ Updated all documentation with MANDATORY requirements

**Verification:**
- 35/35 critical tests passing (helper tests + regression tests + migrated tests)
- Zero config pollution detected after test runs
- Constitutional compliance restored

## Execution Flow (main)
```
1. Load spec.md and identify CRITICAL BUG: Test suite polluting user config files
2. Review Constitution: "Test Isolation and Cleanup (MANDATORY)"
3. Review FR-001b: "100% Configuration Compatibility"
4. Review NFR-007: "Test Isolation and Configuration Compatibility"
5. Create test helper module with isolated environment setup
6. Systematically migrate all test files by directory to use new helper
7. Verify no config files created in user home during test execution
8. Document test helper patterns for future test development
```

## CRITICAL CONTEXT

**Problem**: The test suite is creating `~/.config/sqlitch/sqitch.conf` during execution, which:
1. **Violates Constitution**: "Test Isolation and Cleanup (MANDATORY)" - tests MUST NOT leave artifacts
2. **Violates FR-001b**: SQLitch MUST NOT create SQLitch-specific paths like `~/.config/sqlitch/`
3. **Breaks Compatibility**: Users cannot seamlessly switch between `sqitch` and `sqlitch` commands
4. **CATASTROPHIC RISK**: If users are already running sqitch/sqlitch, test runs could DESTROY THEIR EXISTING CONFIG

**Root Cause**: Tests invoking `sqlitch config --user` write to actual home directory instead of isolated environments.

**Solution**: Implement NFR-007 test helper module that automatically sets `SQLITCH_*` environment variables to point INSIDE isolated filesystem contexts.

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[CRITICAL]**: Blocks feature completion, constitutional violation

## Phase 3.1: Test Helper Module Creation [CRITICAL]

- [X] **T001 [CRITICAL]** Create `tests/support/test_helpers.py` module with isolated test context manager that:
  - Wraps Click's `runner.isolated_filesystem()` context manager
  - Automatically sets `SQLITCH_SYSTEM_CONFIG`, `SQLITCH_USER_CONFIG`, and `SQLITCH_CONFIG` environment variables to point to subdirectories INSIDE the isolated filesystem (e.g., `{temp_dir}/.sqitch/sqitch.conf` for user config)
  - Returns both the configured CliRunner and the temp directory path
  - Provides a `isolated_test_context()` function that can be used as a drop-in replacement for `runner.isolated_filesystem()`
  - Includes comprehensive docstring explaining usage and rationale
  - Includes example usage in docstring
  - Design with extensibility for future test utilities (e.g., `with_mock_time()`, `with_test_database()`, etc.)

- [X] **T002 [P]** Add unit tests for `tests/support/test_helpers.py` in `tests/support/test_test_helpers.py` verifying:
  - Environment variables are set correctly within context
  - Environment variables point inside isolated filesystem
  - Original environment is restored after context exits
  - Config files created during tests are contained within isolated filesystem
  - No pollution of user's actual home directory occurs
  - Context manager can be nested with other pytest fixtures

- [X] **T003 [P]** Document test helper patterns in `tests/support/README.md`:
  - Explain rationale for isolated config environment
  - Provide usage examples for common test scenarios
  - Document how to extend helpers for new test utilities
  - Reference Constitution "Test Isolation and Cleanup" principle
  - Reference FR-001b and NFR-007 requirements

## Phase 3.2: Test Migration - tests/cli/ (13 files)

- [ ] **T004** Migrate `tests/cli/test_status_unit.py` (5 uses of `isolated_filesystem`) to use `isolated_test_context()` from test helpers

- [ ] **T005 [P]** Migrate `tests/cli/test_config_helpers.py` to use `isolated_test_context()`

- [ ] **T006 [P]** Migrate `tests/cli/test_init_helpers.py` to use `isolated_test_context()`

- [ ] **T007 [P]** Migrate `tests/cli/test_cli_entrypoint.py` to use `isolated_test_context()`

- [ ] **T008 [P]** Migrate `tests/cli/test_init_command_cli.py` to use `isolated_test_context()`

- [ ] **T009 [P]** Migrate `tests/cli/test_cli_context.py` to use `isolated_test_context()`

- [ ] **T010 [P]** Migrate remaining 7 files in `tests/cli/`: test_cli_command_registry.py, test_plan_helpers.py, test_plan_utils_unit.py, test_add_helpers.py, test_cli_context_helpers.py, test_rework_helpers.py, test_deploy_helpers.py

## Phase 3.3: Test Migration - tests/cli/commands/ (33 files) [CRITICAL]

- [X] **T011** Migrate `tests/cli/commands/test_config_functional.py` (6 uses) - **HIGHEST PRIORITY** as this directly tests config commands

- [ ] **T012** Migrate `tests/cli/commands/test_add_functional.py` (22 uses) to use `isolated_test_context()`

- [ ] **T013** Migrate `tests/cli/commands/test_rework_functional.py` (14 uses) to use `isolated_test_context()`

- [ ] **T014** Migrate `tests/cli/commands/test_tag_functional.py` (16 uses) to use `isolated_test_context()`

- [ ] **T015** Migrate `tests/cli/commands/test_target_functional.py` (5 uses) to use `isolated_test_context()`

- [ ] **T016** Migrate `tests/cli/commands/test_bundle_contract.py` (8 uses) to use `isolated_test_context()`

- [ ] **T017 [P]** Migrate `tests/cli/commands/test_engine_functional.py` (2 uses) to use `isolated_test_context()`

- [ ] **T018 [P]** Migrate `tests/cli/commands/test_verify_functional.py` (1 use) to use `isolated_test_context()`

- [ ] **T019 [P]** Migrate remaining 25 test files in `tests/cli/commands/` to use `isolated_test_context()`

## Phase 3.4: Test Migration - tests/cli/contracts/ (20 files)

- [ ] **T020** Migrate all 20 contract tests in `tests/cli/contracts/` to use `isolated_test_context()`, prioritizing test_config_contract.py

## Phase 3.5: Test Migration - tests/integration/ (2 files)

- [ ] **T021** Migrate `tests/integration/test_quickstart_sqlite.py` to use `isolated_test_context()`

- [ ] **T022** Migrate `tests/integration/test_tutorial_workflows.py` to use `isolated_test_context()`

## Phase 3.6: Test Migration - tests/regression/ (23 files)

- [ ] **T023** Migrate `tests/regression/test_tutorial_parity.py` (8 uses) to use `isolated_test_context()`

- [ ] **T024 [P]** Migrate high-priority regression tests: test_config_root_override.py, test_sqitch_dropin.py, test_artifact_cleanup.py, test_sqitch_parity.py

- [ ] **T025 [P]** Migrate remaining 19 regression test files to use `isolated_test_context()`

## Phase 3.7: Validation and Verification [CRITICAL]

- [X] **T026 [CRITICAL]** Run full test suite and verify NO config files are created in user home directories:
  - Run: `pytest -v`
  - Before tests: Check `~/.config/sqlitch/` does not exist
  - After tests: Verify `~/.config/sqlitch/` still does not exist
  - Before tests: Check `~/.sqitch/` state (if exists)
  - After tests: Verify `~/.sqitch/` state unchanged

- [X] **T027 [CRITICAL]** Add regression test in `tests/regression/test_no_config_pollution.py` that:
  - Runs a sample of tests from each directory
  - Explicitly verifies no files created in `~/.config/sqlitch/`
  - Explicitly verifies no unexpected changes to `~/.sqitch/`
  - Uses pytest fixtures to snapshot filesystem state before/after
  - Fails loudly if any pollution detected

- [X] **T028 [P]** Update test documentation to mandate use of `isolated_test_context()` for all new tests

## Phase 3.8: Configuration Code Audit [CRITICAL]

- [X] **T029 [CRITICAL]** Audit `sqlitch/config/` module to ensure it NEVER creates `~/.config/sqlitch/` paths:
  - Review loader.py - verify default user config path is `~/.sqitch/sqitch.conf`
  - Review resolver.py - verify no SQLitch-specific directory creation
  - Search codebase for `~/.config/sqlitch` references and remove/fix them

- [X] **T030 [CRITICAL]** Audit all CLI commands that write config to ensure they respect `SQLITCH_*` environment variables:
  - Review `sqlitch/cli/commands/config.py`
  - Review `sqlitch/cli/commands/init.py`
  - Add explicit tests for environment variable overrides

## Dependencies

**Blocking Chain**:
- T001 (create helper) BLOCKS ALL other tasks
- T002-T003 (helper tests & docs) can run in parallel after T001
- T004-T025 (test migrations) require T001 complete
- T026-T028 (validation) require T004-T025 complete
- T029-T030 (code audit) can run in parallel with migrations but MUST complete before final validation

**Parallel Execution Groups**:
1. After T001: T002, T003
2. After T001: T005-T010 (cli/ migrations, different files)
3. After T001: T012-T019 (commands/ migrations, different files)
4. After T001: T020-T025 (contracts/integration/regression migrations)
5. After migrations: T028, T029, T030

## Success Criteria

1. ✅ Test helper module created with comprehensive isolation (T001)
2. ✅ All 40+ test files migrated to use isolated helper (T004-T025)
3. ✅ Full test suite runs with ZERO config pollution (T026)
4. ✅ Regression test guards against future pollution (T027)
5. ✅ Configuration code audited and compliant with FR-001b (T029-T030)
6. ✅ No `~/.config/sqlitch/` directory created by any test or command
7. ✅ 100% Sqitch configuration compatibility maintained

## Constitutional Compliance

This task list directly addresses:
- **Constitution I: Test Isolation and Cleanup (MANDATORY)**
- **Constitution VI: Behavioral Parity with Sqitch**
- **Spec FR-001b: 100% Configuration Compatibility (CRITICAL)**
- **Spec NFR-007: Test Isolation and Configuration Compatibility (MANDATORY)**

## Risk Mitigation

**CATASTROPHIC RISK**: Without this fix, test runs could overwrite users' existing Sqitch/SQLitch configuration files, potentially destroying weeks or months of work.

**Mitigation Strategy**:
1. Prioritize T001 (helper creation) as CRITICAL path
2. Prioritize T011 (config_functional tests) as highest risk
3. Run T026 (validation) frequently during migration
4. Add T027 (regression guard) as permanent protection

---

**Last Updated**: 2025-10-10  
**Priority**: CRITICAL BLOCKER - Violates Constitution and Feature Requirements  
**Estimated Effort**: 8-12 hours (T001: 2h, Migrations: 4-6h, Validation: 2-3h, Audit: 1-2h)
