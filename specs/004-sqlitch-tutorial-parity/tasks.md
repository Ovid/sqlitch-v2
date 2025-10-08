# Tasks: SQLite Tutorial Parity

**Input**: Design documents from `/specs/004-sqlitch-tutorial-parity/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅, contracts/README ✅

## Execution Flow (main)
```
1. Read plan.md (2025-10-08) for clarified requirements on config hierarchy, environment precedence, and deploy/revert semantics.
2. Cross-reference research.md for technical decisions (config overrides, core.uri parity, environment matrix) and data-model.md for identity/registry models.
3. Use quickstart Scenario 10 to drive integration validation after core fixes.
4. Follow Test-First workflow: author failing tests before touching implementation.
5. Preserve Sqitch parity at every step; update docs/reports only after code and tests stabilize.
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Provide absolute file paths.
- Tests precede implementation for each behavior (TDD).

## Phase 3.1 – Environment & Fixtures Prep
- [ ] **T001** Refresh tutorial fixtures to include config/env overrides in `tests/support/tutorial_parity/`.
  - Output: sanitized fixture tree with `sqitch.conf` lacking `%core.uri` and env override metadata.

## Phase 3.2 – Tests First
- [ ] **T002** Add resolver scope precedence tests in `tests/config/test_resolver.py`.
  - Cover FR-001a: system → user → local ordering and duplicate-file rejection.
  - Depends on: T001
- [ ] **T003** Add loader grammar coverage for FR-023 in `tests/config/test_loader.py`.
  - Ensure parser accepts uppercase section headers and rejects stray `%core.uri` entries.
  - Depends on: T001
- [ ] **T004** Extend config CLI functional tests in `tests/cli/commands/test_config_functional.py` to enforce FR-001a interactions and absence of `core.uri` writes.
  - Depends on: T002, T003
- [ ] **T005** Add init command regression in `tests/cli/commands/test_init_functional.py` confirming new project configs omit `%core.uri` and respect engine default notes.
  - Depends on: T002
- [ ] **T006** Create environment precedence matrix tests in `tests/cli/commands/test_deploy_functional.py` validating SQLITCH_* → SQITCH_* → GIT_* chain (FR-005a).
  - Depends on: T001
- [ ] **T007** Add deploy failure event tests in `tests/cli/commands/test_deploy_functional.py` asserting `events` table captures `deploy_fail` rows with identity + note (FR-010a).
  - Depends on: T006
- [ ] **T008** Add log formatting tests in `tests/cli/commands/test_log_functional.py` for failure events and ensure output matches Sqitch parity (FR-010a).
  - Depends on: T007
- [ ] **T009** Extend status command tests in `tests/cli/commands/test_status_functional.py` to surface last failure metadata when deployment pending (FR-010a).
  - Depends on: T007
- [ ] **T010** Add end-to-end Scenario 10 coverage in `tests/integration/test_quickstart_sqlite.py` executing config/env overrides + failure handling.
  - Depends on: T002, T006, T007

## Phase 3.3 – Implementation
- [ ] **T011** Update resolver merge logic in `sqlitch/config/resolver.py` to enforce scope precedence and ignore duplicate files.
  - Depends on: T002
- [ ] **T012** Adjust loader grammar in `sqlitch/config/loader.py` per FR-023; normalize header casing and strip `%core.uri` references.
  - Depends on: T003
- [ ] **T013** Modify config CLI write paths in `sqlitch/cli/commands/config.py` to block `core.uri` entries and respect new precedence rules.
  - Depends on: T004, T011, T012
- [ ] **T014** Update init scaffolding in `sqlitch/cli/commands/init.py` and templates under `sqlitch/templates/` to omit `%core.uri` while preserving Sqitch note layout.
  - Depends on: T005, T012
- [ ] **T015** Enhance deploy workflow in `sqlitch/cli/commands/deploy.py` + `sqlitch/engine/sqlite.py` to record `deploy_fail` events atomically with identity data.
  - Depends on: T007
- [ ] **T016** Update log rendering in `sqlitch/cli/commands/log.py` to display failure markers, and extend `sqlitch/cli/commands/_formatters.py` if needed.
  - Depends on: T008, T015
- [ ] **T017** Adjust status output in `sqlitch/cli/commands/status.py` to highlight last failure per FR-010a, reusing new event data.
  - Depends on: T009, T015
- [ ] **T018** Synchronize identity helpers in `sqlitch/utils/identity.py` to expose env precedence API for deploy/revert reuse.
  - Depends on: T006, T015

## Phase 3.4 – Integration & Polish
- [ ] **T019** Run full quickstart Scenario 10 via `tests/integration/test_quickstart_sqlite.py` ensuring parity with Sqitch outputs.
  - Depends on: T010–T018
- [ ] **T020** Update documentation in `docs/reports/sqlite-tutorial-parity.md` and `REPORT.md` with new behavior summaries and troubleshooting tips.
  - Depends on: T019
- [ ] **T021** Refresh release notes in `REPORT-TASKS.md` and ensure coverage thresholds maintained (run pytest + coverage gate).
  - Depends on: T019, T020
