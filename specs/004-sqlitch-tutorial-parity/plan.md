
# Implementation Plan: SQLite Tutorial Parity

**Branch**: `004-sqlitch-tutorial-parity` | **Date**: 2025-10-06 | **Spec**: [spec.md](spec.md)
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

Feature 004 implements the minimum command functionality required to complete the Sqitch SQLite tutorial end-to-end. The goal is to enable database developers to follow the tutorial using `sqlitch` instead of `sqitch`, achieving identical results and outputs.

**Primary Requirement**: Implement 10 tutorial-critical commands (init, config, add, deploy, verify, status, revert, log, tag, rework) with sufficient functionality to complete all tutorial workflows.

**Configuration Management**: SQLitch must support hierarchical configuration (system/user/local scopes), INI format matching Sqitch conventions, and user identity resolution from config files with environment variable fallback (SQLITCH_* preferred over SQITCH_* for backward compatibility).

**Technical Approach** (from research.md):
- 80% of infrastructure already exists (plan parsing, config loading, registry schema, engine adapter, command scaffolding)
- Need to implement command-specific business logic (~2,500 lines across 8 commands)
- Two commands are ~80% complete (init, add), eight need implementation
- Foundation provides excellent patterns to follow
- Estimated 4-5 weeks total implementation time

**Implementation Order** (tutorial-driven):
- Follow command sequence from `sqitch/lib/sqitchtutorial-sqlite.pod` (1,253 lines)
- Implement in tutorial order: init → config → add → deploy → verify/status → revert/log → tag/rework
- Manual UAT validation after each checkpoint before proceeding
- Ensures behavioral parity with real Sqitch usage patterns
- See tasks.md "Tutorial Implementation Order" section for detailed checkpoints

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: Click (CLI framework), sqlite3 (stdlib database), pytest (testing)  
**Storage**: SQLite databases (target DBs + sqitch.db registry sibling)  
**Testing**: pytest with pytest-cov (≥90% coverage required), contract tests, integration tests  
**Target Platform**: macOS and Linux (Python 3.11+)  
**Project Type**: Single project (CLI tool with library backend)  
**Performance Goals**: <5 seconds for plans with <100 changes, <200ms for typical commands  
**Constraints**: Default output must match Sqitch byte-for-byte (excluding timestamps), structured logging only with flags  
**Scale/Scope**: 10 commands to implement, 2,500 lines of business logic, full tutorial completion

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Initial Check Results** (before research):

- **Test-First Development:** ✅ PASS
  - All 10 commands already have contract tests validating CLI signatures (Feature 003)
  - Will add functional tests for each command implementation in tasks.md
  - Following Red→Green→Refactor: tests before implementation

- **Observability & Determinism:** ✅ PASS
  - Default CLI output matches Sqitch (human-readable, no structured logs)
  - Structured logging infrastructure exists but only active with `--verbose`, `--json` flags
  - Registry events stored in events table (opt-in audit trail)

- **Behavioral Parity:** ✅ PASS
  - Feature references sqitchtutorial-sqlite.pod (1,253 lines) as authoritative source
  - All workflows derived from tutorial examples
  - No intentional deviations documented (will match Sqitch 1:1)

- **Simplicity-First:** ✅ PASS
  - Implementing minimum functionality to complete tutorial only
  - Not adding features beyond Sqitch
  - Reusing existing infrastructure (80% complete)
  - Estimated 2,500 lines across 8 commands (justified by tutorial requirements)

- **Documented Interfaces:** ✅ PASS
  - All new models will include docstrings (documented in data-model.md)
  - Public APIs will follow existing patterns (Change.create, etc.)
  - Will update .github/copilot-instructions.md with Feature 004 status

**Post-Design Check** (after Phase 1): ✅ PASS

All constitution principles maintained:

- **Test-First Development:** ✅ PASS
  - data-model.md defines all entities with validation rules
  - quickstart.md provides 8 test scenarios
  - Will generate TDD tasks in Phase 2 (tests before implementation)
  - All new models will have unit tests before use

- **Observability & Determinism:** ✅ PASS
  - No changes to logging infrastructure
  - All new commands will match Sqitch default output
  - Registry events stored in events table (existing pattern)

- **Behavioral Parity:** ✅ PASS
  - All data models derived from Sqitch registry schema
  - All workflows derived from sqitchtutorial-sqlite.pod
  - No deviations introduced in design

- **Simplicity-First:** ✅ PASS
  - Data model reuses existing infrastructure (Change, Tag, Plan, ConfigProfile, CLIContext)
  - Only 10 new models needed (all justified by commands)
  - No unnecessary abstractions or patterns
  - Helper functions are focused and simple

