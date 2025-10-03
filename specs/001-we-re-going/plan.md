
# Implementation Plan: SQLitch Python Parity Fork MVP

**Branch**: `[001-we-re-going]` | **Date**: 2025-10-03 | **Spec**: [`specs/001-we-re-going/spec.md`](../../specs/001-we-re-going/spec.md)
**Input**: Feature specification from `/specs/001-we-re-going/spec.md`

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
Rebuild Sqitch as a Python-first CLI named SQLitch that delivers drop-in behavioral parity for SQLite, MySQL, and PostgreSQL projects. The new tool will reuse Sqitch’s directory and testing layout, while implementing the command surface with Click, enforcing 90%+ coverage, and running Docker-backed integration tests whenever containers are available. Parity verification compares SQLitch outputs against repository-managed golden fixtures that were generated from Sqitch ahead of time; the automated test suite itself never invokes Sqitch.

## Technical Context
**Language/Version**: Python 3.11 (CPython)  
**Primary Dependencies**: Click (CLI), Rich (structured console output), SQLAlchemy core for plan parsing, sqlite3 stdlib, `psycopg[binary]`, `mysqlclient`, `python-dateutil`, `tomli`, `pydantic` for config validation, packaging extras for Docker orchestration (`docker` SDK)  
**Storage**: SQLite (stdlib driver), MySQL (Docker: mysql:8), PostgreSQL (Docker: postgres:15); Sqitch registry stored via same engines  
**Testing**: pytest + pytest-cov, hypothesis (property coverage for plan semantics), tox for matrix, Docker Compose harness for engines  
**Target Platform**: Cross-platform CLI (macOS, Linux, Windows) running in terminals with optional container runtime  
**Project Type**: Single CLI/service package with mirrored Sqitch layout  
**Performance Goals**: CLI invocations complete <200ms for non-deploy commands; deployments stream progress; parity with Sqitch output  
**Constraints**: 90%+ coverage, zero lint/type/security warnings (black, isort, flake8, pylint, mypy, bandit), deterministic outputs matching Sqitch, Docker tests skip-with-warning if unavailable  
**Scale/Scope**: MVP limited to SQLite, MySQL, PostgreSQL; feature parity with Sqitch core command set; ready for multi-platform CI matrix

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Test-First Development**: Plan mandates pytest-first workflow, contract specs, and dockerized integration suites before implementation → **PASS**
- **CLI-First, Text I/O Contracts**: Click-based CLI mirrors Sqitch outputs, ensures JSON mode parity, and enforces deterministic stdout/stderr → **PASS**
- **Library-First Modules**: Core logic resides in importable `lib/sqlitch` modules with thin CLI wrapper; no business logic in entry script → **PASS**
- **Sqitch Behavioral Parity**: Research and contracts replicate Sqitch command semantics, timestamp formatting, and plan mutation rules → **PASS (tracked via parity reports)**
- **Simplicity & Non-Duplication**: Reuse shared abstractions for engines; forbid unnecessary features beyond Sqitch scope → **PASS**
- **AI Enablement**: Internal tooling (agents, CI bots) configured per current automation defaults; no constitution-mandated assistant → **PASS**

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
├── pyproject.toml
├── README.md
├── Changes
├── bin/
│   └── sqlitch            # Click entry script invoking library CLI shim
├── lib/
│   └── sqlitch/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py     # Click group + command wiring
│       │   └── options.py
│       ├── engine/
│       │   ├── base.py
│       │   ├── sqlite.py
│       │   ├── mysql.py
│       │   └── postgres.py
│       ├── plan/
│       │   ├── parser.py
│       │   └── formatter.py
│       ├── config/
│       │   ├── loader.py
│       │   └── resolver.py
│       ├── registry/
│       │   ├── state.py
│       │   └── migrations.py
│       └── utils/
│           ├── fs.py
│           └── time.py
├── etc/
│   ├── templates/
│   └── tools/
├── docs/
├── tests/
│   ├── cli/
│   ├── engine/
│   ├── plan/
│   ├── regression/
│   ├── support/
│   ├── unit/
│   └── fixtures/
├── xt/
│   └── nightly/
└── scripts/
      └── docker-compose/    # Engine harness definitions
