
# Implementation Plan: SQLitch Python Parity Fork MVP

**Branch**: `[002-sqlite]` | **Date**: 2025-10-05 | **Spec**: [`/specs/002-sqlite/spec.md`](./spec.md)
**Input**: Feature specification from `/specs/002-sqlite/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Ship a SQLite-first SQLitch release that mirrors Sqitch CLI behavior, enforces structured logging and registry isolation, and proves the engine framework is extensible by wiring stub MySQL/PostgreSQL adapters into the registry/tests for future milestones.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: Click, Rich, SQLAlchemy Core, Pydantic, sqlite3, PyMySQL (stub), psycopg[binary] (stub)  
**Storage**: SQLite registry file (`sqitch.db`) for runtime; stub DSNs for MySQL/PostgreSQL adapters  
**Testing**: pytest + pytest-cov, tox (lint/type/security), golden fixture comparisons  
**Target Platform**: macOS, Linux, Windows CLI environments
**Project Type**: single (monolithic CLI package with mirrored tests)  
**Performance Goals**: SQLite deploy/revert happy paths <200ms, long-running flows stream progress per constitution.  
**Constraints**: ≥90% coverage, structured logging with run IDs, docstrings + `__all__`, no secrets in logs, Docker suites auto-skip when unavailable.  
**Scale/Scope**: Plans up to 10k entries, registry tables scaling to millions of rows, contributors across all three desktop OSes.

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Test-First Development: `/tasks` will generate failing contract/regression tests before implementation begins, maintaining Red→Green discipline.
- CLI-First Contracts: All features are driven through Click commands exposing human-readable and `--json` outputs with structured logging.
- Library Separation: Core behavior resides in `sqlitch/` modules; CLI commands remain thin wrappers.
- Observability & Determinism: Structured logging sink, run identifiers, and parity smoke tests enforce constitution Section V.
- Documented Interfaces & Type Hints: Plan reiterates docstring, `__all__`, and modern typing mandates inherited from prior review tasks.
- State Management & Registry Lifecycle: Registry isolation (FR-021/FR-022) and stub adapters ensure global registries remain well-documented and replaceable.

No violations detected; Complexity Tracking remains empty.

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
ios/ or android/
```
sqlitch/
├── __init__.py
├── cli/
│   ├── commands/
│   ├── main.py
│   └── options.py
├── config/
├── engine/
│   ├── base.py
│   ├── sqlite.py
│   └── __init__.py
├── plan/
├── registry/
└── utils/

tests/
├── cli/
│   ├── contracts/
│   └── regression/
├── engine/
├── plan/
├── registry/
├── scripts/
└── support/

docs/
├── architecture/
└── reports/

scripts/
└── docker-compose/
   ├── compose.yaml
   ├── up
   ├── down
   └── wait

bin/
└── sqlitch

etc/
└── templates/
```

**Structure Decision**: Preserve the single-repo CLI layout anchored at `sqlitch/`, mirroring Sqitch’s directory structure so documentation, tests, and tooling align 1:1 with the upstream reference.

## Phase 0: Outline & Research
1. Consolidated prior investigations into `research.md`, covering language/tooling decisions, packaging layout, registry connectors, credential precedence, Docker harness behavior, timestamp parity, and the new stub adapter requirement.
2. No additional research agents are required; existing documentation captures rationale and alternatives for each dependency.
3. Updated “Multi-Engine Framework Proof for M1” and performance follow-up notes ensure there are no outstanding NEEDS CLARIFICATION markers.

**Output**: `research.md` (updated) – COMPLETE

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. `data-model.md` captures entities (Change, Plan, Tag, RegistryRecord, EngineTarget, ConfigProfile) with invariants, scale assumptions, and lifecycle flows consistent with the spec.
2. `/contracts/*.md` mirror Sqitch CLI behaviors for each command, providing the basis for skipped contract tests that will be unskipped during implementation.
3. Regression and contract tests already exist (skipped where required) and align with FR-012 for the Red→Green workflow.
4. `quickstart.md` now emphasizes the SQLite MVP, optional Docker harness for skip verification, and stub adapter expectations.
5. Ran `.specify/scripts/bash/update-agent-context.sh copilot` to refresh the agent context with up-to-date technology references.

**Output**: `data-model.md`, `/contracts/*`, `quickstart.md`, agent context – COMPLETE

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P] 
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation 
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |


## Progress Tracking
*This checklist is updated during execution flow*

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
- [x] Complexity deviations documented

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
