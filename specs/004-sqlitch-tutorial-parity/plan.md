
# Implementation Plan: SQLite Tutorial Parity

**Branch**: `004-sqlitch-tutorial-parity` | **Date**: 2025-10-07 | **Spec**: `/Users/poecurt/projects/sqlitch-v3/specs/004-sqlitch-tutorial-parity/spec.md`
**Input**: Feature specification from `/specs/004-sqlitch-tutorial-parity/spec.md`

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
UAT Step 14 exposed a Sqitch parity defect: `sqlitch engine add sqlite flipr_test` rejects target aliases that Sqitch resolves through configuration (`target.<name>.uri`). This plan captures the incremental work to adopt Sqitch’s alias resolution in the engine command family, update documentation and contracts, and ensure tests enforce the new requirement (**FR-022**).

## Technical Context
**Language/Version**: Python 3.11+ (per `requires-python >=3.11`)  
**Primary Dependencies**: Click 8.x CLI stack, SQLAlchemy 2.x registry helpers, Pydantic 2.x for config validation  
**Storage**: SQLite registry + file-based config hierarchy  
**Testing**: Pytest 8.x with Click’s `CliRunner` and coverage gating ≥90%  
**Target Platform**: macOS/Linux terminals (CLI)  
**Project Type**: Single Python package (`sqlitch`) with CLI focus  
**Performance Goals**: Tutorial deploy/revert flows complete in <5 seconds (NFR-003)  
**Constraints**: Human output must remain byte-parity with Sqitch; default logging silent; adopt FR-022 alias rule without regressing existing commands  
**Scale/Scope**: Scope limited to tutorial parity workflows (single developer, local SQLite targets)

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Test-First Development:** Engine alias parity will be codified via new contract/functional tests before adjusting the CLI implementation; plan keeps tests as the forcing function.
- **Observability & Determinism:** No new logging paths introduced; engine command output remains human-readable and quiet in default mode, preserving determinism.
- **Behavioral Parity:** Sqitch’s `_target` alias resolution is the golden source; no deviations planned, and FR-022 documents the parity requirement.
- **Simplicity-First:** Implementation will reuse existing config loaders and avoid duplicating alias resolution logic—extend existing helpers instead of new abstractions.
- **Documented Interfaces:** Contracts README, quickstart scenario, and spec clarifications already updated; plan tracks docstring/help text adjustments alongside code changes.

## Project Structure

### Documentation (this feature)
```
 specs/004-sqlitch-tutorial-parity/
├── plan.md              # /plan command output (this file)
├── research.md          # Phase 0 research log (updated 2025-10-07)
├── data-model.md        # Phase 1 data definitions
├── quickstart.md        # Phase 1 validation script (Scenario 9 added)
├── contracts/           # CLI contract summaries (engine alias note)
└── tasks.md             # /tasks command output (existing, to be regenerated)
```


### Source Code (repository root)
ios/ or android/
```
sqlitch/
├── cli/
│   ├── commands/
│   │   ├── engine.py
│   │   ├── target.py
│   │   └── __init__.py
│   ├── main.py
│   └── options.py
├── config/
│   ├── loader.py
│   └── resolver.py
├── plan/
│   ├── parser.py
│   └── model.py
└── utils/
      └── fs.py

tests/
├── cli/
│   ├── commands/
│   │   ├── test_engine_contract.py
│   │   └── test_target_contract.py
│   └── contracts/
│       └── test_engine_contract.py
└── engine/
      └── test_base.py
```

**Structure Decision**: Single-package CLI project; engine/target behavior lives under `sqlitch/cli/commands/` with pytest coverage in `tests/cli/commands/` and supporting registry logic in `sqlitch/config/` and `sqlitch/utils/`.

## Phase 0: Outline & Research
1. Captured the new ambiguity (engine alias handling) and confirmed Sqitch reference behavior via `App::Sqitch::Command::engine::_target`.
2. Logged the parity requirement and decision trail in `research.md` under “Update 2025-10-07 — Engine Alias Parity”.

**Output**: `/specs/004-sqlitch-tutorial-parity/research.md` now records the alias decision and upstream source.

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. Documented the new tutorial validation flow in `quickstart.md` (Scenario 9) covering target alias and engine registration parity.
2. Extended `contracts/README.md` with the 2025-10-07 engine alias requirement to guide contract and functional test updates.
3. Plan to add failing tests in `tests/cli/contracts/test_engine_contract.py` (and, if needed, functional coverage) that assert alias-based engine additions succeed and unknown aliases raise Sqitch-grade errors before modifying implementation.
4. Run `.specify/scripts/bash/update-agent-context.sh copilot` after updating docs to ensure agent brief includes the alias requirement.

**Output**: Quickstart and contracts artifacts updated with alias workflow; tests scheduled to encode the requirement.

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
| _None_ | — | — |


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
*Based on Constitution v1.10.1 - See `/memory/constitution.md`*
