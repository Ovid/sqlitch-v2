# Implementation Plan: Quality Lockdown and Stabilization

**Branch**: `005-lockdown` | **Date**: 2025-10-12 (Updated) | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/005-lockdown/spec.md`  
**Target**: Alpha release (NOT v1.0.0 - this is still alpha software)

## Execution Flow (/plan command scope)
1. ✅ Loaded feature specification from `/specs/005-lockdown/spec.md` and processed clarifications.
2. ✅ Populated Technical Context using repository conventions (Python 3.11 CLI app).
3. ✅ Reviewed Constitution v1.10.1 for mandatory principles.
4. ✅ Documented initial constitution check (no violations detected).
5. ✅ Recorded Phase 0 research notes in [`research.md`](./research.md).
6. ✅ Generated Phase 1 design artifacts (`data-model.md`, `contracts/cli-uat-compatibility.md`, `quickstart.md`).
7. ✅ Re-ran constitution check after design (still compliant).
8. ▶️ Phase 2 task planning will run under `/tasks`.
9. ⏹️ Ready for `/tasks` execution once this plan is approved.

## Summary
The lockdown feature prepares SQLitch for a stable **alpha release** by driving coverage, documentation, and security to the constitutional bar while proving Sqitch parity through new UAT compatibility scripts. Work emphasizes tightening existing modules (`config/resolver`, `registry/state`, `utils/identity`), codifying documentation and manual gates, and introducing forward/backward compatibility scripts that reuse the SQLite tutorial workflow. All compatibility validation remains manual via the release checklist, with evidence captured in release PR comments.

**Important**: This is NOT a v1.0.0 release. SQLitch remains alpha software requiring additional validation and real-world usage before production readiness.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: Click (CLI), sqlite3, pytest/pytest-randomly, pip-audit, bandit  
**Storage**: Tutorial SQLite databases (`flipr_test.db`, `flipr_prod.db`, `dev/flipr.db`), Sqitch/SQLitch registry databases  
**Testing**: pytest (unit/integration/golden), click.testing `CliRunner`, manual UAT harnesses under `uat/`  
**Target Platform**: macOS & Linux command-line environments  
**Project Type**: Single CLI + library repository  
**Constraints**: Maintain ≥90% coverage, pass mypy --strict, document manual UAT runs, no new feature work during lockdown, pylint analysis required  
**Scale/Scope**: Sqitch tutorial workflow, existing config/plan/engine modules, release preparations for alpha release (NOT v1.0.0)

## Constitution Check
- **Test-First Development**: Future task list will ensure failing tests precede fixes (coverage, docstrings, UAT harness regression tests).
- **Observability & Determinism**: Compatibility scripts keep human-readable output and sanitize timestamps/SHA1s without emitting structured logs.
- **Behavioral Parity**: All compatibility flows strictly follow `sqitchtutorial-sqlite.pod`; deviations must be documented with rationale.
- **Simplicity-First**: Reuse and extract helpers from `uat/side-by-side.py` rather than rewrite logic; defer multi-engine support.
- **Documented Interfaces**: Plan mandates docstring coverage, README/CONTRIBUTING updates, and release checklist documentation.
- **Sqitch Implementation as Source of Truth**: All behavior must be verified against Sqitch's implementation in the `sqitch/` directory. This includes syntax support (e.g., `@HEAD^`), error handling, and edge cases.

Result: ✅ Initial constitution gate passes; no complexity exemptions required.

### 🎯 Critical Principle: Sqitch Behavioral Parity
**All SQLitch implementation work MUST verify behavior against the Perl Sqitch codebase in `sqitch/`.**

This constitutional requirement means:
- Before implementing features: Consult `sqitch/lib/App/Sqitch/` for canonical behavior
- During implementation: Match Sqitch's handling of syntax, options, edge cases, and error paths
- During testing: Verify against actual Sqitch behavior, not documentation alone
- When behavioral differences are found: Update SQLitch to match (document any intentional deviations)

This principle applies to lockdown work and all future development.

## Project Structure
```
sqlitch/
├── cli/                # Click command bootstrap and context
├── config/             # Loader/resolver modules targeted for coverage
├── engine/             # Database engines (sqlite, postgres, mysql, etc.)
├── plan/               # Plan parser/model utilities
├── utils/              # Shared helpers (time, templates, logging, identity)
└── __init__.py

