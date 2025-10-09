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
- [X] **T001** Refresh tutorial fixtures to include config/env overrides in `tests/support/tutorial_parity/`.
  - Output: sanitized fixture tree with `sqitch.conf` lacking `%core.uri` and env override metadata.

## Phase 3.2 – Tests First
- [X] **T002** Add resolver scope precedence tests in `tests/config/test_resolver.py`.
  - Cover FR-001a: system → user → local ordering and duplicate-file rejection.
  - Depends on: T001
- [X] **T003** Add loader grammar coverage for FR-023 in `tests/config/test_loader.py`.
  - Ensure parser accepts uppercase section headers and rejects stray `%core.uri` entries.
  - Depends on: T001
- [X] **T004** Extend config CLI functional tests in `tests/cli/commands/test_config_functional.py` to enforce FR-001a interactions and absence of `core.uri` writes.
  - Depends on: T002, T003
- [X] **T005** Add init command regression in `tests/cli/commands/test_init_functional.py` confirming new project configs omit `%core.uri` and respect engine default notes.
  - Add assertion that `engine.<engine>.target` is absent unless user provided `--target`, covering FR-007a.
  - Depends on: T002
- [X] **T006** Create environment precedence matrix tests in `tests/cli/commands/test_deploy_functional.py` validating SQLITCH_* → SQITCH_* → GIT_* chain (FR-005a).
  - Depends on: T001
- [X] **T007** Add deploy failure event tests in `tests/cli/commands/test_deploy_functional.py` asserting `events` table captures `deploy_fail` rows with identity + note (FR-010a).
  - Depends on: T006
- [X] **T008** Add log formatting tests in `tests/cli/commands/test_log_functional.py` for failure events and ensure output matches Sqitch parity (FR-010a).
  - Depends on: T007
- [X] **T009** Extend status command tests in `tests/cli/commands/test_status_functional.py` to surface last failure metadata when deployment pending (FR-010a).
  - Depends on: T007
- [X] **T010** Add end-to-end Scenario 10 coverage in `tests/integration/test_quickstart_sqlite.py` executing config/env overrides + failure handling.
  - Depends on: T002, T006, T007

- [X] **T010a** Add compact plan formatter regression tests in `tests/plan/test_formatter.py` asserting output matches Sqitch fixture bytes for a multi-change plan.
  - Capture golden fixture under `tests/support/golden/tutorial_parity/plan_compact` and ensure formatter respects timestamp + planner formatting.
  - Depends on: T001
- [X] **T010b** Add CLI integration test in `tests/cli/commands/test_add_functional.py` verifying `sqlitch add` emits compact entries (no verbose format) when appending to `sqitch.plan`.
  - Extend existing fixture expectations (or add new golden file) to assert entry structure and dependency serialization.
  - Depends on: T010a
- [X] **T010c** Add engine alias functional tests in `tests/cli/commands/test_engine_functional.py` ensuring `engine add sqlite flipr_reg` resolves `target.flipr_reg.uri` when the target exists.
  - Cover success case (writes `engine.sqlite.target` URI) and failure case (unknown target name emits Sqitch-equivalent error).
  - Depends on: T002 (config scaffolding) and existing target command fixtures.
- [X] **T010d** Add regression test in `tests/cli/commands/test_target_functional.py` confirming `target add` persists alias entries consumed by the new engine test, keeping tutorial workflow intact.
  - Ensure config writes remain silent and paths match FR-022 expectations.
  - Depends on: T010c
- [X] **T010e** Extend add-command regression coverage in `tests/cli/commands/test_add_functional.py` to assert dependency flags, quiet mode, and script templating remain Sqitch-identical.
  - Capture stdout/stderr fixtures for `--requires`, `--conflicts`, and `--note` flows to guard FR-009 behavior.
  - Depends on: Existing add fixtures (no additional prerequisites).
  - Include golden output assertions for default listing to cover FR-015.
  - Depends on: T010e (plan fixtures shared).
- [X] **T010f** Add tag-command regression coverage in `tests/cli/commands/test_tag_functional.py` to guard Sqitch output parity, including quiet mode suppression and golden stdout fixtures.
  - Capture stdout comparison leveraging `tests/support/golden/cli/tag_users_output.txt` and assert quiet mode yields no additional output.
  - Depends on: T010e (plan fixtures shared).
- [ ] **T010g** Add rework-command regression suite in `tests/cli/commands/test_rework_functional.py` confirming @tag suffix script generation, dependency preservation, and quiet mode parity (FR-016).
  - Ensure fixtures cover both tagged and untagged change flows.
  - Depends on: T010f
- [ ] **T010h** Add script template parity test in `tests/templates/test_sqlite_templates.py` comparing deployed `sqlitch/templates/sqlite/*.tmpl` files against Sqitch golden fixtures via byte digests.
  - Reuse checksum helper so deploy/revert/verify templates fail fast when diverging (FR-020).
  - Depends on: T001
- [ ] **T010i** Add target URI parsing tests in `tests/cli/commands/test_target_functional.py` validating relative path resolution, in-memory databases, and normalization of registry sibling paths (FR-021).
  - Include coverage for environment overrides (`SQLITCH_TARGET`) and ensure outputs match Sqitch fixtures.
  - Depends on: T010d
- [ ] **T010j** Expand verify command parity tests in `tests/cli/commands/test_verify_functional.py` to cover success, single failure, multi-failure, and out-of-order deployment scenarios (FR-011/FR-011a).
  - Capture stdout/stderr fixtures matching Sqitch and assert summary exit codes across all permutations.
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
