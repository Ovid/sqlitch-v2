# Tasks: SQLitch Python Parity Fork MVP

**Input**: Design documents from `/specs/002-sqlite/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Phase 3.1: Setup
- [ ] T001 Create failing-change fixture and SQLite registry helper in `tests/support/sqlite_fixtures.py` to exercise transaction rollback and `sqitch.db` path assertions used by upcoming regression tests.

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
*All new tests MUST be committed in a failing state before implementation work begins.*
- [ ] T002 [P] Add regression test `tests/regression/test_sqlite_deploy_atomicity.py` asserting deploy+registry mutations roll back together when a scripted SQL error occurs.
- [ ] T003 [P] Add regression test `tests/regression/test_sqlite_registry_attach.py` verifying deploy attaches `sqitch.db` under alias `sqitch` and leaves the workspace database untouched.
- [ ] T004 [P] Add engine stub test `tests/engine/test_stub_adapters.py` confirming MySQL/PostgreSQL adapters register with `ENGINE_REGISTRY` and raise `NotImplementedError` with parity messaging.
- [ ] T005 [P] Add suite-behavior test `tests/regression/test_engine_suite_skips.py` ensuring full pytest runs emit expected warnings for skipped MySQL/PostgreSQL suites while keeping SQLite coverage intact.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T006 Update `sqlitch/cli/commands/deploy.py` to execute change scripts and registry writes inside a single SQLite transaction using the attached registry connection.
- [ ] T007 Update `sqlitch/engine/sqlite.py` to resolve a canonical adjacent `sqitch.db`, attach it under the `sqitch` alias, and expose helpers consumed by the deploy command.
- [ ] T008 Extend `sqlitch/config/resolver.py` and related providers to compute the registry SQLite path (including in-memory targets) and surface it through `EngineTarget.registry_uri`.
- [ ] T009 Adjust registry migrations/tests in `sqlitch/registry/migrations.py` and `tests/engine/test_sqlite_registry.py` to accommodate attached `sqitch.db` connections and verify schema setup.
- [ ] T010 Implement stub adapters `sqlitch/engine/mysql.py` and `sqlitch/engine/postgres.py` that register with `ENGINE_REGISTRY`, raise `NotImplementedError`, and document placeholders per FR-001a.
- [ ] T011 Wire stub adapters into `sqlitch/engine/__init__.py` (and any CLI surface such as `sqlitch/cli/commands/engine.py`) so unsupported engine selection yields deterministic parity messaging.
- [ ] T012 Update `sqlitch/cli/commands/deploy.py` and `sqlitch/utils/logging.py` to ensure structured logs reflect registry path, transaction scope, and stub-engine warnings without leaking credentials.

## Phase 3.4: Integration
- [ ] T013 Refresh parity fixtures in `tests/support/golden/` (SQLite deploy/log outputs) to match the new registry path and transaction logging.
- [ ] T014 Update documentation (`docs/architecture/registry-lifecycle.md`, `specs/002-sqlite/quickstart.md`) with the attach-based registry flow and stub adapter behavior.
- [ ] T015 Run full validation (`pytest` + `tox -e lint`) capturing evidence that skipped engine suites emit warnings while SQLite coverage remains ≥90% (store output under `docs/reports/sqlite-gate.md`).
- Complete T046 followed by T050–T070 before attempting T081.
- Engine adapters beyond SQLite must execute in strict sequence: T047 → T082 → T048 → T083, each on a fresh branch after the prior gate merges.
- T081 must complete (merged) before starting T047; T082 must complete (merged) before starting T048; T083 must complete (merged) before any integration work (Phase 3.4).
- Any PR exiting Phase 3.3 MUST include docstrings for all newly- or publicly-exposed symbols; reviewers should block merges otherwise.
- T051 must complete before command handler tasks T052–T070.
- T035d and T035e must be unskipped before starting observability implementation tasks T093–T095.
- T035f and T035g must be unskipped before beginning credential handling work in T096–T097.
- T093 completes before T095 updates command harnesses; T094 provides the structured logging sink consumed by T095.
- T008a and T008b must finish before Phase 3.3 work begins to ensure the skip-removal gate is active in tooling and reviews.
- Integration tasks T073–T074 depend on completion of all relevant command and engine tasks.
- Polish tasks (T077–T080) run only after integration is solid.
- Code Quality Refinement tasks (T084–T092) SHOULD be completed before starting T052–T070 (command handlers) to ensure consistent patterns across new code. T084–T087 and T091 may be executed in parallel as they touch distinct files.

## Parallel Execution Example
```
# After T046–T070 complete and T081 merges, begin the MySQL adapter on a fresh branch:
Task: "T047 Implement MySQL engine adapter in sqlitch/engine/mysql.py" (agent-engine)
# After T082 merges, begin the PostgreSQL adapter:
Task: "T048 Implement PostgreSQL engine adapter in sqlitch/engine/postgres.py" (agent-engine)
# Code quality tasks T084-T087, T091 can run in parallel:
Task: "T084 Standardize type hints" (agent-quality)
Task: "T085 Replace Optional with union syntax" (agent-quality)
Task: "T086 Add ABC to Engine" (agent-quality)
Task: "T087 Add __all__ exports" (agent-quality)
Task: "T091 Fix import grouping" (agent-quality)
```

## Notes
- [P] tasks touch distinct files and may be assigned concurrently once prerequisites finish.
- Ensure every test created in Phase 3.2 is executed and failing prior to corresponding implementation work.
- All scripts and tests must clean up Docker containers, temporary directories, and generated plan files to satisfy FR-010.
- Code Quality Refinement phase addresses systematic issues identified in comprehensive review to maintain constitutional compliance and Python best practices.
