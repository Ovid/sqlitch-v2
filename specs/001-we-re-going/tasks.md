# Tasks: SQLitch Python Parity Fork MVP

**Input**: Design documents from `/specs/001-we-re-going/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Phase 3.1: Setup
- [ ] T001 Create SQLitch project skeleton (`sqlitch/` root, `bin/`, `lib/`, `etc/`, `tests/`, `xt/`, `scripts/`) with `tests/` as a top-level sibling to `sqlitch/`, mirroring Sqitch’s layout without the legacy `t/` root.
- [ ] T002 Author `sqlitch/pyproject.toml` with runtime dependencies (Click, Rich, SQLAlchemy Core, sqlite3, `psycopg[binary]`, `mysqlclient`, python-dateutil, tomli, pydantic, docker SDK) and dev tool configurations (black, isort, flake8, pylint, mypy, bandit, pytest, pytest-cov, hypothesis, tox).
- [ ] T003 Configure linting and type checking (`.flake8`, `.pylintrc`, `mypy.ini`, black/isort sections in `pyproject.toml`) ensuring zero-warning gates per FR-004.
- [ ] T004 Create `pytest.ini` and `tests/__init__.py` enforcing ≥90% coverage, deterministic seed configuration, and Rich output capture.
- [ ] T005 Add `tox.ini` matrix (py311 + OS overrides) running lint, type, security, and coverage suites with failure on warnings.
- [ ] T006 Define Docker Compose harness in `sqlitch/scripts/docker-compose/compose.yaml` plus helper scripts (`up`, `down`, `wait`) for MySQL 8 and PostgreSQL 15 containers.
- [ ] T007 Seed Sqitch parity fixtures under `tests/support/` (plan files, registry snapshots) for regression comparisons.
- [ ] T008 Create `.github/workflows/ci.yml` enforcing macOS/Linux/Windows matrices, docker setup, and coverage/quality gates.

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
- [ ] T009 [P] Add failing contract test for `sqlitch add` parity in `tests/cli/contracts/test_add_contract.py`.
- [ ] T010 [P] Add failing contract test for `sqlitch bundle` parity in `tests/cli/contracts/test_bundle_contract.py`.
- [ ] T011 [P] Add failing contract test for `sqlitch checkout` parity in `tests/cli/contracts/test_checkout_contract.py`.
- [ ] T012 [P] Add failing contract test for `sqlitch config` parity in `tests/cli/contracts/test_config_contract.py`.
- [ ] T013 [P] Add failing contract test for `sqlitch deploy` parity in `tests/cli/contracts/test_deploy_contract.py`.
- [ ] T014 [P] Add failing contract test for `sqlitch engine` parity in `tests/cli/contracts/test_engine_contract.py`.
- [ ] T015 [P] Add failing contract test for `sqlitch help` parity in `tests/cli/contracts/test_help_contract.py`.
- [ ] T016 [P] Add failing contract test for `sqlitch init` parity in `tests/cli/contracts/test_init_contract.py`.
- [ ] T017 [P] Add failing contract test for `sqlitch log` parity in `tests/cli/contracts/test_log_contract.py`.
- [ ] T018 [P] Add failing contract test for `sqlitch plan` parity in `tests/cli/contracts/test_plan_contract.py`.
- [ ] T019 [P] Add failing contract test for `sqlitch rebase` parity in `tests/cli/contracts/test_rebase_contract.py`.
- [ ] T020 [P] Add failing contract test for `sqlitch revert` parity in `tests/cli/contracts/test_revert_contract.py`.
- [ ] T021 [P] Add failing contract test for `sqlitch rework` parity in `tests/cli/contracts/test_rework_contract.py`.
- [ ] T022 [P] Add failing contract test for `sqlitch show` parity in `tests/cli/contracts/test_show_contract.py`.
- [ ] T023 [P] Add failing contract test for `sqlitch status` parity in `tests/cli/contracts/test_status_contract.py`.
- [ ] T024 [P] Add failing contract test for `sqlitch tag` parity in `tests/cli/contracts/test_tag_contract.py`.
- [ ] T025 [P] Add failing contract test for `sqlitch target` parity in `tests/cli/contracts/test_target_contract.py`.
- [ ] T026 [P] Add failing contract test for `sqlitch upgrade` parity in `tests/cli/contracts/test_upgrade_contract.py`.
- [ ] T027 [P] Add failing contract test for `sqlitch verify` parity in `tests/cli/contracts/test_verify_contract.py`.
- [ ] T028 [P] Integration test parity against existing Sqitch projects in `tests/regression/test_sqitch_parity.py`.
- [ ] T029 [P] Integration test contributor onboarding workflow (quickstart) in `tests/regression/test_onboarding_workflow.py`.
- [ ] T030 [P] Integration test drop-in support for `sqitch.*` artifacts without conflicts in `tests/regression/test_sqitch_dropin.py`.
- [ ] T030a [P] Regression test enforcing the blocking error when both `sqitch.*` and `sqlitch.*` artifacts are present in `tests/regression/test_sqitch_conflicts.py`.
- [ ] T031 [P] Regression test immediate failure for unsupported engines in `tests/regression/test_unsupported_engine.py`.
- [ ] T032 [P] Regression test timestamp/timezone parity across engines in `tests/regression/test_timestamp_parity.py`.
- [ ] T033 [P] Regression test Docker-unavailable skip behavior in `tests/regression/test_docker_skip.py`.
- [ ] T034 [P] Regression test configuration-root override isolation in `tests/regression/test_config_root_override.py`.
- [ ] T035 [P] Regression test artifact cleanup guarantees in `tests/regression/test_artifact_cleanup.py`.

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T036 Implement plan domain models (Change, Tag, Plan entries) in `sqlitch/lib/sqlitch/plan/model.py`.
- [ ] T037 Implement plan parser mirroring Sqitch semantics in `sqlitch/lib/sqlitch/plan/parser.py`.
- [ ] T038 Implement plan formatter and checksum utilities in `sqlitch/lib/sqlitch/plan/formatter.py`.
- [ ] T039 Implement configuration loader with layered scopes in `sqlitch/lib/sqlitch/config/loader.py`.
- [ ] T040 Implement configuration resolver & overrideable root handling in `sqlitch/lib/sqlitch/config/resolver.py`.
- [ ] T041 Implement registry state read/write operations in `sqlitch/lib/sqlitch/registry/state.py`.
- [ ] T042 Implement registry migrations aligned with Sqitch SQL in `sqlitch/lib/sqlitch/registry/migrations.py`.
- [ ] T043 Implement filesystem utilities for drop-in detection and cleanup in `sqlitch/lib/sqlitch/utils/fs.py`.
- [ ] T044 Implement timestamp/zone handling helpers in `sqlitch/lib/sqlitch/utils/time.py`.
- [ ] T045 Implement engine base interface and connection factory in `sqlitch/lib/sqlitch/engine/base.py`.
- [ ] T046 [P] Implement SQLite engine adapter in `sqlitch/lib/sqlitch/engine/sqlite.py`.
- [ ] T047 [P] Implement MySQL engine adapter in `sqlitch/lib/sqlitch/engine/mysql.py`.
- [ ] T048 [P] Implement PostgreSQL engine adapter in `sqlitch/lib/sqlitch/engine/postgres.py`.
- [ ] T049 Implement Docker orchestration helpers and health checks in `sqlitch/lib/sqlitch/engine/docker.py`.
- [ ] T050 Create CLI command package scaffolding (`sqlitch/lib/sqlitch/cli/commands/__init__.py`) and shared exceptions.
- [ ] T051 Wire Click group, global options, and command registration in `sqlitch/lib/sqlitch/cli/main.py`.
- [ ] T052 [P] Implement `sqlitch add` command handler in `sqlitch/lib/sqlitch/cli/commands/add.py`.
- [ ] T053 [P] Implement `sqlitch bundle` command handler in `sqlitch/lib/sqlitch/cli/commands/bundle.py`.
- [ ] T054 [P] Implement `sqlitch checkout` command handler in `sqlitch/lib/sqlitch/cli/commands/checkout.py`.
- [ ] T055 [P] Implement `sqlitch config` command handler in `sqlitch/lib/sqlitch/cli/commands/config.py`.
- [ ] T056 [P] Implement `sqlitch deploy` command handler in `sqlitch/lib/sqlitch/cli/commands/deploy.py`.
- [ ] T057 [P] Implement `sqlitch engine` command handler in `sqlitch/lib/sqlitch/cli/commands/engine.py`.
- [ ] T058 [P] Implement `sqlitch help` command handler in `sqlitch/lib/sqlitch/cli/commands/help.py`.
- [ ] T059 [P] Implement `sqlitch init` command handler in `sqlitch/lib/sqlitch/cli/commands/init.py`.
- [ ] T060 [P] Implement `sqlitch log` command handler in `sqlitch/lib/sqlitch/cli/commands/log.py`.
- [ ] T061 [P] Implement `sqlitch plan` command handler in `sqlitch/lib/sqlitch/cli/commands/plan.py`.
- [ ] T062 [P] Implement `sqlitch rebase` command handler in `sqlitch/lib/sqlitch/cli/commands/rebase.py`.
- [ ] T063 [P] Implement `sqlitch revert` command handler in `sqlitch/lib/sqlitch/cli/commands/revert.py`.
- [ ] T064 [P] Implement `sqlitch rework` command handler in `sqlitch/lib/sqlitch/cli/commands/rework.py`.
- [ ] T065 [P] Implement `sqlitch show` command handler in `sqlitch/lib/sqlitch/cli/commands/show.py`.
- [ ] T066 [P] Implement `sqlitch status` command handler in `sqlitch/lib/sqlitch/cli/commands/status.py`.
- [ ] T067 [P] Implement `sqlitch tag` command handler in `sqlitch/lib/sqlitch/cli/commands/tag.py`.
- [ ] T068 [P] Implement `sqlitch target` command handler in `sqlitch/lib/sqlitch/cli/commands/target.py`.
- [ ] T069 [P] Implement `sqlitch upgrade` command handler in `sqlitch/lib/sqlitch/cli/commands/upgrade.py`.
- [ ] T070 [P] Implement `sqlitch verify` command handler in `sqlitch/lib/sqlitch/cli/commands/verify.py`.
- [ ] T071 Implement parity smoke-test CLI (`sqlitch/bin/sqlitch-parity`) that diff-checks SQLitch output against repository-managed Sqitch golden fixtures (generated ahead of time) without invoking Sqitch during test execution.
- [ ] T072 Implement pytest fixtures (`tests/conftest.py`) for Docker lifecycle, config-root isolation, and artifact cleanup.

### Phase 3.3 Manual Verification Gates (Hard Stops)
- [ ] T081 Freeze upstream work after T046, run manual SQLite parity verification, document results in `docs/reports/sqlite-gate.md`, and raise a PR for merge before starting T047.
- [ ] T082 Branch from merged main, implement T047, then pause to run manual MySQL parity verification, capture results in `docs/reports/mysql-gate.md`, and raise a PR for merge before starting T048.
- [ ] T083 Branch from merged main, implement T048, run manual PostgreSQL parity verification, capture results in `docs/reports/postgres-gate.md`, and merge before moving into integration work.

## Phase 3.4: Integration
- [ ] T073 Integrate engine adapters with registry layer and plan execution pipeline in `sqlitch/lib/sqlitch/engine/__init__.py`.
- [ ] T074 Integrate CLI commands with Docker harness, config loader, and plan/registry modules ensuring deterministic stdout/stderr across platforms.
- [ ] T075 Implement GitHub Actions artifacts (coverage XML, parity diff uploads) and document in `sqlitch/.github/workflows/ci.yml`.
- [ ] T076 Finalize quickstart and docs updates (`sqlitch/quickstart.md`, `sqlitch/docs/ARCHITECTURE.md`, `sqlitch/docs/PARITY.md`) reflecting implementation details and smoke tests.

## Phase 3.5: Polish
- [ ] T077 [P] Add targeted unit tests for utilities (`tests/unit/test_utils_fs.py`, `tests/unit/test_utils_time.py`).
- [ ] T078 [P] Add performance regression test ensuring CLI non-deploy commands complete <200ms in `tests/perf/test_cli_latency.py`.
- [ ] T079 [P] Update `sqlitch/README.md` and `Changes` with release notes and coverage badge.
- [ ] T080 [P] Run final tox + coverage, ensure ≥90%, zero warnings, and capture parity report for release checklist.

## Dependencies
- Phase 3.2 tests must complete (and fail) before starting any Phase 3.3 implementation task.
- T045 precedes engine-specific tasks T046–T048.
- Engine adapters must execute in strict sequence: T046 → T081 → T047 → T082 → T048 → T083.
- T081 must complete (merged) before starting T047; T082 must complete (merged) before starting T048; T083 must complete (merged) before any integration work (Phase 3.4).
- T051 must complete before command handler tasks T052–T070.
- Integration tasks T073–T074 depend on completion of all relevant command and engine tasks.
- Polish tasks (T077–T080) run only after integration is solid.

## Parallel Execution Example
```
# After T046 completes and T081 merges, begin the MySQL adapter on a fresh branch:
Task: "T047 Implement MySQL engine adapter in sqlitch/lib/sqlitch/engine/mysql.py" (agent-engine)
# After T082 merges, begin the PostgreSQL adapter:
Task: "T048 Implement PostgreSQL engine adapter in sqlitch/lib/sqlitch/engine/postgres.py" (agent-engine)
```

## Notes
- [P] tasks touch distinct files and may be assigned concurrently once prerequisites finish.
- Ensure every test created in Phase 3.2 is executed and failing prior to corresponding implementation work.
- All scripts and tests must clean up Docker containers, temporary directories, and generated plan files to satisfy FR-010.