- **Documented Interfaces:** ✅ PASS
  - All new models documented in data-model.md with docstrings
  - All validation rules specified
  - All relationships documented
  - Implementation guidance clear

**No violations found. Ready to proceed to Phase 2.**

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
sqlitch/                      # Core implementation
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py
│   └── commands/
│       ├── __init__.py
│       ├── _context.py       # CLIContext (existing)
│       ├── _models.py        # NEW: Command-specific models (DeployOptions, etc.)
│       ├── add.py            # ~80% complete, needs dependency validation
│       ├── config.py         # Need get/set operations (~200 lines)
│       ├── deploy.py         # Need full implementation (~500 lines) - MOST COMPLEX
│       ├── init.py           # ~80% complete, needs engine validation
│       ├── log.py            # Need event display (~250 lines)
│       ├── revert.py         # Need logic (~400 lines)
│       ├── rework.py         # Need logic (~400 lines)
│       ├── status.py         # Need queries + formatting (~300 lines)
│       ├── tag.py            # Need management (~300 lines)
│       └── verify.py         # Need execution (~250 lines)
├── config/
│   ├── __init__.py
│   ├── loader.py             # 100% complete (config loading with hierarchy)
│   └── resolver.py           # Need config writing (~200 lines)
├── engine/
│   ├── __init__.py
│   ├── base.py               # 100% complete
│   ├── sqlite.py             # 95% complete (well-tested)
│   └── scripts.py            # NEW: Script models (Script, ScriptResult)
├── plan/
│   ├── __init__.py
│   ├── model.py              # Need helper methods for Plan class
│   ├── parser.py             # 100% complete
│   └── writer.py             # 100% complete
├── registry/
│   ├── __init__.py
│   ├── migrations.py         # 100% complete (schema DDL)
│   └── state.py              # NEW: Registry models (DeployedChange, DeploymentEvent, DeploymentStatus)
└── utils/
    ├── __init__.py
    ├── identity.py           # NEW: UserIdentity resolution (config → env → fallback)
    └── time.py               # 100% complete

tests/                        # Comprehensive test suite
├── cli/
│   └── commands/
│       ├── test_add_functional.py        # NEW: Add command business logic tests
│       ├── test_config_functional.py     # NEW: Config get/set tests
│       ├── test_deploy_functional.py     # NEW: Deploy logic tests
│       ├── test_init_functional.py       # NEW: Init validation tests
│       ├── test_log_functional.py        # NEW: Log display tests
│       ├── test_revert_functional.py     # NEW: Revert logic tests
│       ├── test_rework_functional.py     # NEW: Rework logic tests
│       ├── test_status_functional.py     # NEW: Status query tests
│       ├── test_tag_functional.py        # NEW: Tag management tests
│       └── test_verify_functional.py     # NEW: Verify execution tests
├── integration/
│   └── test_tutorial_workflows.py        # NEW: End-to-end tutorial scenarios
└── regression/
    └── test_tutorial_parity.py           # NEW: Sqitch output comparison tests

