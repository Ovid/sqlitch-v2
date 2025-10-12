# T120 & T121 Implementation Plan

**Status**: Ready for systematic execution  
**Created**: 2025-10-12  
**Priority**: P1 (both tasks block lockdown completion)

## Overview

Tasks T120 (mypy --strict) and T121 (flake8) require coordinated refactoring across
multiple CLI command modules. This document outlines a systematic approach to resolve
all violations while maintaining test coverage and Sqitch parity.

## Current State (2025-10-12)

### T120: mypy --strict backlog
- **Total errors**: 76
- **Primary hotspots**:
  - `sqlitch/config/loader.py` (2 errors): `optionxform` assignment type issues
  - `sqlitch/registry/state.py` (4 errors): Missing generic type parameters for `tuple`
  - `sqlitch/engine/sqlite.py` (2 errors): Optional/Any type issues
  - `sqlitch/plan/parser.py` (7 errors): Type incompatibility in change/tag parsing
  - `sqlitch/cli/options.py` (2 errors): Redundant casts
  - `sqlitch/cli/commands/__init__.py` (1 error): Override signature mismatch
  - `sqlitch/utils/logging.py` (3 errors): Optional TextIO handling
  - `sqlitch/config/resolver.py` (1 error): Optional path argument
  - `sqlitch/cli/main.py` (1 error): Unused type ignore comment
  - `sqlitch/cli/commands/verify.py` (6 errors): EngineTarget vs str typing
  - `sqlitch/cli/commands/target.py` (10 errors): Method assignment issues (5 files × 2 each)
  - `sqlitch/cli/commands/status.py` (4 errors): Similar to verify.py
  - `sqlitch/cli/commands/plan.py` (1 error): Path | str | None typing
  - `sqlitch/cli/commands/help.py` (3 errors): BaseCommand type alias issues
  - `sqlitch/cli/commands/engine.py` (2 errors): Method assignment issues

### T121: flake8 violations
- **Total violations**: 72 (reduced from 73)
- **Breakdown**:
  - 48× E501 (line too long) - primarily in `sqlitch/registry/migrations.py`
  - 14× F401 (unused imports) - scattered across CLI command modules
  - 6× E203 (whitespace before ':') - black conflict, can be ignored
  - 3× F811 (redefinition) - `deploy.py` has duplicate helper imports
  - 1× W293 (blank line with whitespace) - `registry/migrations.py`

## Execution Strategy

### Phase 1: Quick Wins (Low Risk)
1. **F401 (Unused Imports)** - Already started, 1/14 complete
   - Remove simple single-line unused imports
   - Handle multi-import lines carefully (may need manual splitting)
   - Files affected: add.py, deploy.py, log.py, plan.py, revert.py, rework.py, tag.py, upgrade.py, verify.py
   
2. **W293 (Whitespace)** - Trivial fix
   - Remove trailing whitespace from `registry/migrations.py:191`
   
3. **E203 (Whitespace before ':')** - Configure flake8 to ignore
   - This is a known black/flake8 conflict
   - Add to `.flake8` config: `ignore = E203`
   - Affects: engine.py, sqlite.py, target.py (6 occurrences)

4. **F811 (Redefinition)** - Remove duplicate imports
   - `deploy.py:35` vs `deploy.py:903` - `generate_change_id`
   - `verify.py:12` vs `verify.py:83, :230` - `config_resolver`
   - Check if the redefined versions are actually used

### Phase 2: Type Safety (Medium Risk)
5. **mypy: Simple type fixes**
   - Remove redundant casts in `cli/options.py` (2 fixes)
   - Remove unused type ignore in `cli/main.py` (1 fix)
   - Add generic parameters to `tuple` in `registry/state.py` (4 fixes)
   - Fix Optional path argument in `config/resolver.py` (1 fix)
   
6. **mypy: TextIO handling**
   - `utils/logging.py` - properly handle Optional TextIO
   - May need assertion or early return pattern

