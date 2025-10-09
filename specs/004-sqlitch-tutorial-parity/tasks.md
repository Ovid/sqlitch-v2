# Tasks: SQLite Tutorial Parity

**Input**: Design documents from `/specs/004-sqlitch-tutorial-parity/`
**Prerequisites**: plan.md, research.md, data-model.md, quickstart.md, contracts/README

## Execution Flow (main)
```
1. Validate toolchain from plan.md (Python 3.11, Click CLI, pytest) and ensure dev extras are installed
2. Extend failing status/log tests to lock Sqitch parity before touching implementation
3. Implement status/log command fixes guided by data-model entities (DeploymentStatus, DeploymentEvent)
4. Re-run quickstart regression scenarios that cover status/log (Scenarios 7 & 10) to confirm byte-identical output
5. Refresh supporting docs and helpers for registry path normalization and event formatting
```

## Phase 3.1: Setup
- [X] T001 Verify dev environment by running `pip install -e .[dev]` in project root (touches `pyproject.toml` dependencies)

## Phase 3.2: Tests First (TDD)
- [X] T002 [P] Augment `tests/cli/test_status_unit.py` to assert registry targets render as project-relative URIs and `_load_registry_rows` raises `CommandError` when the SQLite file is missing (locks current failure before implementation)
- [X] T003 [P] Tighten `tests/cli/contracts/test_status_contract.py` expectations for human output and JSON payload (target string, summary header, undeployed list) based on Sqitch transcript
- [X] T004 [P] Expand `tests/cli/contracts/test_log_contract.py` to assert newline spacing and identity lines exactly match Sqitch log output (ensures current failure remains)
- [X] T005 [P] Update `tests/regression/test_tutorial_parity.py` log/status snapshots for Quickstart Scenarios 7 and 10 to capture Sqitch baseline before code changes

## Phase 3.3: Core Implementation
- [ ] T006 Normalize SQLite registry targets in `sqlitch/cli/commands/status.py::_resolve_registry_target` so CLI output keeps the original target string while resolving filesystem paths internally
- [ ] T007 Ensure `sqlitch/cli/commands/status.py::_load_registry_rows` raises `CommandError` on missing databases and hydrates `DeploymentStatus` rows with project-relative URIs
- [ ] T008 Update `sqlitch/cli/commands/status.py::_render_human_output` to emit Sqitch-parity headers, undeployed lists, and ahead/in-sync summaries using the normalized target string
- [ ] T009 Align JSON payload construction in `sqlitch/cli/commands/status.py::_build_json_payload` with contract expectations (target, pending changes, status state)
- [ ] T010 Match Sqitch human output ordering and spacing in `sqlitch/cli/commands/log.py`, reusing `DeploymentEvent` metadata for identity lines

## Phase 3.4: Integration
- [ ] T011 Re-run `tests/regression/test_tutorial_parity.py::test_log_output_matches_sqitch` after implementation to confirm Scenario 7 parity (update snapshots only if byte-perfect)
- [ ] T012 Re-run `tests/regression/test_tutorial_parity.py::test_status_output_matches_sqitch` with environment overrides from Scenario 10 to validate relative target handling

## Phase 3.5: Polish
- [ ] T013 [P] Document status/log normalization changes in `docs/architecture/reports/status-log-parity.md`
- [ ] T014 [P] Add focused unit coverage for `sqlitch/engine/sqlite.py::resolve_sqlite_filesystem_path` ensuring relative resolution mirrors CLI output expectations

## Dependencies
- T002 → T006 → T007 → T008 → T009
- T003 → T008 → T009
- T004 → T010
- T005 → T011 → T012
- T006 blocks T010 (shared target normalization assumptions)
- T011, T012 depend on all core implementation tasks
- T013, T014 start after integration tasks validate parity

## Parallel Execution Example
```
/task start T003
/task start T004
/task start T005
```

## Notes
- Tests in Phase 3.2 must fail before implementing Phase 3.3 changes to satisfy TDD requirements.
- Quickstart scenarios beyond status/log remain covered by existing parity suites; expand as needed once current blockers are resolved.