specs/004-sqlitch-tutorial-parity/
├── spec.md                   # ✅ Complete
├── quickstart.md             # ✅ Complete
├── README.md                 # ✅ Complete
├── ROADMAP.md                # ✅ Complete
├── research.md               # ✅ Complete
├── data-model.md             # ✅ Complete
├── plan.md                   # This file
├── tasks.md                  # Phase 2 output (created by /tasks command)
└── contracts/                # Phase 1 output (CLI contracts)
```

**Structure Decision**: Single project structure. SQLitch is a CLI tool with a library backend following the existing architecture established in Features 001-003. All command implementations live in `sqlitch/cli/commands/`, domain models in their respective modules (`plan/model.py`, `registry/state.py`), and tests mirror the source structure.

## Phase 0: Outline & Research

**Status**: ✅ COMPLETE

**Completed Research** (research.md, 1,034 lines):

1. **Registry Schema Analysis**: Documented all 6 tables (releases, projects, changes, tags, dependencies, events) with full column definitions, relationships, and SQLite-specific behavior (sibling sqitch.db file)

2. **Existing Infrastructure Assessment**:
   - Plan parsing/writing: 100% complete (parse_plan, write_plan)
   - Config loading: 100% complete (load_config with system/user/local hierarchy)
   - Config writing: Needs implementation (~200 lines)
   - User identity resolution: Implemented with priority chain (config → SQLITCH_*/SQITCH_* → GIT_* → system → fallback)
   - SQLite engine adapter: 95% complete (well-tested)
   - Command scaffolding: 100% complete (all stubs registered)

3. **Command Implementation Status**:
   - init: 80% complete (file generation works, needs engine validation)
   - add: 80% complete (script generation works, needs dependency validation)
   - config: 0% (need get/set operations)
   - deploy: 0% (need ~500 lines - most complex)
   - verify: 0% (need ~250 lines)
   - status: 0% (need ~300 lines)
   - revert: 0% (need ~400 lines)
   - log: 0% (need ~250 lines)
   - tag: 0% (need ~300 lines)
   - rework: 0% (need ~400 lines)

4. **Technical Decisions**:
   - Transaction management: Scripts manage own transactions by default, SQLitch wraps only if needed
   - Change ID generation: SHA1(project + change + timestamp) matching Sqitch
   - Planner/committer identity: From config → env → defaults (priority: config [user] section → SQLITCH_*/SQITCH_* env vars → GIT_* env vars → system USER/USERNAME → generated fallback)
   - Environment variables: SQLITCH_* prefix preferred, SQITCH_* as fallback for Sqitch compatibility
   - Configuration hierarchy: local (./sqitch.conf) overrides user (~/.sqitch/sqitch.conf) overrides system (/etc/sqitch/sqitch.conf)
   - Configuration format: Git config format (INI-style) with 4-space indentation, backslash continuation for multi-line values
   - Registry attachment: ATTACH DATABASE sibling sqitch.db
   - Dependency validation: Check registry before deploy
   - Tag management: In-memory plan updates, write to file
   - Script discovery: Search project templates → config templates → /etc/sqitch
   - Error handling: Clear, actionable messages matching Sqitch conventions

5. **Effort Estimates**:
   - 2 easy commands (config, log): ~5 days
   - 3 medium commands (status, verify, tag): ~10 days
   - 2 complex commands (deploy, revert): ~7 days
   - 1 very complex command (rework): ~5 days
   - Testing and integration: ~5 days
   - **Total**: 4-5 weeks

6. **Risk Analysis**:
   - HIGH: Deploy complexity (transaction management, dependency validation)
   - HIGH: Rework complexity (plan manipulation, @tag suffix handling)
   - MEDIUM: Registry concurrency (SQLite locking)
   - MEDIUM: Config precedence (system/user/local scopes, environment variable fallback)
   - MEDIUM: User identity resolution (multiple fallback sources with precedence)
   - LOW: Script execution errors (well-tested engine adapter)

**Key Findings**:
- Foundation is excellent: 80% of infrastructure already exists
- Just need to implement command business logic (~2,500 lines total)
- All patterns established from existing code
- No architectural changes needed

**Output**: research.md (committed d2c2a3f)

## Phase 1: Design & Contracts
*Prerequisites: research.md complete ✅*

**Status**: ✅ COMPLETE

**Completed Artifacts**:

1. **data-model.md** (10 sections, comprehensive):
   - **Existing Models**: Documented Change, Tag, Plan, ConfigProfile, CLIContext (ready to use)
   - **New Models Defined**: 10 new dataclasses needed:
     - ProjectMetadata (paths and settings)
     - DeployedChange (registry change record)
     - DeploymentEvent (registry event record with committer identity)
     - DeploymentStatus (status summary)
     - CommandResult (standardized results)
     - DeployOptions (deploy command options)
     - RevertOptions (revert command options)
     - Script (script file representation)
     - ScriptResult (script execution result)
     - UserIdentity (user name and email from config/env with precedence chain)
   - **Helper Functions**: generate_change_id(), validate_change_name(), validate_dependencies(), validate_tag_name()
   - **Validation Rules**: All documented with examples
   - **Data Flow Diagrams**: Deploy, status, and add workflows visualized
   - **Database Schema Reference**: All 6 registry tables documented (events table stores committer name/email)
   - **Implementation Notes**: Clear guidance on which modules need new models

2. **quickstart.md** (260 lines, 8 validation scenarios):
   - Scenario 1: Initialize new project
   - Scenario 2: Add first change (users table)
   - Scenario 3: Deploy and verify
   - Scenario 4: Check status
   - Scenario 5: Add dependent change (flips table)
   - Scenario 6: Tag release (v1.0.0-dev1)
   - Scenario 7: Revert changes
   - Scenario 8: View history with log
   - Full automation test script included
   - Success metrics and troubleshooting guide

3. **contracts/** (CLI contracts):
   - All 10 command CLI signatures already validated in Feature 003
   - Contract tests exist in tests/cli/commands/test_*_contract.py
   - 213 contract tests passing (CLI parity established)
   - Will add functional tests for business logic in Phase 2 tasks

4. **Agent context update**: (Next step after Phase 1)

**Design Validation**:
- All entities mapped to implementation modules
- All validation rules defined with examples
- All relationships documented
- Data flows visualized
- Ready for task generation

**Output**: data-model.md ✅, quickstart.md ✅, contracts/ (existing) ✅

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Model Creation Tasks** (from data-model.md):
   - Create `sqlitch/registry/state.py` with DeployedChange, DeploymentEvent, DeploymentStatus
   - Create `sqlitch/cli/commands/_models.py` with CommandResult, DeployOptions, RevertOptions
   - Create `sqlitch/engine/scripts.py` with Script, ScriptResult
   - Create `sqlitch/utils/identity.py` with UserIdentity
   - Add helper methods to `sqlitch/plan/model.py` (Plan.get_changes, Plan.find_change, etc.)
   - Each task: Write test first → Implement model → Verify test passes

2. **Helper Function Tasks** (from data-model.md):
   - Create validation functions in appropriate modules
   - generate_change_id() in sqlitch/utils/
   - validate_change_name(), validate_dependencies(), validate_tag_name() in sqlitch/plan/
   - Each task: Write test first → Implement function → Verify test passes

3. **Command Implementation Tasks** (10 commands, ordered by complexity):
   - **Simple** (5 days): config, log
   - **Medium** (10 days): status, verify, tag
   - **Complex** (7 days): deploy, revert
   - **Very Complex** (5 days): rework
   - **Finalization** (2 days): init (complete), add (complete)
   
4. **Integration Test Tasks** (from quickstart.md):
   - One integration test per quickstart scenario (8 scenarios)
   - Tests run full workflows end-to-end
   - Compare outputs with expected results
   - All scenarios must pass before feature complete

**Ordering Strategy**:
1. Foundation first: Create all models and helpers (enables parallel work)
2. TDD order: Tests before implementation for each command
3. Dependency order: Simple commands → Medium → Complex
   - config first (needed by other commands for identity resolution)
   - status second (needed to validate deploy/revert)
   - deploy/verify/revert core (most critical functionality)
   - log/tag/rework (build on deploy/revert)
4. Integration tests last (validate complete workflows)
5. Mark [P] for parallel execution (independent tasks)

**Task Categories**:
- **Foundation** (~8 tasks): Models, helpers, validation
- **Core Commands** (~20 tasks): 10 commands × (test + implementation)
- **Integration** (~8 tasks): One per quickstart scenario
- **Documentation** (~2 tasks): Update docs, final review

**Estimated Output**: ~40 numbered, ordered tasks in tasks.md

**Test Coverage Target**: ≥90% (constitution requirement)

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

**No violations found.** All design decisions align with constitutional principles:

- **Simplicity**: Using existing infrastructure (80% complete), only implementing tutorial-required functionality
- **Test-First**: All tasks will follow TDD (tests before implementation)
- **Parity**: All behavior derived from sqitchtutorial-sqlite.pod (1,253 lines)
- **Documentation**: All new models documented in data-model.md with docstrings
- **Observability**: Default output matches Sqitch, structured logging opt-in only

**Justifications** (for context, not violations):

| Design Decision | Rationale | Alignment |
|-----------------|-----------|-----------|
| 10 new models needed | Each model maps to a specific command need or registry entity | Constitutional: Necessary for tutorial completion, no duplication |
| ~2,500 lines of command logic | Minimal to complete tutorial workflows, matches Sqitch complexity | Constitutional: Tutorial-required, not adding extra features |
| Deploy command most complex (~500 lines) | Transaction management, dependency validation, registry updates | Constitutional: Core Sqitch functionality, cannot simplify further |
| Rework command complex (~400 lines) | Plan manipulation, @tag suffix handling, script copying | Constitutional: Tutorial demonstrates rework, must match Sqitch |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) - research.md committed (d2c2a3f)
- [x] Phase 1: Design complete (/plan command) - data-model.md complete, quickstart.md exists
- [x] Phase 2: Task planning complete (/plan command - approach described)
- [ ] Phase 3: Tasks generated (/tasks command) - Ready to execute
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (no violations)
- [x] Post-Design Constitution Check: PASS (no violations)
- [x] All NEEDS CLARIFICATION resolved (spec.md Session 2025-10-06)
- [x] Complexity deviations documented (none required - all justified by tutorial needs)

**Artifact Status**:
- [x] spec.md (372 lines, all clarifications resolved, FR-001 through FR-021 defined)
- [x] research.md (1,034 lines, comprehensive analysis)
- [x] data-model.md (complete, 10 new models defined)
- [x] quickstart.md (260 lines, 8 scenarios)
- [x] README.md (212 lines)
- [x] ROADMAP.md (252 lines)
- [x] plan.md (this file - complete, updated with config requirements)
- [ ] tasks.md (next: /tasks command)

**Next Action**: Run `/tasks` command to generate tasks.md from Phase 1 design artifacts

---
*Based on Constitution v1.7.0 - See `/memory/constitution.md`*