tests/
├── cli/
├── config/
├── integration/
├── regression/
└── support/            # Golden fixtures & tutorial parity harness

uat/
├── side-by-side.py     # Existing parity harness
├── forward-compat.py   # (Planned) sqlitch→sqitch validation
├── backward-compat.py  # (Planned) sqitch→sqlitch validation
└── shared helpers      # sanitization.py, comparison.py, test_steps.py (planned)

specs/005-lockdown/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

**Structure Decision**: Single Python CLI/library repository; enhancements span `sqlitch/*`, `tests/*`, `uat/`, and documentation assets.

## Phase 0: Outline & Research
- Captured clarifications on UAT scope (SQLite-only), manual execution cadence, and evidence capture in [`research.md`](./research.md).
- Summarized baseline coverage metrics and target modules from `BASELINE_ASSESSMENT.md`.
- Identified helper extraction strategy (sanitization/comparison/test steps) to minimize duplication across UAT scripts.

Deliverable: Research doc complete ✅

## Phase 1: Design & Contracts
- Documented operational artifacts and planned helper modules in [`data-model.md`](./data-model.md); no schema changes required.
- Defined CLI contract expectations for compatibility scripts in [`contracts/cli-uat-compatibility.md`](./contracts/cli-uat-compatibility.md).
- Authored [`quickstart.md`](./quickstart.md) covering setup, quality gates, manual UAT execution, and release PR comment template.
- Confirmed that future test work will add failing tests for coverage gaps, docstrings, security scans, and new UAT harness behaviours before implementation.

Post-design constitution check: ✅ unchanged (still compliant).

## Phase 1.1: Quality Signal Follow-Up (2025-10-12)
- Recorded fresh gate results (pytest ✅, coverage 91.39%) exposing three regression areas:
  - **Type Safety**: `mypy` currently reports 70 errors concentrated in `sqlitch/cli/commands/{target,deploy,rework,...}`; requires coordinated refactor plus regression guard to keep `mypy --strict` in CI.
  - **Linting**: `flake8` reports 73 violations (line length, unused imports, duplicate helpers) led by `sqlitch/registry/migrations.py`; plan includes trimming lines, removing unused imports, and consolidating helper definitions.
  - **Security**: `bandit` flags SHA1 usage in `sqlitch/utils/identity.py`; mitigation is to mark `usedforsecurity=False` while keeping Sqitch-compatible change IDs.
- Action: escalate these items into Phase 3 tasks (see new T120–T123) and document black/mypy regression tests to ensure future runs fail fast.

## Phase 1.2: Pylint Remediation Workflow (2025-10-12)
**Objective**: Treat pylint as a constitutional quality gate by driving issues to closure, not simply documenting them.

**Status**: ▶️ **IN PROGRESS — ANALYSIS COMPLETE, REMEDIATION REQUIRED**

### Execution Summary

1. **Baseline Report Generated**: ✅
   ```bash
   pylint sqlitch tests --output-format=json > pylint_report.json
   ```
   - Report saved to workspace root
   - 182 total issues identified
   - Score: **9.65/10** (excellent baseline)

2. **Issue Analysis Completed**: ✅
   - Parsed JSON report systematically
   - Categorized by type: errors (2), warnings (90), refactor (86), convention (4)
   - Identified top issue symbols and file hotspots
   - **Key Finding**: 0 issues in test files (tests/ directory 100% clean)

3. **Remediation Plan Established**: ✅
   - New Phase 3.8 tasks (see `tasks.md`) elevate pylint remediation to P1/P2 work
   - Gate requirements:
     - Zero `fatal`/`error` diagnostics before lockdown completion
     - Warnings/refactors reduced or scheduled with explicit owners and deadlines
     - `tox -e lint` (or equivalent) enforced in CI with `--fail-under` guard

4. **Convention Fixes Applied**: ✅ (2025-10-12)
   - T130 series hardened unavoidable suppressions with rationale
   - Remaining conventions tracked for follow-up as part of new remediation phase

5. **Remediation Execution**: 🚧
   - Current score: **9.66/10** (downstream work must maintain or raise)
   - Total issues: **179** (target is active reduction, not deferral)
   - Report: `specs/005-lockdown/artifacts/final/pylint_report.json`
   - Error backlog must be cleared as part of Phase 3.8 remediation tasks

