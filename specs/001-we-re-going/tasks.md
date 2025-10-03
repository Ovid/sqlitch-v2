# Tasks: SQLitch Python Parity Fork MVP

**Input**: Design documents from `/specs/001-we-re-going/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Phase 3.1: Setup
- [X] T001 Create SQLitch project skeleton (top-level `bin/`, `docs/`, `etc/`, `scripts/`, `sqlitch/`, `tests/`, `xt/`) mirroring Sqitch’s layout without the legacy `t/` root.
- [X] T002 Author `pyproject.toml` with runtime dependencies (Click, Rich, SQLAlchemy Core, sqlite3, `psycopg[binary]`, `PyMySQL`, python-dateutil, tomli, pydantic, docker SDK) and dev tool configurations (black, isort, flake8, pylint, mypy, bandit, pytest, pytest-cov, hypothesis, tox).
- [X] T003 Configure linting and type checking (`.flake8`, `.pylintrc`, `mypy.ini`, black/isort sections in `pyproject.toml`) ensuring zero-warning gates per FR-004.
- [X] T004 Create `pytest.ini` and `tests/__init__.py` enforcing ≥90% coverage, deterministic seed configuration, and Rich output capture.
- [X] T005 Add `tox.ini` matrix (py311 + OS overrides) running lint, type, security, and coverage suites with failure on warnings.
- [X] T006 Define Docker Compose harness in `scripts/docker-compose/compose.yaml` plus helper scripts (`up`, `down`, `wait`) for MySQL 8 and PostgreSQL 15 containers.
- [X] T007 Seed Sqitch parity fixtures under `tests/support/` (plan files, registry snapshots) for regression comparisons.
- [X] T008 Create `.github/workflows/ci.yml` enforcing macOS/Linux/Windows matrices, docker setup, and coverage/quality gates.
- [X] T008a Build `scripts/check-skips.py` (invoked by the tox lint stage/CI) that fails when skip markers remain on tests whose implementation tasks are in progress, ensuring the skip-removal gate is automated.
- [X] T008b Update `.github/pull_request_template.md` to include a mandatory checkbox confirming `scripts/check-skips.py` was run and that relevant skips were removed before starting implementation.

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
*All tests in this phase ship with skip markers and have those skips removed immediately before the corresponding implementation tasks start (FR-012).* 
- [X] T009 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch add` parity in `tests/cli/contracts/test_add_contract.py`.
- [X] T010 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch bundle` parity in `tests/cli/contracts/test_bundle_contract.py`.
- [X] T011 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch checkout` parity in `tests/cli/contracts/test_checkout_contract.py`.
- [X] T012 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch config` parity in `tests/cli/contracts/test_config_contract.py`.
- [X] T013 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch deploy` parity in `tests/cli/contracts/test_deploy_contract.py`.
- [X] T014 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch engine` parity in `tests/cli/contracts/test_engine_contract.py`.
- [X] T015 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch help` parity in `tests/cli/contracts/test_help_contract.py`.
- [X] T016 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch init` parity in `tests/cli/contracts/test_init_contract.py`.
- [X] T017 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch log` parity in `tests/cli/contracts/test_log_contract.py`.
- [X] T018 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch plan` parity in `tests/cli/contracts/test_plan_contract.py`.
- [X] T019 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch rebase` parity in `tests/cli/contracts/test_rebase_contract.py`.
- [X] T020 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch revert` parity in `tests/cli/contracts/test_revert_contract.py`.
- [X] T021 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch rework` parity in `tests/cli/contracts/test_rework_contract.py`.
- [X] T022 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch show` parity in `tests/cli/contracts/test_show_contract.py`.
- [X] T023 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch status` parity in `tests/cli/contracts/test_status_contract.py`.
- [X] T024 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch tag` parity in `tests/cli/contracts/test_tag_contract.py`.
- [X] T025 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch target` parity in `tests/cli/contracts/test_target_contract.py`.
- [X] T026 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch upgrade` parity in `tests/cli/contracts/test_upgrade_contract.py`.
- [X] T027 [P] Add skipped contract test (remove skip immediately before implementation) for `sqlitch verify` parity in `tests/cli/contracts/test_verify_contract.py`.
- [X] T028 [P] Add skipped integration test (remove skip immediately before implementation) covering parity against existing Sqitch projects in `tests/regression/test_sqitch_parity.py`.
- [X] T029 [P] Add skipped integration test (remove skip immediately before implementation) for contributor onboarding workflow (quickstart) in `tests/regression/test_onboarding_workflow.py`.
- [X] T030 [P] Add skipped integration test (remove skip immediately before implementation) for drop-in support of `sqitch.*` artifacts without conflicts in `tests/regression/test_sqitch_dropin.py`.
- [X] T030a [P] Add skipped regression test (remove skip immediately before implementation) enforcing the blocking error when both `sqitch.*` and `sqlitch.*` artifacts are present in `tests/regression/test_sqitch_conflicts.py`.
- [X] T031 [P] Add skipped regression test (remove skip immediately before implementation) for immediate failure on unsupported engines in `tests/regression/test_unsupported_engine.py`.
- [X] T032 [P] Add skipped regression test (remove skip immediately before implementation) for timestamp/timezone parity across engines in `tests/regression/test_timestamp_parity.py`.
- [X] T033 [P] Add skipped regression test (remove skip immediately before implementation) for Docker-unavailable skip behavior in `tests/regression/test_docker_skip.py`.
- [X] T034 [P] Add skipped regression test (remove skip immediately before implementation) for configuration-root override isolation in `tests/regression/test_config_root_override.py`.
- [X] T035 [P] Add skipped regression test (remove skip immediately before implementation) for artifact cleanup guarantees in `tests/regression/test_artifact_cleanup.py`.
- [X] T035a [P] Add skipped tooling test (remove skip immediately before implementation) ensuring Black formatting compliance enforcement in `tests/scripts/test_black_formatting.py`.
- [X] T035b [P] Add skipped tooling test (remove skip immediately before implementation) validating isort import ordering gate in `tests/scripts/test_isort_ordering.py`.
- [X] T035c [P] Add skipped tooling test (remove skip immediately before implementation) covering lint gate aggregation for flake8/pylint in `tests/scripts/test_lint_suite.py`.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
*Before beginning any task in this phase, remove the related skip markers introduced in Phase 3.2, confirm the tests fail, and use that failure as the Red→Green starting point (FR-012).* 
*All public modules/classes/functions touched during implementation MUST be updated (or created) with comprehensive docstrings covering purpose, parameters, returns, side effects, and error modes. Private helpers MAY rely on succinct inline comments instead.*
- [X] T036 Implement plan domain models (Change, Tag, Plan entries) in `sqlitch/plan/model.py`.
- [X] T037 Implement plan parser mirroring Sqitch semantics in `sqlitch/plan/parser.py`.
- [X] T038 Implement plan formatter and checksum utilities in `sqlitch/plan/formatter.py`.
- [X] T039 Implement configuration loader with layered scopes in `sqlitch/config/loader.py`.
- [X] T040 Implement configuration resolver & overrideable root handling in `sqlitch/config/resolver.py`.
- [X] T041 Implement registry state read/write operations in `sqlitch/registry/state.py`.
- [X] T042 Implement registry migrations aligned with Sqitch SQL in `sqlitch/registry/migrations.py`.
- [X] T043 Implement filesystem utilities for drop-in detection and cleanup in `sqlitch/utils/fs.py`.
- [X] T044 Implement timestamp/zone handling helpers in `sqlitch/utils/time.py`.
- [X] T045 Implement engine base interface and connection factory in `sqlitch/engine/base.py`.
- [X] T046 [P] Implement SQLite engine adapter in `sqlitch/engine/sqlite.py`.
- [X] T050 Create CLI command package scaffolding (`sqlitch/cli/commands/__init__.py`) and shared exceptions (focus on SQLite-ready paths first).
- [X] T051 Wire Click group, global options, and command registration in `sqlitch/cli/main.py`, ensuring SQLite workflows operate end-to-end.
- [ ] T052 [P] Implement `sqlitch add` command handler in `sqlitch/cli/commands/add.py` with SQLite parity.
- [ ] T053 [P] Implement `sqlitch bundle` command handler in `sqlitch/cli/commands/bundle.py` with SQLite parity.
- [ ] T054 [P] Implement `sqlitch checkout` command handler in `sqlitch/cli/commands/checkout.py` with SQLite parity.
- [ ] T055 [P] Implement `sqlitch config` command handler in `sqlitch/cli/commands/config.py` with SQLite parity.
- [ ] T056 [P] Implement `sqlitch deploy` command handler in `sqlitch/cli/commands/deploy.py` with SQLite parity.
- [ ] T057 [P] Implement `sqlitch engine` command handler in `sqlitch/cli/commands/engine.py` with SQLite parity.
- [ ] T058 [P] Implement `sqlitch help` command handler in `sqlitch/cli/commands/help.py` with SQLite parity.
- [ ] T059 [P] Implement `sqlitch init` command handler in `sqlitch/cli/commands/init.py` with SQLite parity.
- [ ] T060 [P] Implement `sqlitch log` command handler in `sqlitch/cli/commands/log.py` with SQLite parity.
- [ ] T061 [P] Implement `sqlitch plan` command handler in `sqlitch/cli/commands/plan.py` with SQLite parity.
- [ ] T062 [P] Implement `sqlitch rebase` command handler in `sqlitch/cli/commands/rebase.py` with SQLite parity.
- [ ] T063 [P] Implement `sqlitch revert` command handler in `sqlitch/cli/commands/revert.py` with SQLite parity.
- [ ] T064 [P] Implement `sqlitch rework` command handler in `sqlitch/cli/commands/rework.py` with SQLite parity.
- [ ] T065 [P] Implement `sqlitch show` command handler in `sqlitch/cli/commands/show.py` with SQLite parity.
- [ ] T066 [P] Implement `sqlitch status` command handler in `sqlitch/cli/commands/status.py` with SQLite parity.
- [ ] T067 [P] Implement `sqlitch tag` command handler in `sqlitch/cli/commands/tag.py` with SQLite parity.
- [ ] T068 [P] Implement `sqlitch target` command handler in `sqlitch/cli/commands/target.py` with SQLite parity.
- [ ] T069 [P] Implement `sqlitch upgrade` command handler in `sqlitch/cli/commands/upgrade.py` with SQLite parity.
- [ ] T070 [P] Implement `sqlitch verify` command handler in `sqlitch/cli/commands/verify.py` with SQLite parity.
- [ ] T047 [P] Implement MySQL engine adapter in `sqlitch/engine/mysql.py`.
- [ ] T048 [P] Implement PostgreSQL engine adapter in `sqlitch/engine/postgres.py`.
- [ ] T049 Implement Docker orchestration helpers and health checks in `sqlitch/engine/docker.py`.
- [ ] T071 Implement parity smoke-test CLI (`bin/sqlitch-parity`) that diff-checks SQLitch output against repository-managed Sqitch golden fixtures (generated ahead of time) without invoking Sqitch during test execution.
- [ ] T072 Implement pytest fixtures (`tests/conftest.py`) for Docker lifecycle, config-root isolation, and artifact cleanup.

### Phase 3.3 Manual Verification Gates (Hard Stops)
- [ ] T081 Freeze upstream work after T046–T070, run manual SQLite parity verification (including CLI walkthrough), document results in `docs/reports/sqlite-gate.md`, and raise a PR for merge before starting T047.
- [ ] T082 Branch from merged main, implement T047, then pause to run manual MySQL parity verification, capture results in `docs/reports/mysql-gate.md`, and raise a PR for merge before starting T048.
- [ ] T083 Branch from merged main, implement T048, run manual PostgreSQL parity verification, capture results in `docs/reports/postgres-gate.md`, and merge before moving into integration work.

## Phase 3.4: Integration
- [ ] T073 Integrate engine adapters with registry layer and plan execution pipeline in `sqlitch/engine/__init__.py`.
- [ ] T074 Integrate CLI commands with Docker harness, config loader, and plan/registry modules ensuring deterministic stdout/stderr across platforms.
- [ ] T075 Implement GitHub Actions artifacts (coverage XML, parity diff uploads) and document in `.github/workflows/ci.yml`.
- [ ] T076 Finalize quickstart and docs updates (`quickstart.md`, `docs/ARCHITECTURE.md`, `docs/PARITY.md`) reflecting implementation details and smoke tests.

## Phase 3.5: Polish
- [ ] T077 [P] Add targeted unit tests for utilities (`tests/unit/test_utils_fs.py`, `tests/unit/test_utils_time.py`).
- [ ] T078 [P] Add performance regression test ensuring CLI non-deploy commands complete <200ms in `tests/perf/test_cli_latency.py`.
- [ ] T079 [P] Update `README.md` and `Changes` with release notes and coverage badge.
- [ ] T080 [P] Run final tox + coverage, ensure ≥90%, zero warnings, and capture parity report for release checklist.

## Phase 3.6: Code Quality Refinement (Post-Review)
*Based on comprehensive code review (REPORT.md, 2025-10-03), address identified best practices before scaling to full command implementation.*
- [ ] T084 [P] Standardize all type hints to use modern Python 3.9+ built-ins (`dict`, `list`, `tuple`, `type`) instead of typing module equivalents across all files in `sqlitch/` (addresses REPORT.md Issue 1.1, FR-014).
- [ ] T085 [P] Remove all `Optional` imports and replace with `X | None` union syntax throughout codebase (addresses REPORT.md Issue 1.2, FR-014).
- [ ] T086 [P] Add `abc.ABC` inheritance and `@abstractmethod` decorators to `Engine` base class in `sqlitch/engine/base.py` (addresses REPORT.md Issue 2.4, FR-017).
- [ ] T087 [P] Add `__all__` exports to public modules missing them: `sqlitch/registry/state.py`, `sqlitch/plan/model.py`, `sqlitch/config/loader.py` (addresses REPORT.md Issue 3.3, FR-015).
- [X] T088 Document registry lifecycle for `ENGINE_REGISTRY` and `_COMMAND_REGISTRY`, including initialization phases and test cleanup patterns (addresses REPORT.md Issue 2.1, FR-018).
- [ ] T089 Refactor `ConfigConflictError` to extend `RuntimeError` instead of `ValueError` for semantic consistency in `sqlitch/config/loader.py` (addresses REPORT.md Issue 2.3, FR-016).
- [X] T090 Extract complex validation from `Change.__post_init__` into testable factory method or validator class in `sqlitch/plan/model.py` (addresses REPORT.md Issue 2.5, FR-019).
- [ ] T091 [P] Fix PEP 8 import grouping (stdlib, third-party, local with blank lines) in `sqlitch/cli/commands/__init__.py` and any other files flagged by review (addresses REPORT.md Issue 1.7).
- [ ] T092 Review and standardize error messages to consistently include field/context information across all validation errors (addresses REPORT.md Issue 3.2).

## Dependencies
- Phase 3.2 tests must complete (and fail) before starting any Phase 3.3 implementation task.
- Tooling coverage tasks T035a–T035c must be operational before expanding automation around lint/format enforcement in Phase 3.3.
- T045 precedes downstream engine and CLI work.
- Complete T046 followed by T050–T070 before attempting T081.
- Engine adapters beyond SQLite must execute in strict sequence: T047 → T082 → T048 → T083, each on a fresh branch after the prior gate merges.
- T081 must complete (merged) before starting T047; T082 must complete (merged) before starting T048; T083 must complete (merged) before any integration work (Phase 3.4).
- Any PR exiting Phase 3.3 MUST include docstrings for all newly- or publicly-exposed symbols; reviewers should block merges otherwise.
- T051 must complete before command handler tasks T052–T070.
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
