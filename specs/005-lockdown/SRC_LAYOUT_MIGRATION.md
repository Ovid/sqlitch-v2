# Src Layout Migration Plan

**Date**: 2025-10-13  
**Branch**: 005-lockdown  
**Constitutional Principle**: Simplicity-First, Test-First Development

## Overview
Migrate SQLitch from flat layout to src layout per Python Packaging Authority guidelines. This is a structural improvement that prevents accidental import issues and enforces proper installation workflows.

## Rationale

### Benefits of Src Layout
1. **Import Safety**: Prevents accidental usage of in-development code instead of installed package
2. **Packaging Correctness**: Ensures editable installs only import intended files
3. **Test Reliability**: Forces tests to import from installed package, catching packaging issues early
4. **Industry Standard**: Aligns with PyPA recommendations and modern Python project structure

### Current State (Flat Layout)
```
sqlitch/                 # Import package at root
├── cli/
├── config/
├── engine/
└── ...
tests/                   # Tests at root
pyproject.toml          # Config at root
```

### Target State (Src Layout)
```
src/
└── sqlitch/            # Import package under src/
    ├── cli/
    ├── config/
    ├── engine/
    └── ...
tests/                  # Tests still at root
pyproject.toml         # Config at root
```

## Migration Steps

### Phase 1: Directory Restructuring
1. Create `src/` directory
2. Move `sqlitch/` package into `src/sqlitch/`
3. Create `src/sqlitch/__main__.py` for direct Python execution
4. Verify no files left behind

### Phase 2: Configuration Updates
1. Update `pyproject.toml`:
   - Change `packages.find.where` to `["src"]`
   - Update coverage source paths
   - Update mypy paths
2. Update `tox.ini`:
   - Update PYTHONPATH references
   - Update command targets
3. Update `mypy.ini`:
   - Add src to paths
4. Update `.flake8` and other linting configs
5. Update `.gitignore` if needed

### Phase 3: Import Path Updates
1. Tests remain unchanged (import from installed package)
2. UAT scripts may need PYTHONPATH adjustments
3. Entry point configured in `pyproject.toml` [project.scripts]

### Phase 4: Documentation Updates
1. Update README.md installation instructions
2. Update CONTRIBUTING.md development workflow
3. Update specs/005-lockdown/plan.md project structure section
4. Update specs/005-lockdown/quickstart.md

### Phase 5: Validation
1. Run `pip install -e .` in clean venv
2. Run full test suite: `pytest`
3. Run all quality gates: `tox`
4. Test CLI directly: `sqlitch --version`
5. Test UAT scripts: `python uat/side-by-side.py --help`
6. Verify imports work from installed package

## File Changes Required

### New Files
- `src/` (directory)
- `src/sqlitch/__main__.py` (CLI entry point with sys.path workaround)

### Modified Files
- `pyproject.toml` (packaging config, entry points)
- `tox.ini` (PYTHONPATH)
- `mypy.ini` (paths)
- `specs/005-lockdown/plan.md` (project structure section)
- `specs/005-lockdown/quickstart.md` (setup instructions)
- `README.md` (installation/development)
- `CONTRIBUTING.md` (workflow)

### Moved Files
- `sqlitch/*` → `src/sqlitch/*` (entire package tree)

## Risks & Mitigations

### Risk 1: Import Breakage
- **Mitigation**: All imports use absolute paths (`from sqlitch.cli...`)
- **Mitigation**: Editable install required for development (already best practice)
- **Mitigation**: Full test suite validates imports

### Risk 2: UAT Script Breakage
- **Mitigation**: Scripts use installed package or explicit sys.path manipulation
- **Mitigation**: Test all three UAT scripts after migration

### Risk 3: IDE/Editor Confusion
- **Mitigation**: Editable install makes src layout transparent to IDEs
- **Mitigation**: Update .vscode/settings.json if present

### Risk 4: CI/CD Breakage
- **Mitigation**: Verify tox environments work
- **Mitigation**: Test in clean venv before pushing

## Success Criteria
- [ ] `pip install -e .` succeeds
- [ ] `sqlitch --version` works
- [ ] `pytest` passes all tests (maintain ≥90% coverage)
- [ ] `tox` passes all environments
- [ ] UAT scripts executable: `python uat/side-by-side.py --help`
- [ ] No import errors in any module
- [ ] Documentation updated and accurate
- [ ] Git history clean (one atomic commit)

## Rollback Plan
If critical issues arise:
1. Revert the migration commit
2. Run `pip install -e .` to reinstall flat layout
3. Verify tests pass
4. Document issues for future attempt

## Timeline
- Planning: 30 minutes (this document)
- Execution: 1-2 hours (careful file movement + validation)
- Validation: 30 minutes (full test suite + manual checks)
- Documentation: 30 minutes (update all references)

## Constitutional Compliance

### Test-First Development ✅
- All existing tests validate behavior without modification
- Tests already use absolute imports from package
- No new functionality being added

### CLI-First, Text I/O Contracts ✅
- No changes to CLI behavior
- Same entry points work after migration

### Behavioral Parity with Sqitch ✅
- No behavior changes
- Purely structural reorganization

### Simplicity-First ✅
- Follows Python packaging best practices
- Reduces long-term complexity and import confusion
- Industry-standard approach

## Post-Migration Tasks
1. Update lockdown plan.md to reflect new structure
2. Verify all spec references to file paths
3. Test on fresh clone in new directory
4. Consider updating .github workflows if any exist

## Notes
- This migration is **MANDATORY** for proper Python packaging
- Should be done atomically in a single commit
- All team members need to run `pip install -e .` after pulling
- Virtual environments should be recreated (`rm -rf .venv && python -m venv .venv`)
