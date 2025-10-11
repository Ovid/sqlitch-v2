# Implementation Plan: Quality Lockdown and Stabilization

**Branch**: `005-lockdown` | **Date**: 2025-10-10 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/005-lockdown/spec.md`

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
The lockdown feature prepares SQLitch for a stable 1.0 release by driving coverage, documentation, and security to the constitutional bar while proving Sqitch parity through new UAT compatibility scripts. Work emphasizes tightening existing modules (`config/resolver`, `registry/state`, `utils/identity`), codifying documentation and manual gates, and introducing forward/backward compatibility scripts that reuse the SQLite tutorial workflow. All compatibility validation remains manual via the release checklist, with evidence captured in release PR comments.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: Click (CLI), sqlite3, pytest/pytest-randomly, pip-audit, bandit  
**Storage**: Tutorial SQLite databases (`flipr_test.db`, `flipr_prod.db`, `dev/flipr.db`), Sqitch/SQLitch registry databases  
**Testing**: pytest (unit/integration/golden), click.testing `CliRunner`, manual UAT harnesses under `uat/`  
**Target Platform**: macOS & Linux command-line environments  
**Project Type**: Single CLI + library repository  
**Constraints**: Maintain ≥90% coverage, pass mypy --strict, document manual UAT runs, no new feature work during lockdown  
**Scale/Scope**: Sqitch tutorial workflow, existing config/plan/engine modules, release preparations for v1.0.0

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

## Phase 2: Task Planning Approach (preview)
- `/tasks` will transform design artifacts into actionable steps:
  - Coverage and docstring gaps → failing tests then fixes per module.
  - Security gates → scripted checks plus remediation tasks.
  - UAT scripts → shared helper extraction, forward/backward script implementation, manual checklist updates, evidence-review tasks.
- Tasks remain grouped by phase (Assessment, Coverage, Documentation, Stability, Security, UAT Validation) with P1 priority for constitutional gates and manual UAT deliverables.

## Complexity Tracking
_None required; plan remains within constitutional constraints._

## Progress Tracking
**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented (not required)
- [ ] Implementation report assembled (`specs/005-lockdown/IMPLEMENTATION_REPORT_LOCKDOWN.md`) capturing rerun results for pytest, mypy, pydocstyle, pip-audit, bandit, tox, and summarizing follow-up actions

---
*Based on Constitution v1.10.1 — see `.specify/memory/constitution.md`*
