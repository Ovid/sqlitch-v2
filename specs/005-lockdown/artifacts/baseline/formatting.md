# Formatting Baseline (2025-10-10)

## Black `--check`
- **Status**: Failed (exit 1)
- **Command**: `black --check .`
- **Files requiring reformat**:
  - `scripts/add_global_options.py`
  - `scripts/migrate_test_isolation.py`
  - `scripts/audit_global_options.py`
  - `scripts/check-skips.py`
  - `scripts/audit_exit_codes.py`
  - `scripts/audit_stub_validation.py`
  - `uat/side-by-side.py`
- **Remediation**: `black .` applied on 2025-10-10 (see git diff for normalized formatting).
- **Verification**: `black --check .` now reports no changes required.

## isort `--check-only`
- **Status**: Failed (exit 1)
- **Command**: `isort --check-only .`
- **Files requiring import ordering fixes**:
  - `temp/side-by-side.py`
  - `uat/side-by-side.py`
  - `bin/sqlitch`
  - `scripts/add_global_options.py`
  - `scripts/check-skips.py`
- **Remediation**: `isort .` executed on 2025-10-10; re-run checks should now pass barring new changes.
- **Verification**: `isort --check-only .` succeeds (noting configured skips in 7 files).
