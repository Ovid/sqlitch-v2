# Session Continuity Guide for SQLitch Lockdown Phase

## Quick Start (Every New Session)

```bash
cd /Users/poecurt/projects/sqlitch
source .venv/bin/activate
```

**ALWAYS run these two commands before starting any work.**

## Current Status Snapshot

### ✅ Completed
- **Phase 3.1**: All setup and baseline tasks (T001-T005)
- **Phase 3.2**: Core lockdown tests (T010-T018)
  - Helper modules created and tested
  - UAT compatibility script stubs in place
  - Documentation validation tests added
- **Partial Phase 3.3**: T111, T114 implementation complete

### 📊 Current Metrics
- **Tests**: 1003 passing, 22 skipped
- **Coverage**: 91.29% (exceeds 90% requirement ✅)
- **Branch**: `005-lockdown`
- **Helper Modules**: `uat/sanitization.py`, `uat/comparison.py`, `uat/test_steps.py` ✅
- **UAT Scripts**: `uat/scripts/forward-compat.py`, `uat/scripts/backward-compat.py` (scaffolded with skip mode)

### 🎯 Next Priority Tasks
See `specs/005-lockdown/tasks.md` for complete list. Critical next steps:

1. **T115**: Refactor `uat/side-by-side.py` to use shared helpers
2. **T116-T117**: Implement full forward/backward compatibility scripts
3. **T110, T112, T113**: Module-specific coverage improvements
4. **T040-T044**: Documentation updates
5. **T060-T066**: Final validation and release prep

## Common Operations

### Run Specific Test
```bash
pytest tests/path/to/test_file.py -v
```

### Run Test with Coverage
```bash
pytest tests/path/to/test_file.py --cov=sqlitch
```

### Run Full Suite (Required After Each Task)
```bash
pytest
```

### Verify Coverage
```bash
pytest --cov=sqlitch --cov-report=term
```

### Quality Gates
```bash
mypy --strict sqlitch/
pydocstyle sqlitch/
black --check .
isort --check-only .
pip-audit
bandit -r sqlitch/
```

## Task Completion Checklist

For each task:
1. ☑️ Activate venv (`source .venv/bin/activate`)
2. ☑️ Run task-specific test to see current state
3. ☑️ Implement changes
4. ☑️ Rerun task-specific test until it passes
5. ☑️ Run full test suite (`pytest`)
6. ☑️ Verify coverage still ≥90%
7. ☑️ Mark task `[X]` in `specs/005-lockdown/tasks.md`
8. ☑️ Commit changes

## File Organization

### UAT Infrastructure
```
uat/
├── __init__.py
├── sanitization.py          # Sanitization helpers (HEX_ID, timestamps)
├── comparison.py            # Database comparison utilities
├── test_steps.py            # Tutorial step manifest (46 steps)
├── side-by-side.py          # Existing parity harness (needs refactor)
└── scripts/
    ├── forward-compat.py    # SQLitch → Sqitch validation (scaffolded)
    └── backward-compat.py   # Sqitch → SQLitch validation (scaffolded)
```

### Test Organization
```
tests/
├── uat/
│   ├── test_uat_helpers.py       # Helper module tests ✅
│   ├── test_forward_compat.py    # Forward script CLI tests ✅
│   └── test_backward_compat.py   # Backward script CLI tests ✅
├── docs/
│   └── test_quickstart_lockdown.py  # Documentation validation ✅
├── config/
│   ├── test_resolver_lockdown.py    # Resolver edge cases ✅
│   └── ...
├── registry/
│   ├── test_state_lockdown.py       # State mutation tests ✅
│   └── ...
└── ...
```

## Known Issues & Notes

1. **UAT Scripts**: Forward/backward compatibility scripts exist as stubs with skip mode. Full implementation pending (T116-T117).

2. **Side-by-Side Refactor**: The `uat/side-by-side.py` script still contains inline sanitization logic that should use the shared helpers (T115).

3. **CLI Lockdown Tests**: Tasks T019-T034 define additional CLI contract tests. Many commands already have extensive contract coverage in existing test files.

4. **Coverage Gaps**: Some modules (resolver, identity, CLI main) still need targeted improvements to close specific branch coverage gaps.

5. **Documentation**: README and CONTRIBUTING will need updates once UAT harnesses are fully implemented (T040-T044).

## Recovery Commands

If tests fail unexpectedly:
```bash
# Clean and reinstall
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

If you need to check what changed:
```bash
git status
git diff
```

## Reference Documents

- **This Guide**: `specs/005-lockdown/SESSION_CONTINUITY.md` (session workflow)
- **Task List**: `specs/005-lockdown/tasks.md`
- **Technical Plan**: `specs/005-lockdown/plan.md`
- **Research Notes**: `specs/005-lockdown/research.md`
- **UAT Contracts**: `specs/005-lockdown/contracts/cli-uat-compatibility.md`
- **Quickstart Guide**: `specs/005-lockdown/quickstart.md`
- **Data Model**: `specs/005-lockdown/data-model.md`

## Contact Points

- **Repository**: sqlitch-v2 (Ovid)
- **Branch**: 005-lockdown
- **Python Version**: 3.11+ (tested with 3.13.7)
- **Coverage Requirement**: ≥90% (currently 91.29%)

---

**Last Updated**: 2025-10-10  
**Test Count**: 1003 passing, 22 skipped  
**Next Session Start**: Run `source .venv/bin/activate` first!
