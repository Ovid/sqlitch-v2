# Tasks: SQLite Tutorial Parity

**Input**: Design documents from `/specs/004-sqlitch-tutorial-parity/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅, contracts/README ✅

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
- [ ] **T043 [P]** Flesh out remaining data-model helpers in `sqlitch/cli/_models.py` (e.g., `ProjectMetadata`, `DeploymentStatus`, `CommandResult`) per design doc.
- [ ] **T044 [P]** Implement script domain helpers in `sqlitch/utils/fs.py` or new module (`Script`, `ScriptResult`) matching data-model expectations.
- [ ] **T045 [P]** Introduce deploy/revert option dataclasses in `sqlitch/cli/commands/_models.py` and refactor commands to use them (data-model §§4.3–4.4).
- [ ] **T046** Normalize CLI error messaging across commands using centralized formatter to satisfy NFR-005 parity expectations.

## Phase 3.4 – Integration & Polish
- [ ] **T047** Re-run and stabilize quickstart integration (`tests/integration/test_quickstart_sqlite.py`) ensuring all scenarios, especially Scenario 10, pass with new behaviors.
- [ ] **T048** Update documentation (`docs/reports/sqlite-tutorial-parity.md`, `REPORT.md`) with config precedence, failure logging, and template parity notes.
- [ ] **T049** Refresh release artifacts (`REPORT-TASKS.md`, `IMPLEMENTATION_REPORT.md`) and capture coverage results ≥90% (NFR-002).
- [ ] **T050** Execute performance smoke (`tests/performance/test_deploy_latency.py`) validating <5s deploy for <100 changes, documenting in parity report (NFR-003).
- [ ] **T051** Sync agent context via `.specify/scripts/bash/update-agent-context.sh copilot` with new tech highlights after implementation wraps.

## Dependencies
- T001 → T003–T005, T014, T017, T021, T022, T023.
- T002 → T009–T013, T025 (shared goldens).
- T003, T004 must precede T026–T028.
- T007 precedes T008, T011, T015, T035.
- T008 precedes T009, T010, T013, T035–T037.
- T014/T015/T016 precede T030–T032.
- T017/T018 precede T040–T041.
- T019/T020/T021 precede T031/T042.
- T022 precedes T042.
- T025 precedes T047–T050.

## Parallel Execution Example
```
# After completing T001 and T002 dependencies:
Task: "T009 [P] Add log failure rendering assertions in tests/cli/commands/test_log_functional.py"
Task: "T010 [P] Extend status command tests in tests/cli/commands/test_status_functional.py"
Task: "T011 [P] Create verify parity suite in tests/cli/commands/test_verify_functional.py"
Task: "T012 [P] Create revert parity suite in tests/cli/commands/test_revert_functional.py"
```

```
# Once T030–T037 implementations are complete:
Task: "T047 Re-run and stabilize quickstart integration (tests/integration/test_quickstart_sqlite.py)"
Task: "T048 Update documentation (docs/reports/sqlite-tutorial-parity.md, REPORT.md)"
Task: "T049 Refresh release artifacts (REPORT-TASKS.md, IMPLEMENTATION_REPORT.md)"
```
  - Depends on: T007
- [ ] **T010k** Add revert command regression tests in `tests/cli/commands/test_revert_functional.py` for confirmation prompts, `--yes` bypass, dependency protection, and failure messaging (FR-012/FR-012a).
  - Ensure prompts match Sqitch wording byte-for-byte and that declined confirmations leave registry untouched.
  - Depends on: T007
- [ ] **T010l** Add config formatting preservation tests in `tests/config/test_loader.py` (and writer fixtures) validating multiline values, indentation, and comment retention across read/write cycles (FR-002/FR-003).
  - Use golden INI fixtures to assert byte-identical round trips for system/user/local scopes.
  - Depends on: T003
- [ ] **T010m** Add registry schema parity guard in `tests/registry/test_schema_parity.py` comparing `sqlitch/registry/migrations.py` DDL against Sqitch’s SQLite schema (FR-017).
  - Compute canonicalized SQL digests and fail on divergence.
  - Depends on: T001
- [ ] **T010n** Extend plan validation tests in `tests/plan/test_validation.py` to assert duplicate names, missing dependencies, and conflict cycles raise Sqitch-identical errors (FR-019).
  - Introduce fixtures mirroring Sqitch failure cases for parity checking.
  - Depends on: T010a
- [ ] **T010o** Add error message parity tests in `tests/cli/commands/test_errors_functional.py` covering representative CLI failure paths (deploy, verify, revert) to satisfy NFR-005.
  - Assert error text, formatting, and exit codes align with Sqitch goldens.
  - Depends on: T007, T010j, T010k

## Phase 3.3 – Implementation
- [ ] **T011** Update resolver merge logic in `sqlitch/config/resolver.py` to enforce scope precedence and ignore duplicate files.
  - Depends on: T002
- [ ] **T012** Adjust loader grammar in `sqlitch/config/loader.py` per FR-023; normalize header casing and strip `%core.uri` references.
  - Depends on: T003
- [ ] **T012a** Update plan formatter implementation in `sqlitch/plan/formatter.py` to emit Sqitch-compact format for changes and tags, reusing parser models for deterministic field ordering.
  - Depends on: T010a, T010b
- [ ] **T012b** Ensure CLI writers (`sqlitch/cli/commands/{init,add,tag,rework}.py`) and helper utilities leverage the updated formatter, removing verbose-format fallbacks and adjusting write paths.
  - Depends on: T012a
- [ ] **T012c** Update `sqlitch/cli/commands/engine.py` to resolve existing target aliases when adding or altering engines, mirroring Sqitch’s lookup order and emitting parity error messages when targets are missing.
  - Depends on: T010c, T010d
- [ ] **T012d** Adjust configuration helpers in `sqlitch/config/resolver.py` and CLI context builders to expose target URIs for engine commands, ensuring tutorial `engine add sqlite flipr_test` flow succeeds post-init.
  - Depends on: T012c
- [X] **T012e** Audit `sqlitch/cli/commands/add.py` to resolve any regressions surfaced by T010b/T010e parity tests, keeping dependency, conflicts, and note handling aligned with Sqitch.
  - Depends on: T010e
- [X] **T012f** Update `sqlitch/cli/commands/tag.py` if T010f uncovers ordering or formatting drift, ensuring tag listings and duplicate detection match Sqitch.
  - Depends on: T010f
- [ ] **T012g** Adjust `sqlitch/cli/commands/rework.py` per findings from T010g so @tag script generation, dependency copying, and messaging remain parity-accurate.
  - Depends on: T010g
- [ ] **T012h** Synchronize template discovery and rendering utilities (`sqlitch/cli/commands/add.py`, `sqlitch/cli/commands/rework.py`, `sqlitch/cli/commands/init.py`, `sqlitch/utils/fs.py`) to ensure Sqitch templates are loaded without mutation and accommodate any fixes highlighted by T010h.
  - Depends on: T010h
- [ ] **T012i** Patch `sqlitch/cli/commands/target.py` and related URI helpers to mirror Sqitch parsing semantics (relative path resolution, :memory: support, registry sibling detection) based on gaps revealed in T010i.
  - Depends on: T010i
- [ ] **T012j** Align verify command implementation in `sqlitch/cli/commands/verify.py` with new T010j parity tests, ensuring failure aggregation, output ordering, and exit codes match Sqitch.
  - Depends on: T010j
- [ ] **T012k** Address revert command gaps in `sqlitch/cli/commands/revert.py` highlighted by T010k, covering confirmation prompts, dependency guards, and error messaging.
  - Depends on: T010k
- [ ] **T012l** Update config read/write helpers (`sqlitch/config/loader.py`, `sqlitch/config/resolver.py`, and writer utilities) to maintain indentation, multiline values, and comment fidelity per T010l.
  - Depends on: T010l
- [ ] **T012m** Reconcile registry migrations in `sqlitch/registry/migrations.py` with Sqitch schema differences uncovered by T010m (column types, indexes, triggers) to maintain parity.
  - Depends on: T010m
- [ ] **T012n** Update plan validation logic in `sqlitch/plan/validation.py` (and related helpers) to reflect expectations from T010n duplicate/conflict tests.
  - Depends on: T010n
- [ ] **T012o** Normalize CLI error messaging across commands (deploy, verify, revert) in light of T010o parity assertions, ensuring output channels and copy match Sqitch.
  - Depends on: T010o
- [ ] **T013** Modify config CLI write paths in `sqlitch/cli/commands/config.py` to block `core.uri` entries and respect new precedence rules.
  - Depends on: T004, T011, T012
- [ ] **T014** Update init scaffolding in `sqlitch/cli/commands/init.py` and templates under `sqlitch/templates/` to omit `%core.uri` while preserving Sqitch note layout.
  - Ensure `engine.<engine>.target` is written only when `--target` is supplied (FR-007a) and propagate optional target flag through scaffolding helpers.
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
- [ ] **T022** Execute performance smoke test (`tests/performance/test_deploy_latency.py`) to confirm deploy of <100 changes completes within 5 seconds (NFR-003), documenting results in `docs/reports/sqlite-tutorial-parity.md`.
  - Depends on: T015, T019
