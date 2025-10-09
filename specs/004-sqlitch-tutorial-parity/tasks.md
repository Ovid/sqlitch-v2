# Tasks: SQLite Tutorial Parity

**Input**: Design documents from `/specs/004-sqlitch-tutorial-parity/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅, contracts/README ✅

## Execution Flow (main)
```
1. Load plan.md (2025-10-08) to confirm CLI parity goals, constitution gates, and sequencing.
2. Pull identities, registry shape, and helper expectations from research.md and data-model.md.
3. Map each quickstart scenario to integration coverage, with Scenario 10 as final regression.
4. Derive failing tests first for every new or changed behavior before touching implementation.
5. Preserve Sqitch parity, including byte-identical default output and config semantics, then update docs once code and tests are stable.
```

## Format: `[ID] [P?] Description`
- Mark tasks touching disjoint files that have no dependency constraints with **[P]**.
- Provide absolute (or repo-rooted) paths for every artifact.
- Keep tests ahead of implementation per TDD.

## Phase 3.1 – Environment & Fixture Preparation
- [ ] **T001** Refresh tutorial fixtures under `tests/support/tutorial_parity/` to match compact plan format and config/env override cases (no `core.uri`, new `%default_engine`).
- [ ] **T002** Snapshot Sqitch golden outputs for failure/log/status flows in `tests/support/golden/tutorial_parity/` to drive later parity assertions.

## Phase 3.2 – Tests First (must fail before implementation)
- [ ] **T003 [P]** Add scope precedence coverage (FR-001/FR-001a) in `tests/config/test_resolver.py` for system→user→local ordering and duplicate-file rejection.
- [ ] **T004 [P]** Extend config loader grammar tests (FR-002/FR-003/FR-023) in `tests/config/test_loader.py`, covering multiline values, indentation, and `%core.uri` omission.
- [ ] **T005 [P]** Expand config CLI functional tests in `tests/cli/commands/test_config_functional.py` to verify scope writes, silence on set, and environment override redirects.
- [ ] **T006** Add init regression tests in `tests/cli/commands/test_init_functional.py` asserting new projects omit `core.uri` and avoid `engine.<engine>.target` unless `--target` supplied (FR-007a/FR-007b).
- [ ] **T007** Build environment precedence matrix tests in `tests/cli/commands/test_deploy_functional.py` asserting SQLITCH_* → SQITCH_* → git/system fallbacks (FR-004/FR-005/FR-005a).
- [ ] **T008** Author deploy failure registry tests in `tests/cli/commands/test_deploy_functional.py` verifying transactional rollback and `events` table `fail` rows (FR-010a).
- [ ] **T008a** Extend deploy failure parity tests in `tests/cli/commands/test_deploy_functional.py` to assert registry tables remain unchanged after a simulated failure (FR-010a, data-model §§4.6–4.7).
- [ ] **T009 [P]** Add log failure rendering assertions in `tests/cli/commands/test_log_functional.py` comparing output to Sqitch golden fixtures (FR-010a, NFR-004).
- [ ] **T010 [P]** Extend status command tests in `tests/cli/commands/test_status_functional.py` to surface last-failure metadata and pending indicators (FR-010a).
- [ ] **T011 [P]** Create verify parity suite in `tests/cli/commands/test_verify_functional.py` covering success, single failure, multi-failure, and out-of-order cases (FR-011/FR-011a).
- [ ] **T012 [P]** Create revert parity suite in `tests/cli/commands/test_revert_functional.py` for prompts, `--yes`, dependency guards, and error messaging (FR-012/FR-012a).
- [ ] **T013 [P]** Add log/error message parity tests in `tests/cli/commands/test_errors_functional.py` to cover representative failure paths (NFR-005).
- [ ] **T014 [P]** Capture compact plan formatter regression in `tests/plan/test_formatter.py` with golden comparisons (FR-019/FR-019a).
- [ ] **T015 [P]** Extend plan validation coverage in `tests/plan/test_validation.py` for duplicates, missing dependencies, and conflict cycles (FR-019).
- [ ] **T016 [P]** Add plan parser round-trip tests in `tests/plan/test_parser.py` ensuring compact format parsing matches Sqitch grammar (FR-019/FR-019a).
- [ ] **T017 [P]** Author target URI normalization tests in `tests/cli/commands/test_target_functional.py` for relative paths, `:memory:`, registry siblings, and env overrides (FR-021/FR-022).
- [ ] **T018 [P]** Add engine alias resolution tests in `tests/cli/commands/test_engine_functional.py` validating alias success/failure cases (FR-022).
- [ ] **T019 [P]** Introduce tag parity tests in `tests/cli/commands/test_tag_functional.py` for quiet mode, notes, and listing outputs (FR-015).
- [ ] **T020 [P]** Extend rework parity tests in `tests/cli/commands/test_rework_functional.py` for @tag scripts, dependency preservation, and quiet mode (FR-016).
- [ ] **T021 [P]** Add add-command compact entry tests in `tests/cli/commands/test_add_functional.py` verifying dependency serialization and quiet output (FR-009/FR-019a).
- [ ] **T022 [P]** Guard template parity in `tests/templates/test_sqlite_templates.py` via checksum comparison (FR-020).
- [ ] **T023 [P]** Add registry schema parity guard in `tests/registry/test_schema_parity.py` comparing DDL with Sqitch baseline (FR-017/FR-018).
- [ ] **T024 [P]** Extend deployment identity helper tests in `tests/utils/test_identity.py` to capture new precedence APIs (FR-004/FR-005).
- [ ] **T025** Add integration Scenario 10 regression in `tests/integration/test_quickstart_sqlite.py` covering env overrides, failure handling, and tag/rework flows (Quickstart).

## Phase 3.3 – Core Implementation (only start when corresponding tests are failing)
- [ ] **T026** Update scope resolution logic in `sqlitch/config/resolver.py` to honor environment overrides, precedence, and duplicate suppression (FR-001/FR-001a).
- [ ] **T027** Enhance config loader and writer in `sqlitch/config/loader.py` to preserve formatting, multiline values, and strip `%core.uri` (FR-002/FR-003/FR-023).
- [ ] **T028** Refine config CLI in `sqlitch/cli/commands/config.py` to block `core.uri`, respect scope targeting, and keep silent success (FR-001–FR-003, FR-005a).
- [ ] **T029** Adjust init scaffolding in `sqlitch/cli/commands/init.py` and template helpers to avoid `core.uri` and optional engine targets (FR-007a/FR-007b).
- [ ] **T030** Implement compact plan emission in `sqlitch/plan/formatter.py`, coordinating with parser/validation for deterministic ordering (FR-019/FR-019a).
- [ ] **T031** Update plan write callers (`sqlitch/cli/commands/{add,tag,rework}.py`) to rely on the new formatter and remove verbose fallbacks (FR-009/FR-015/FR-016).
- [ ] **T032** Propagate validation improvements into `sqlitch/plan/validation.py` for duplicates/conflicts aligned with Sqitch errors (FR-019).
- [ ] **T033** Reconcile registry migrations in `sqlitch/registry/migrations.py` with Sqitch DDL, including triggers/indexes (FR-017/FR-018).
- [ ] **T034** Extend identity utilities in `sqlitch/utils/identity.py` to expose shared precedence logic for deploy/verify/revert (FR-004/FR-005).
- [ ] **T035** Harden deploy flow in `sqlitch/cli/commands/deploy.py` to record fail events atomically, reuse identity helper, and align output with Sqitch (FR-010/FR-010a).
- [ ] **T036** Update log rendering in `sqlitch/cli/commands/log.py` to display failure markers and honor new golden outputs (FR-010a, NFR-004).
- [ ] **T037** Enhance status reporting in `sqlitch/cli/commands/status.py` to show last failure/pending blocks per new tests (FR-010a).
- [ ] **T038** Align verify command in `sqlitch/cli/commands/verify.py` with multi-failure aggregation and exit codes (FR-011/FR-011a).
- [ ] **T039** Complete revert parity in `sqlitch/cli/commands/revert.py`, including prompts, dependency safeguards, and messaging (FR-012/FR-012a).
- [ ] **T040** Implement target normalization in `sqlitch/cli/commands/target.py` and helpers for relative paths, :memory:, and registry resolution (FR-021).
- [ ] **T041** Add engine alias resolution in `sqlitch/cli/commands/engine.py`, leveraging target storage and parity errors (FR-022).
- [ ] **T042** Synchronize template discovery/rendering across `sqlitch/cli/commands/{init,add,rework}.py` and `sqlitch/utils/fs.py`, ensuring byte-for-byte parity with Sqitch templates (FR-020).
- [ ] **T043 [P]** Implement `ProjectMetadata` and `DeploymentStatus` dataclasses in `sqlitch/cli/_models.py`, enforcing immutability, validation, and serialization rules outlined in data-model.md §§3.1–3.2.
- [ ] **T044 [P]** Create `Script` and `ScriptResult` helpers in `sqlitch/utils/fs.py` (or dedicated module) with checksum calculation and lifecycle hooks per data-model.md §4.1, plus unit tests covering success and failure paths.
- [ ] **T045 [P]** Add `DeployOptions` and `RevertOptions` dataclasses to `sqlitch/cli/commands/_models.py`, mirroring data-model.md §§4.3–4.4, and refactor CLI commands to consume them with validation on mutually exclusive flags.
- [ ] **T046** Normalize CLI error messaging across commands using centralized formatter to satisfy NFR-005 parity expectations.

## Phase 3.4 – Integration & Polish
- [ ] **T047** Re-run and stabilize quickstart integration in `tests/integration/test_quickstart_sqlite.py`, ensuring all tutorial scenarios pass with new behaviors.
- [ ] **T048** Run the full pytest suite (`python -m pytest`) from repo root and log pass/fail results before closing tasks (NFR-006 gate).
- [ ] **T049** Update documentation (`docs/reports/sqlite-tutorial-parity.md`, `REPORT.md`) with config precedence, failure logging, and template parity notes.
- [ ] **T050** Refresh release artifacts (`REPORT-TASKS.md`, `IMPLEMENTATION_REPORT.md`) and capture coverage results ≥90% (NFR-002).
- [ ] **T051** Execute performance smoke (`tests/performance/test_deploy_latency.py`) validating <5s deploy for <100 changes, documenting in the parity report (NFR-003).
- [ ] **T052** Sync agent context via `.specify/scripts/bash/update-agent-context.sh copilot` with new tech highlights after implementation wraps.

## Dependencies
- T001 → T003–T005, T014, T017, T021, T022, T023.
- T002 → T009–T013, T025 (shared goldens).
- T003, T004 precede T026–T028.
- T007 precedes T008, T008a, T011, T015, T035.
- T008 precedes T008a, T009, T010, T013, T035–T037.
- T008a precedes T035–T037.
- T014/T015/T016 precede T030–T032.
- T017/T018 precede T040–T041.
- T019/T020/T021 precede T031/T042.
- T022 precedes T042.
- T025 precedes T047–T052.
- T047 precedes T048.
- T048 precedes T049–T052.

## Parallel Execution Example
```
# After completing T001 and T002 dependencies:
Task: "T009 [P] Add log failure rendering assertions in tests/cli/commands/test_log_functional.py"
Task: "T010 [P] Extend status command tests in tests/cli/commands/test_status_functional.py"
Task: "T011 [P] Create verify parity suite in tests/cli/commands/test_verify_functional.py"
Task: "T012 [P] Create revert parity suite in tests/cli/commands/test_revert_functional.py"
```

```
# Once T030–T037 implementations are complete and T047/T048 have passed:
Task: "T049 Update documentation (docs/reports/sqlite-tutorial-parity.md, REPORT.md)"
Task: "T050 Refresh release artifacts (REPORT-TASKS.md, IMPLEMENTATION_REPORT.md)"
Task: "T052 Sync agent context via .specify/scripts/bash/update-agent-context.sh copilot"
```
