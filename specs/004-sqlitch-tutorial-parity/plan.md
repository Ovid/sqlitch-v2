
# Implementation Plan: SQLite Tutorial Parity

**Branch**: `004-sqlitch-tutorial-parity` | **Date**: 2025-10-08 | **Spec**: [`specs/004-sqlitch-tutorial-parity/spec.md`](spec.md)
**Input**: Feature specification from `specs/004-sqlitch-tutorial-parity/spec.md`

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
Deliver full Sqitch parity for the SQLite tutorial so every documented workflow (`init`, `config`, `add`, `deploy`, `verify`, `status`, `revert`, `log`, `tag`, `rework`, `engine`, `target`) executes with byte-for-byte identical output when run with `sqlitch`. The implementation centers on wiring the existing plan/registry infrastructure into the CLI commands, enforcing the clarified configuration hierarchy and environment-variable precedence, and emitting the compact plan format while recording deploy/revert/verify/fail events exactly as Sqitch does. The feature succeeds when the tutorial can be completed end-to-end using SQLitch with the same files, registry contents, and console output as upstream Sqitch.

## Technical Context
**Language/Version**: Python 3.11 (per `requires-python >=3.11`)
**Primary Dependencies**: Click 8.1 CLI framework, SQLAlchemy 2.x for registry I/O, python-dateutil for timezone-aware parsing, Pydantic 2.x domain models
**Storage**: SQLite registry database co-located with target DB; plan/config/state stored on filesystem
**Testing**: Pytest (strict config), Click `CliRunner`, pytest-randomly, pytest-cov ≥90%
**Target Platform**: Cross-platform CLI on macOS & Linux shells
**Project Type**: Single back-end/CLI project (`sqlitch/` package with tests)
**Performance Goals**: Tutorial deploys <5 seconds for plans <100 changes (FR-003); default CLI interactions remain near-instant (<200ms) when not executing SQL
**Constraints**: Maintain ≥90% coverage (NFR-002), byte-identical default output to Sqitch (NFR-004), honor config/env precedence (FR-001a/FR-005a), structured logging only via flags
**Scale/Scope**: Tutorial-scale plans (~dozens of changes); registry and config must scale to continuous CLI use but feature scope limited to SQLite tutorial flows

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Test-First Development:** Each CLI enhancement will begin by unskipping or adding failing tests under `tests/cli`, `tests/integration`, and `tests/regression` that lock parity with the Sqitch tutorial (e.g., deploy failure recording, config hierarchy, environment variable overrides) before touching implementation modules.
- **Observability & Determinism:** Default command executions will continue emitting only Sqitch-style human output; structured logs remain off unless verbose/json flags trigger existing instrumentation. Registry writes on deploy/revert stay transactional to preserve deterministic histories (FR-010a).
- **Behavioral Parity:** All behaviors are cross-checked against `sqitch/` Perl sources (`App::Sqitch::Command::*`) and tutorial POD. Newly clarified expectations—no `core.uri` entry, precise config scope ordering, and full `SQLITCH_*`/`SQITCH_*` environment coverage—are treated as non-negotiable parity items.
- **Simplicity-First:** Implementation will extend existing helpers (config loader, plan formatter, registry migrations) instead of introducing new abstractions. Any unavoidable complexity (e.g., identity fallback chain) will reuse shared utility modules in `sqlitch/utils` to avoid duplication.
- **Documented Interfaces:** Public-facing modules touched during implementation (`sqlitch.cli.commands.*`, `sqlitch.config.*`, `sqlitch.utils.identity`) will have docstrings updated to reflect environment variable precedence, registry event semantics, and CLI options, keeping docs aligned with behavior.

## Project Structure

### Documentation (this feature)
```
 specs/004-sqlitch-tutorial-parity/
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
│   ├── __init__.py
│   ├── main.py
│   └── commands/
│       ├── __init__.py
│       ├── add.py
│       ├── config.py
│       ├── deploy.py
│       ├── engine.py
│       ├── log.py
│       ├── rework.py
│       ├── revert.py
│       ├── status.py
│       ├── tag.py
│       ├── target.py
│       └── verify.py
├── config/
│   ├── __init__.py
│   ├── loader.py
│   └── resolver.py
├── engine/
│   ├── __init__.py
│   ├── base.py
│   └── sqlite.py
├── plan/
│   ├── __init__.py
│   ├── formatter.py
│   ├── model.py
│   └── parser.py
├── registry/
│   ├── __init__.py
│   └── migrations.py
└── utils/
      ├── __init__.py
      ├── fs.py
      ├── identity.py
      ├── logging.py
      └── time.py

tests/
├── cli/
├── config/
├── integration/
├── plan/
├── registry/
├── regression/
├── scripts/
└── support/

sqitch/                 # Vendored Perl reference implementation
```

