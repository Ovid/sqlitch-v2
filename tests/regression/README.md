# Regression Tests Directory

## Overview

This directory contains **placeholder tests** for future regression coverage. Most tests here are currently skipped pending implementation of specific features or task completion.

## Migration History (2025-10-12)

As part of test suite reorganization, most regression tests were **migrated to their corresponding feature test files**:

### Migrated Tests

| Original File | New Location | Notes |
|--------------|--------------|-------|
| `test_tutorial_parity.py` | `tests/integration/test_tutorial_parity.py` | Integration test |
| `test_sqlite_deploy_atomicity.py` | `tests/engine/test_sqlite.py` | Added to deploy behavior section |
| `test_sqlite_deploy_script_transactions.py` | `tests/engine/test_sqlite.py` | Transaction handling tests |
| `test_sqlite_registry_attach.py` | `tests/engine/test_sqlite.py` | Registry isolation tests |
| `test_credentials_precedence.py` | Deleted (duplicate) | Already covered by `tests/config/test_resolver_credentials.py` |
| `test_credentials_redaction.py` | `tests/utils/test_logging.py` | Credential redaction section |
| `test_observability_logging.py` | `tests/utils/test_logging.py` | Observability opt-in section |
| `test_error_messages.py` | `tests/cli/commands/test_deploy_functional.py` | New `TestDeployErrorMessages` class |
| `test_global_options_parity.py` | `tests/cli/contracts/test_global_options_contract.py` | GC-002 tests |
| `test_exit_code_parity.py` | `tests/cli/contracts/test_global_options_contract.py` | GC-003 tests |
| `test_error_output_parity.py` | `tests/cli/contracts/test_global_options_contract.py` | GC-004 tests |
| `test_help_format_parity.py` | `tests/cli/contracts/test_global_options_contract.py` | GC-001 tests |
| `test_unknown_option_rejection.py` | `tests/cli/contracts/test_global_options_contract.py` | GC-005 tests |
| `test_no_config_pollution.py` | `tests/test_no_config_pollution.py` | Meta-test moved to root |
| `test_test_isolation_enforcement.py` | `tests/test_test_isolation_enforcement.py` | Meta-test moved to root |
| `test_engine_suite_skips.py` | `tests/test_engine_suite_skips.py` | Pytest config test moved to root |

## Remaining Placeholder Tests

The following tests remain in this directory as **skipped placeholders** for future work:

### Pending Implementation

- `test_artifact_cleanup.py` - **T035**: Artifact cleanup regression coverage
- `test_config_root_override.py` - **T034**: Configuration root override isolation
- `test_docker_skip.py` - **T033**: Docker unavailability skip behavior
- `test_onboarding_workflow.py` - **T029**: Onboarding workflow documentation
- `test_sqitch_conflicts.py` - **T030a**: Sqitch/SQLitch artifact conflict detection
- `test_sqitch_dropin.py` - **T030**: Drop-in Sqitch artifact parity
- `test_sqitch_parity.py` - **T028**: Regression parity against Sqitch projects
- `test_timestamp_parity.py` - **T032**: Timestamp and timezone parity
- `test_unsupported_engine.py` - **T031**: Unsupported engine failure handling

## Guideline: When to Use This Directory

**Do NOT add new regression tests here.** Instead:

1. **For existing feature tests**: Add regression tests directly to the corresponding feature test file (e.g., `test_sqlite.py`, `test_deploy_functional.py`)
2. **For integration tests**: Use `tests/integration/`
3. **For cross-cutting concerns**: Use `tests/cli/contracts/` for CLI contracts
4. **For meta-tests**: Use `tests/` root (e.g., `test_no_config_pollution.py`)

**Only use this directory for**:
- Placeholder tests tied to specific tracked tasks (with skip markers)
- Temporary regression guards that will be merged once the feature area is identified

## References

- **Migration Documentation**: See `MIGRATION_COMPLETE.md` for detailed migration notes
- **Test Isolation**: See `README_ENFORCEMENT.md` for test isolation requirements
- **Constitutional Mandate**: Tests must follow Constitution I (Test Isolation and Cleanup)
