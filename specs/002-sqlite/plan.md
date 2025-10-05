
# Implementation Plan: SQLitch Python Parity Fork MVP

**Branch**: `002-sqlite` | **Date**: 2025-10-05 | **Spec**: [/specs/002-sqlite/spec.md](/specs/002-sqlite/spec.md)
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
Deliver a Python-based fork of Sqitch that provides command-line parity, structured logging, and rigorous quality gates while initially shipping a SQLite-only runtime. The implementation must mirror Sqitch semantics for plan parsing, registry management, and CLI ergonomics, supported by automated parity evidence, multi-engine architecture readiness, and constitution-driven development practices.

## Technical Context
**Language/Version**: Python 3.11 (with `from __future__ import annotations` enforcement)  
**Primary Dependencies**: Click, Rich, SQLAlchemy Core, sqlite3 stdlib, `psycopg[binary]`, PyMySQL, python-dateutil, tomli, pydantic, docker SDK  
**Storage**: SQLite primary (registry in sibling `sqitch.db`), architecture-ready for MySQL/PostgreSQL schemas  
**Testing**: pytest + pytest-cov, CLI contract/regression suites with golden fixtures, docker-backed integration when available  
**Target Platform**: macOS, Linux, and Windows via CI matrix  
**Project Type**: Single CLI/library project (`sqlitch/` package + `tests/`)  
**Performance Goals**: CLI commands should complete typical non-deploy actions in <200 ms; deploy operations stream progression similar to Sqitch  
**Constraints**: ≥90 % coverage, zero lint/type/security warnings, structured logging parity, no secret leakage, registry isolation per engine  
**Scale/Scope**: Supports existing Sqitch-sized projects (multi-target plans, dozens of changes); must remain deterministic for automation pipelines

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Test-First Development**: Plan centers on regenerating contract/regression tests before implementations; skips remain only for unstarted engines, satisfying Red→Green discipline.
- **II. CLI-First Contracts**: All deliverables flow through `sqlitch` CLI parity, maintaining stdout/stderr semantics and JSON toggles.
- **VI. Parity with Sqitch**: Research + contracts explicitly reference upstream `sqitch/` for behavior, including registry separation and plan whitespace.
- **Observability & Security Constraints**: Structured logging, credential handling, and secret redaction align with NFR-001/NFR-002.
- **Additional Constraints**: Type hints, docstrings, minimal global state, and ABC usage are already codified in spec and will be revalidated during design.

✅ Initial Constitution Check: PASS (no deviations identified)

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
```
sqlitch/
├── cli/
│   ├── commands/
│   ├── options.py
│   └── main.py
├── config/
├── engine/
├── plan/
├── registry/
└── utils/

tests/
├── cli/
│   ├── contracts/
│   ├── regression/
│   └── unit helpers
├── engine/
├── plan/
├── registry/
├── scripts/
└── utils/

.github/
└── prompts/, workflows/, guidance files
```

directories captured above]
**Structure Decision**: Adopt existing single-package layout (`sqlitch/` with domain subpackages, `tests/` mirroring commands/engines/plan`) to preserve parity-focused module boundaries and reuse current contract and regression suites.

## Phase 0: Outline & Research
1. **Targeted research backlog** (map to `research.md`):
   - Validate multi-engine registry behavior against upstream Sqitch (schema selection, SQLite `sqitch.db` mirroring).
   - Confirm credential precedence and secure storage expectations (config vs env) from Sqitch docs and Perl source.
   - Catalogue plan formatting nuances (pragma ordering, blank-line separation, timestamp normalization) to drive parser/formatter specs.
   - Document Docker-backed integration requirements and fallback behavior when containers are unavailable.
   - Inventory quality gate tooling configurations (black, isort, flake8, pylint, mypy, bandit, pytest-cov) and any repo-specific overrides.

2. **Dispatch research tasks**:
   ```
   Task: "Research Sqitch registry storage strategy across SQLite/MySQL/PostgreSQL for SQLitch parity"
   Task: "Summarize Sqitch credential handling precedence and redaction expectations"
   Task: "Extract plan formatting rules (pragmas, blank lines, metadata) from Sqitch reference"
   Task: "Detail Docker integration setup and skip semantics for SQLitch tests"
   Task: "List enforcement settings for lint/type/security gates in sqlitch project"
   ```

3. **Record findings** in `research.md`:
   - Decision, Rationale, Alternatives for each topic
   - Link to upstream references (Sqitch docs, Perl modules) where applicable

**Output**: `research.md` updated to capture upstream-aligned behavior and repo tooling expectations

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Model design (`data-model.md`)**:
   - Detail Deployment Plan, Plan Entry (Change/Tag), Registry Record, Engine Target, Log Configuration entities with fields, validation rules, and relationships.
   - Capture registry storage separation (SQLite file vs schema) and credential attributes.
   - Document state transitions (deploy → revert → rework) and checksum expectations.

2. **CLI contract specifications (`contracts/`)**:
   - For each CLI surface (plan/add/deploy/status/log/config/global options), define command synopsis, options, stdout/stderr expectations, JSON payload schema, and structured logging events.
   - Include regression contract for plan whitespace and registry isolation behavior.

3. **Contract tests scaffolding**:
   - Ensure each contract spec has a matching test skeleton referencing existing pytest modules (e.g., extend `tests/cli/contracts/*` with new cases for logging payloads or plan formatting).
   - Tests should intentionally fail until implementation updates align with generated contracts.

4. **Integration scenarios & quickstart**:
   - Map user stories to end-to-end flows (initialize project, add changes, deploy, verify) emphasizing SQLite-first run-through and pointers for future engines.
   - Update `quickstart.md` with deterministic CLI steps, environment setup (`python -m venv`), Docker expectations, and parity validation checkpoints.

5. **Agent context refresh**:
   - Run `.specify/scripts/bash/update-agent-context.sh copilot` after documentation updates.
   - Append only newly introduced technologies or workflow adjustments (<150 lines total).

**Output**: Updated `data-model.md`, refreshed `/specs/002-sqlite/contracts/`, failing-but-documented contract tests, refreshed `quickstart.md`, and synchronized Copilot agent context

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
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

*No constitution deviations currently identified; table intentionally empty.*


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented (N/A)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