6. **Documentation Updated in research.md**: ✅
   - Captures baseline, remediation scope, and outstanding work

### Pylint Gate Outcomes

**Mandatory Deliverables**:
- ✅ Baseline captured and analyzed
- 🔄 Remediation plan in progress with tracked tasks and owners
- 🔄 Automated lint gate required before declaring lockdown complete

**Deferred Items (Require Explicit Scheduling)**:
- Unused argument warnings (67) — tracked under new Phase 3.8 tasks
- Complexity metrics (too-many-arguments/locals, duplicate-code) — assigned as follow-up with remediation timeline
- Broad exception handling review — targeted refactor tasks opened

**Constitutional Alignment**: 🔒 Enforced
- Analysis alone no longer sufficient; remediation tied to quality gate checklist
- Deviations require documented suppressions and reviewer visibility
- Prevents regression by wiring lint gate into CI workflows

### Execution Summary

1. **Baseline Report Generated**: ✅
   ```bash
   pylint sqlitch tests --output-format=json > pylint_report.json
   ```
   - Report saved to workspace root
   - 182 total issues identified
   - Score: **9.65/10** (excellent baseline)

2. **Issue Analysis Completed**: ✅
   - Parsed JSON report systematically
   - Categorized by type: errors (2), warnings (90), refactor (86), convention (4)
   - Identified top issue symbols and file hotspots
   - **Key Finding**: 0 issues in test files (tests/ directory 100% clean)

3. **Tasks Created in tasks.md**: ✅
   - **Phase 3.9** added with 8 new tasks (T130-T136)
   - Tasks categorized by issue type:
     - T130 series: Convention fixes (4 issues)
     - T131: Unused arguments (67 issues)
     - T132: Argument count reduction (37 issues)
     - T133: Local variable reduction (18 issues)
     - T134: Exception handling (13 issues)
     - T135-T136: Validation and documentation
   - Each task includes file locations, validation commands, and success targets

4. **Documentation Updated in research.md**: ✅
   - Added comprehensive "Pylint Analysis - Updated Baseline" section
   - Documented 36% reduction from initial baseline (286 → 182 issues)
   - Score improvement: 9.29 → 9.65 (+0.36 points)
   - Detailed breakdown by type, symbol, and file
   - Implementation strategy and validation protocol documented

### Remediation Milestones

**Baseline Snapshot (2025-10-12)**:
- Initial pylint run produced **182 total diagnostics** (2 errors, 90 warnings, 86 refactors, 4 conventions) with a score of **9.65/10**.
- Results captured in `specs/005-lockdown/artifacts/baseline/pylint_report.json` and summarized in `research.md`.

**Active Remediation Tasks (Phase 3.8 · T140–T149)**:
- **T140 & T141 (P1)**: Eliminate all remaining `fatal`/`error` diagnostics and document any unavoidable suppressions.
- **T142 (P1)**: Enforce the lint gate via `tox -e lint --fail-under=9.00`, failing on new errors or regressions.
- **T143–T146 (P2)**: Drive down high-volume warnings (unused arguments, complexity metrics, duplicate code) or schedule documented follow-ups.
- **T147–T149 (P1)**: Record before/after metrics, capture final lint gate evidence, and log deferred items in `TODO.md` with owners and timelines.

**Legacy Analysis (T237–T243)**:
- Earlier documentation-only findings remain archived for context but no longer represent the active remediation scope.

### Validation Plan

- Re-run `pylint sqlitch tests --output-format=json` after each remediation wave and store updated reports under `specs/005-lockdown/artifacts/`.
- Maintain a running metrics table in `research.md` and `IMPLEMENTATION_REPORT_LOCKDOWN.md`, highlighting score trends and issue counts.
- Confirm CI executes `tox -e lint` with the 9.00 threshold before declaring the lockdown complete.
- Any unresolved warnings/refactors at release time must have dated follow-up tickets per T149.

## Phase 2: Task Planning Approach (preview)
- `/tasks` will transform design artifacts into actionable steps:
  - Coverage and docstring gaps → failing tests then fixes per module.
  - Security gates → scripted checks plus remediation tasks.
  - UAT scripts → shared helper extraction, forward/backward script implementation, manual checklist updates, evidence-review tasks.
  - **UAT Validation Protocol**: Before testing sqlitch parity, verify sqitch behavior matches tutorial expectations from `uat/sqitchtutorial-sqlite.pod`.