**Structure Decision**: Single-package CLI application; all commands and supporting libraries live under `sqlitch/`, with pytest suites mirroring the same module layout for contract, integration, and regression coverage.

## Phase 0: Outline & Research
1. Validate Sqitch’s environment-variable contract (sqitch-environment.pod) to confirm precedence for `SQLITCH_*`/`SQITCH_*` pairs covering target selection, authentication, identity, originating host metadata, editor, and pager (FR-004/FR-005a). Capture authoritative references and expected fallbacks in `research.md`.
2. Document configuration scope resolution, including `SQITCH_CONFIG`, `SQITCH_USER_CONFIG`, and `SQITCH_SYSTEM_CONFIG` overrides, plus merge order system→user→local (FR-001/FR-001a). Verify how Sqitch handles missing files or duplicate entries.
3. Analyze deploy/revert failure handling in `App::Sqitch::Command::deploy` to confirm event recording semantics (FR-010a) and registry transaction boundaries for SQLite; note required SQLAlchemy transaction patterns.
4. Reconcile plan formatter output with compact Sqitch format (FR-019a) ensuring timestamps, planner identity, and tag placement remain parity-consistent; document any gaps between current formatter behavior and desired state.
5. Inventory command outputs in the tutorial (help text, success messages, prompts) to ensure expected stdout/stderr/exit codes are captured as acceptance baselines.

**Output**: `specs/004-sqlitch-tutorial-parity/research.md` refreshed with parity notes on environment precedence, config hierarchy, deploy failure events, plan formatting, and CLI output expectations.

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Data model updates (`data-model.md`)**: Document the registry entities (projects, changes, dependencies, events, tags), config scopes, and plan entries with newly clarified fields—highlight failure event records, identity resolution order, and environment-variable inputs that feed identity/target resolution.
2. **CLI command contracts (`contracts/`)**: For each tutorial-critical command, capture invocation, required options, environment/config inputs, stdout/stderr expectations, prompts, and exit codes. Include explicit notes for config scope writing, deploy failure recording, and verify failure summary (FR-008–FR-016, FR-010a, FR-011a, FR-012a).
3. **Test blueprints**: For every contract, outline the failing test that will be added/unskipped first (CLI regression tests, integration flows, golden comparisons). Ensure deploy/revert/verify tests assert registry contents, log/fail events, and environment variable overrides.
4. **Quickstart path (`quickstart.md`)**: Translate the tutorial scenarios into a condensed walkthrough that exercises config overrides, environment variable precedence, deploy failure handling, and tag/rework flows.
5. **Agent context**: Run `.specify/scripts/bash/update-agent-context.sh copilot` and append any new technologies or decisions (environment variable precedence, config overrides) to keep automation context current.

**Output**: Updated `data-model.md`, refreshed CLI contract specs under `specs/004-sqlitch-tutorial-parity/contracts/`, failing test plans referenced in design docs, `quickstart.md` walkthrough, and synchronized agent context file.

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Derive task list from Phase 1 artifacts: each CLI contract becomes a failing CLI regression/integration test task, followed by implementation tasks to make it pass.
- Data model items yield persistence/identity helper tasks (e.g., environment-variable resolution helper, registry event writer).
- Quickstart scenarios produce end-to-end acceptance test tasks verifying tutorial parity, including config override flows and deploy failure cases.
- Include dedicated tasks for config writer updates (no core.uri, scope overrides), environment variable handling, and plan formatter compact output.

**Ordering Strategy**:
- TDD order: For every command, add failing tests before code; environment variable helpers tested prior to CLI wiring.
- Dependency order: Update configuration/identity helpers before command implementations; registry functions before CLI surfaces that depend on them.
- Mark [P] for parallel execution when tests touch disjoint commands (e.g., `log` vs `verify`).

**Estimated Output**: 28-32 ordered tasks spanning tests, config/env support, command implementations, plan formatter updates, and refactors.

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


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented

---
*Based on Constitution v1.10.1 – see `.specify/memory/constitution.md`*
