# T120 Execution Summary

**Status**: Ready for Execution  
**Created**: 2025-10-12  
**Baseline**: 62 mypy --strict errors  
**Goal**: 0 errors (100% type safety compliance)

## Quick Reference

### Current State
- **T120 (Regression Guard)**: ✅ Complete - Baseline tracking at 62 errors
- **T121 (Flake8)**: ✅ Complete - Zero violations, automated enforcement
- **T122 (Bandit)**: ✅ Complete - SHA1 usedforsecurity=False
- **T123 (Black/Isort)**: ✅ Complete - Automated enforcement

### Remaining Work
- **27 granular tasks** (T120a - T120aa) to eliminate 62 mypy errors
- Tasks organized into 10 phases
- Each task: ≤6 errors, ≤30 minutes

## Task Checklist

### Phase 1: Quick Wins (7 errors)
- [ ] T120a: Remove unused type:ignore (cli/main.py) → -1 error
- [ ] T120b: Remove redundant casts (cli/options.py) → -2 errors
- [ ] T120c: Fix optionxform type:ignore (8 files) → -4 errors

**Checkpoint**: 55 errors remaining

### Phase 2: Registry State (4 errors)
- [ ] T120d: Add tuple type parameters (state.py) → -2 errors
- [ ] T120e: Fix datetime type casts (state.py) → -2 errors

**Checkpoint**: 51 errors remaining

### Phase 3: Plan Parser (6 errors)
- [ ] T120f: Fix _parse_compact_entry type (parser.py) → -3 errors
- [ ] T120g: Fix _parse_uuid None handling (parser.py) → -1 error
- [ ] T120h: Fix script_paths dict types (parser.py) → -2 errors

**Checkpoint**: 45 errors remaining

### Phase 4: SQLite Engine (2 errors)
- [ ] T120i: Fix _build_connect_arguments (sqlite.py) → -1 error
- [ ] T120j: Fix connect return type (sqlite.py) → -1 error

**Checkpoint**: 43 errors remaining

### Phase 5: Config Module (5 errors)
- [ ] T120k: Fix Path None handling (resolver.py) → -1 error
- [ ] T120l: Fix range() None arguments (config.py) → -4 errors

**Checkpoint**: 38 errors remaining

### Phase 6: Logging (3 errors)
- [ ] T120m: Fix TextIO handling (logging.py) → -3 errors

**Checkpoint**: 35 errors remaining

### Phase 7: Deploy Command (5 errors)
- [ ] T120n: Fix registry_uri None (deploy.py) → -1 error
- [ ] T120o: Fix target variable type (deploy.py) → -1 error
- [ ] T120p: Fix dict type annotations (deploy.py) → -2 errors
- [ ] T120q: Fix set[str] assignment (deploy.py) → -1 error

**Checkpoint**: 30 errors remaining

### Phase 8: CLI Commands (16 errors)
- [ ] T120r: Fix verify.py EngineTarget → -5 errors
- [ ] T120s: Fix status.py types → -3 errors
- [ ] T120t: Fix show.py Tag type → -5 errors
- [ ] T120u: Fix plan.py _format_path → -1 error
- [ ] T120v: Fix help.py BaseCommand → -3 errors
- [ ] T120w: Fix __init__.py show() override → -1 error

**Checkpoint**: 14 errors remaining

### Phase 9: Rework & Revert (8 errors)
- [ ] T120x: Fix rework.py Path types → -6 errors
- [ ] T120y: Fix revert.py types → -2 errors

**Checkpoint**: 6 errors remaining

### Phase 10: Final Cleanup
- [ ] T120z: Update BASELINE_MYPY_ERROR_COUNT to 0
- [ ] T120aa: Document achievement

**Final**: 0 errors ✅

## Validation Commands

### After Each Task
```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate

# Check mypy error count
mypy --strict sqlitch/ 2>&1 | grep "^Found"

# Run type safety test
pytest tests/test_type_safety.py -v

# Ensure no test regressions
pytest --tb=short
```

### Expected Output Pattern
```
# Start
Found 62 errors in 20 files

# After Phase 1
Found 55 errors in 19 files

# After Phase 2
Found 51 errors in 18 files

# ... (progressive reduction)

# Final
Success: no issues found in 53 source files
```

## Execution Tips

1. **One Task at a Time**: Complete, test, commit before moving to next
2. **Read the Error**: Each task references specific mypy output
3. **Consult Sqitch**: Verify behavior doesn't change
4. **Test Early**: Run pytest after each fix
5. **Commit Often**: Small commits easier to review/revert

## File Reference

- **Implementation Plan**: `specs/005-lockdown/T120_T121_PLAN.md`
- **Task List**: `specs/005-lockdown/tasks.md` (Phase 3.3b)
- **Type Safety Test**: `tests/test_type_safety.py`
- **Baseline**: `BASELINE_MYPY_ERROR_COUNT = 62`

## Success Criteria

- [ ] All 27 tasks marked [X] in tasks.md
- [ ] `mypy --strict sqlitch/` exits with code 0
- [ ] `pytest tests/test_type_safety.py` passes
- [ ] All 1112+ tests continue to pass
- [ ] `BASELINE_MYPY_ERROR_COUNT` updated to 0
- [ ] Documentation updated in IMPLEMENTATION_REPORT_LOCKDOWN.md

## Estimated Effort

- **Quick Wins (Phase 1-3)**: 2-3 hours
- **Engine/Config (Phase 4-6)**: 2 hours
- **Commands (Phase 7-9)**: 4-5 hours
- **Final (Phase 10)**: 30 minutes

**Total**: 8-10 hours focused work

---
*Ready to execute - all tasks are atomic and independently testable*