```

**Structure Decision**: Mirror Sqitch’s `bin/`, `lib/`, `etc/`, and `xt/` directories under a new `sqlitch/` root while implementing Python modules inside `lib/sqlitch`. Create a sibling top-level `tests/` directory (next to `sqlitch/`) that mirrors the former Sqitch `t/` layout via subpackages (cli/, engine/, plan/, regression/, support/, unit/, fixtures/). Nightly/extended cases remain in `xt/`. Supporting scripts and packaging metadata live at the root to integrate with Python tooling while honoring the original layout.

## Phase 0: Outline & Research
1. Investigate Sqitch Perl internals for command workflows, plan file semantics, registry schema, and template expansion rules that must be mirrored in Python.
2. Validate Python ecosystem choices: compare `psycopg[binary]` vs `asyncpg`, `mysqlclient` vs `PyMySQL`, and confirm Click patterns for nested command trees that match Sqitch help text.
3. Prototype Docker orchestration scripts to spin up SQLite (in-memory), MySQL, and PostgreSQL containers with deterministic seed data and timestamp controls.
4. Document findings in `research.md` (decision, rationale, alternatives) with links back to Sqitch source references.

**Output**: `research.md` capturing parity rules, dependency selections, Docker strategy, and testing conventions.

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. Derive core domain entities (Change, Plan, Tag, RegistryRecord, EngineTarget) and interactions → capture schemas, invariants, and lifecycle diagrams in `data-model.md`.
2. For each CLI command (`add`, `bundle`, `checkout`, `config`, `deploy`, `engine`, `help`, `init`, `log`, `plan`, `rebase`, `revert`, `rework`, `show`, `status`, `tag`, `target`, `upgrade`, `verify`), author command contracts in `/contracts/cli-<command>.md` describing inputs, flags, environment variables, expected stdout/stderr/exit codes, and timestamp formatting rules.
3. Outline pytest skeleton suites under the repository-level `tests/` directory (mirroring the legacy `t/` subdirectories) with Docker-based fixtures; mark each new test as skipped until the corresponding implementation task is ready to start, then—immediately before beginning that implementation—remove the skip so the test fails per FR-012.
4. Produce `quickstart.md` guiding contributors through `python -m venv`, dependency installation, Docker prerequisites, and parity verification steps with references to the `tests/` hierarchy.
5. Update Copilot agent context by running `.specify/scripts/bash/update-agent-context.sh copilot`, appending new tech choices (Click, docker SDK, connectors) while keeping the file concise.

**Output**: `data-model.md`, `/contracts/*`, `quickstart.md`, docker-aware pytest scaffolds (documented), and refreshed Copilot agent file.

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

**Mandatory Test Gate**: Before beginning any implementation task generated in Phase 3.2 (e.g., T036+), engineers MUST remove the corresponding skip markers, confirm the tests fail, and treat that failure as the starting point for the Red→Green→Refactor loop.
- **Automation**: Task T008a creates `scripts/check-skips.py` and wires it into the tox lint stage/CI so pipelines fail if targeted skips remain when implementation begins.
- **Review Checklist**: Task T008b updates the pull request template with a mandatory checkbox confirming the script has passed and skips were removed prior to starting implementation work.

### Engine Implementation Order & Manual Gates
1. Implement the SQLite engine adapter first. After the adapter and its automated tests land (T046), halt feature work to perform manual parity verification, capture findings, and raise a dedicated PR for review and merge before touching other engines.
2. Implement the MySQL engine adapter next (from a fresh branch). Repeat the manual verification + PR/merge cycle immediately after T047 completes so downstream changes cannot pile up.
3. Implement the PostgreSQL engine adapter last (T048) and run the same manual check/merge gate before proceeding to integration tasks.
4. Resume remaining work only after the relevant manual gate has cleared; downstream tasks must treat these pauses as hard stops.

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
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none)

---
*Based on Constitution v1.3.0 - See `.specify/memory/constitution.md`*