- Tasks remain grouped by phase (Assessment, Coverage, Documentation, Stability, Security, UAT Validation) with P1 priority for constitutional gates and manual UAT deliverables.

## Critical Discovery (2025-10-11)

### UAT Script Validation Issue (Resolved)
**UAT Script Validation Issue Identified**: During execution of T060b, discovered that `uat/side-by-side.py` step 30 fails because the script removes test directories without preserving essential project files (`sqitch.conf`, `sqitch.plan`). This revealed a fundamental flaw in the UAT validation approach:

**Problem**: The UAT script was testing "sqlitch vs sqitch" without first verifying that sqitch behavior itself matches the tutorial expectations from `sqitchtutorial-sqlite.pod`.

**Impact**: When step 30 (`sqitch deploy db:sqlite:dev/flipr.db`) produced "Plan file sqitch.plan does not exist", we discovered the UAT script's test setup doesn't match the tutorial workflow. According to the tutorial, this command should produce:
```
Adding registry tables to db:sqlite:dev/sqitch.db
Deploying changes to db:sqlite:dev/flipr.db
  + users ................... ok
  + flips ................... ok
```

**Root Cause**: UAT script removes working directories between test phases without recreating the project context that the tutorial assumes.

**Resolution**: Added new task T060b2 to establish a validation protocol:
1. Before running any UAT comparison, verify each test step against corresponding tutorial section
2. Ensure UAT script setup (files, directories, context) matches tutorial prerequisites  
3. Validate that sqitch produces tutorial-expected output at every step FIRST
4. Only after sqitch behavior is verified correct, proceed to test sqlitch parity

This discovery reinforces the constitutional principle: **Sqitch implementation is the source of truth**, and the tutorial documents expected behavior. UAT scripts must validate against both.

### Missing Rework Support (BLOCKING - 2025-10-11)

**Critical Missing Feature Identified**: During UAT execution at step 39 (`sqitch rework userflips`), discovered that SQLitch's plan parser does not support **reworked changes** - a core Sqitch feature that allows the same change name to appear multiple times in the plan with different versions.

**CONSTITUTIONAL VIOLATION**: This is a fundamental behavioral parity gap. Sqitch explicitly allows and expects reworked changes via the `sqitch rework` command.

**Sqitch's Rework Behavior** (verified in `sqitch/lib/App/Sqitch/Plan.pm`):
- Allows duplicate change names in plan files
- Uses tag dependency syntax to mark rework versions: `change_name [change_name@tag_name]`
- Example from tutorial step 39: `userflips [userflips@v1.0.0-dev2]` creates a new version of userflips
- Maintains rework chains via `add_rework_tags` method
- Uses `@HEAD` suffix internally to track latest version

**SQLitch's Current Behavior**:
- Plan parser explicitly rejects duplicate change names in `Plan.__post_init__`
- Raises `ValueError: Plan contains duplicate change name: userflips`
- Cannot parse plans created by `sqitch rework` command

**Impact**:
- UAT execution blocked at step 39 (cannot parse plan after `sqitch rework userflips`)
- Steps 39-46 cannot be tested without this feature
- Forward/backward compatibility testing blocked
- Cannot claim Sqitch parity without rework support

**Required Implementation** (Task T067):
1. Remove duplicate name validation from `Plan.__post_init__`
2. Add rework relationship tracking to `Change` model
3. Update plan parser to handle rework syntax
4. Implement `@HEAD` version tracking for changes
5. Update symbolic resolution to use latest version by default
6. Add comprehensive rework tests

**Blocking Tasks**: T060b (side-by-side UAT), T060c-T060f (forward/backward compat)

**Priority**: P1 - CRITICAL - Must be implemented before lockdown can proceed

## Complexity Tracking
_None required; plan remains within constitutional constraints._

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 3.7: Test suite consolidation (2025-10-12) - 37 tasks to reduce file count by ~34-37 files
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented (not required)
- [ ] Test consolidation complete (Phase 3.7: T130a-T134d)
- [ ] Implementation report assembled (`specs/005-lockdown/IMPLEMENTATION_REPORT_LOCKDOWN.md`) capturing rerun results for pytest, mypy, pydocstyle, pip-audit, bandit, tox, and summarizing follow-up actions

---
*Based on Constitution v1.10.1 — see `.specify/memory/constitution.md`*
