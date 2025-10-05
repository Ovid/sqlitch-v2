# Tasks: SQLitch Python Parity Fork MVP

**Input**: Design documents from `/specs/002-sqlite/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Phase 3.1: Setup
- [X] T001 Create failing-change fixture and SQLite registry helper in `tests/support/sqlite_fixtures.py` to exercise transaction rollback and `sqitch.db` path assertions used by upcoming regression tests.

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
*All new tests MUST be committed in a failing state before implementation work begins.*
- [X] T002 [P] Add regression test `tests/regression/test_sqlite_deploy_atomicity.py` asserting deploy+registry mutations roll back together when a scripted SQL error occurs.
- [X] T003 [P] Add regression test `tests/regression/test_sqlite_registry_attach.py` verifying deploy attaches `sqitch.db` under alias `sqitch` and leaves the workspace database untouched.
- [X] T004 [P] Add engine stub test `tests/engine/test_stub_adapters.py` confirming MySQL/PostgreSQL adapters register with `ENGINE_REGISTRY` and raise `NotImplementedError` with parity messaging.
- [X] T005 [P] Add suite-behavior test `tests/regression/test_engine_suite_skips.py` ensuring full pytest runs emit expected warnings for skipped MySQL/PostgreSQL suites while keeping SQLite coverage intact.
- [X] T016 [P] Add regression tests `tests/regression/test_credentials_precedence.py` and `tests/regression/test_credentials_redaction.py` covering credential source ordering and structured-log redaction for SQLite targets and stub adapters.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [X] T006 Update `sqlitch/cli/commands/deploy.py` to execute change scripts and registry writes inside a single SQLite transaction using the attached registry connection.
- [X] T007 Update `sqlitch/engine/sqlite.py` to resolve a canonical adjacent `sqitch.db`, attach it under the `sqitch` alias, and expose helpers consumed by the deploy command.
- [X] T008 Extend `sqlitch/config/resolver.py` and related providers to compute the registry SQLite path (including in-memory targets) and surface it through `EngineTarget.registry_uri`.
- [X] T009 Adjust registry migrations/tests in `sqlitch/registry/migrations.py` and `tests/engine/test_sqlite_registry.py` to accommodate attached `sqitch.db` connections and verify schema setup.
- [X] T010 Implement stub adapters `sqlitch/engine/mysql.py` and `sqlitch/engine/postgres.py` that register with `ENGINE_REGISTRY`, raise `NotImplementedError`, and document placeholders per FR-001a.
- [X] T011 Wire stub adapters into `sqlitch/engine/__init__.py` (and any CLI surface such as `sqlitch/cli/commands/engine.py`) so unsupported engine selection yields deterministic parity messaging.
- [X] T012 Update `sqlitch/cli/commands/deploy.py` and `sqlitch/utils/logging.py` to ensure structured logs reflect registry path, transaction scope, and stub-engine warnings without leaking credentials.
- [X] T017 Implement credential precedence resolution and structured logging redaction safeguards in `sqlitch/config/resolver.py`, `sqlitch/utils/logging.py`, and `sqlitch/cli/options.py` to satisfy NFR-002.

## Phase 3.4: Integration
- [ ] T013 Refresh parity fixtures in `tests/support/golden/` (SQLite deploy/log outputs) to match the new registry path and transaction logging.
- [ ] T014 Update documentation (`docs/architecture/registry-lifecycle.md`, `specs/002-sqlite/quickstart.md`) with the attach-based registry flow, stub adapter behavior, and credential precedence/redaction guidance.
- [ ] T015 Run full validation (`pytest` + `tox -e lint`) capturing evidence that skipped engine suites emit warnings while SQLite coverage remains ≥90% (store output under `docs/reports/sqlite-gate.md`).

## Dependencies
- T001 prepares shared fixtures before any regression tests (T002–T005, T016).
- T002–T005 must fail before implementation begins on T006–T012.
- T016 must fail before starting credential implementation work in T017.
- T006 depends on T002; T007–T009 depend on T003; T010–T011 depend on T004.
- T012 depends on the logging assertions added in T002–T005 to validate structured output.
- T013 requires completion of T006–T012 (and T017 for logging parity) before fixture refresh.
- T014 documents outcomes from T006–T013 and the credential updates from T017.
- T015 runs only after implementation tasks (T006–T012, T017) and integration tasks (T013–T014) are complete.

## Parallel Execution Example
```
# After T001 completes, draft failing regression tests in parallel:
Task: "T002 Add regression test tests/regression/test_sqlite_deploy_atomicity.py"
Task: "T003 Add regression test tests/regression/test_sqlite_registry_attach.py"
Task: "T004 Add engine stub test tests/engine/test_stub_adapters.py"
Task: "T005 Add suite-behavior test tests/regression/test_engine_suite_skips.py"
Task: "T016 Add regression tests for credential precedence and redaction"

# Once T006–T012 and T017 land, proceed with integration work together:
Task: "T013 Refresh parity fixtures"
Task: "T014 Update documentation with registry and credential guidance"
Task: "T015 Run full validation and capture reports"
```

## Notes
- [P] tasks touch distinct files and may be assigned concurrently once prerequisites finish.
- Ensure every test created in Phase 3.2 is executed and failing prior to corresponding implementation work.
- All scripts and tests must clean up Docker containers, temporary directories, and generated plan files to satisfy FR-010.
- Credential regression tests in T016 should validate CLI flag → environment → config precedence and ensure logs emitted by the CLI and structured logging sink redact secret values before implementation begins in T017.
- Code Quality Refinement expectations from the constitution remain in force; enforce docstrings, typing, and structured logging standards during reviews.