### Phase 3: Line Length (Low Risk, High Volume)
7. **E501 (Line too long)** - 48 occurrences
   - **Strategy**: Use black/auto-formatting where possible
   - Most are in `registry/migrations.py` (SQL strings)
   - For SQL strings, consider using implicit string concatenation:
     ```python
     # Before
     sql = "CREATE TABLE very_long_table_name (col1 TEXT, col2 TEXT, ...)"
     
     # After
     sql = (
         "CREATE TABLE very_long_table_name "
         "(col1 TEXT, col2 TEXT, ...)"
     )
     ```
   - Or use `textwrap.dedent()` for readability

### Phase 4: Complex Type Issues (High Risk)
8. **mypy: Target configuration typing**
   - `cli/commands/target.py` - method assignment issues (10 errors)
   - `cli/commands/verify.py` - EngineTarget vs str (6 errors)
   - `cli/commands/status.py` - similar issues (4 errors)
   - **Root cause**: ConfigParser's `optionxform` is a method, can't reassign
   - **Solution**: Create wrapper class or use different approach

9. **mypy: Plan parser types**
   - `plan/parser.py` - Change | Tag | None vs Change | None (7 errors)
   - May require refactoring parse logic or adding type narrowing

10. **mypy: BaseCommand type alias**
    - `cli/commands/help.py` - variable vs type alias issues (3 errors)
    - May need to use proper type alias syntax

## Testing Strategy

After each phase:
```bash
# Run affected module tests
pytest tests/<module>/ -v

# Check mypy progress
mypy --strict sqlitch/ 2>&1 | wc -l

# Check flake8 progress
flake8 sqlitch/ --count

# Ensure full test suite still passes
pytest --no-cov -x
```

## Regression Guards

Once fixes are complete, add enforcement to prevent regressions:

### For mypy (T120)
Create `tests/test_type_checking.py`:
```python
def test_mypy_strict_compliance():
    """Ensure mypy --strict passes on all code."""
    result = subprocess.run(
        ["mypy", "--strict", "sqlitch/"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"mypy errors:\n{result.stdout}"
```

### For flake8 (T121)
Create `tests/test_linting.py`:
```python
def test_flake8_compliance():
    """Ensure flake8 passes on all code."""
    result = subprocess.run(
        ["flake8", "sqlitch/"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"flake8 violations:\n{result.stdout}"
```

## Risk Mitigation

- **Commit frequently**: After each file or small group of related fixes
- **Run tests after each fix**: Don't accumulate untested changes
- **Consult Sqitch source**: For any behavioral questions during refactoring
- **Document type choices**: Add comments explaining complex type annotations
- **Keep diffs small**: Easier to review and revert if needed

## Estimated Effort

- **Phase 1 (Quick Wins)**: 1-2 hours
- **Phase 2 (Simple Types)**: 1-2 hours  
- **Phase 3 (Line Length)**: 2-3 hours
- **Phase 4 (Complex Types)**: 3-4 hours
- **Testing & Regression Guards**: 1 hour

**Total**: 8-12 hours of focused work

## Success Criteria

- [X] T122: Bandit SHA1 warning resolved (complete)
- [X] T123: Automated black/isort enforcement (complete)
- [ ] T120: `mypy --strict sqlitch/` exits with code 0
- [ ] T121: `flake8 sqlitch/` exits with code 0
- [ ] All existing tests continue to pass
- [ ] New regression guard tests added
- [ ] Tasks.md updated to mark T120 and T121 complete

## Notes

- E203 (whitespace before ':') conflicts with black formatting
  - Solution: Configure flake8 to ignore E203
  - This is a known and accepted conflict in the Python community
  
- ConfigParser `optionxform` reassignment is a common mypy pain point
  - Sqitch compatibility requires preserving key case
  - May need to create a helper wrapper or suppress specific lines

- SQL string line lengths in migrations.py are the bulk of E501
  - Consider extracting to separate .sql files if refactoring gets complex
  - Or use multi-line string literals with proper indentation
