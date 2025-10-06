
# Implementation Plan: Complete Sqitch Command Surface Parity

**Branch**: `003-ensure-all-commands` | **Date**: 2025-10-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/poecurt/projects/sqlitch-v3/specs/003-ensure-all-commands/spec.md`

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
Ensure all 19 Sqitch commands are available in SQLitch with complete CLI signature parity, proper argument validation, consistent help output, and appropriate stub implementations for commands not yet feature-complete. This feature focuses on command surface completeness rather than full implementation, ensuring existing automation and workflows see a consistent CLI interface.

**Primary Requirement**: All SQLitch commands must accept the same arguments, options, and global flags as their Sqitch equivalents, validate inputs identically, and provide matching help text.

**Technical Approach**: Audit existing command modules against Sqitch documentation (sqitchcommands.pod), verify argument parsing patterns are consistent across all commands, ensure stub implementations properly validate arguments before emitting "not implemented" messages, and add contract tests to prevent CLI signature drift.

## Technical Context
**Language/Version**: Python 3.9+  
**Primary Dependencies**: Click (CLI framework), pytest (testing)  
**Storage**: N/A (command interface layer only)  
**Testing**: pytest with Click's CliRunner for contract tests  
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows)
**Project Type**: Single project (CLI tool)  
**Performance Goals**: Instant command parsing (<10ms), help text retrieval (<50ms)  
**Constraints**: Must maintain 1:1 Sqitch CLI parity, no breaking changes to existing command signatures  
**Scale/Scope**: 19 commands with ~150 total options/flags across all commands

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check (Pre-Research)

- **Test-First Development**: ✅ PASS
  - All contract tests will be written before implementation changes
  - Task ordering: Contract tests → Audits → Fixes → Validation
  - Each command gets a failing contract test before any CLI changes

- **Observability & Determinism**: ✅ PASS
  - Feature focuses on CLI signatures, not logging behavior
  - No changes to structured logging or observability infrastructure
  - Maintains existing opt-in logging principles

- **Behavioral Parity**: ✅ PASS
  - All contracts derived from Sqitch documentation (pod files)
  - Help text must match pod documentation structure
  - Argument validation must match Sqitch behavior
  - Exit codes follow Sqitch conventions (0/1/2)

- **Simplicity-First**: ✅ PASS
  - Minimal change: ensure command signatures match Sqitch
  - No new commands, no new features, only parity enforcement
  - Audit → Fix approach avoids over-engineering
  - Rejected alternatives: Complete reimplementation (too complex)

- **Documented Interfaces**: ✅ PASS
  - Contract specifications document expected CLI behavior
  - Help text serves as user-facing documentation
  - No library API changes (CLI layer only)

### Post-Design Check (After Phase 1)

- **Test-First Development**: ✅ PASS
  - Contract test specifications complete in `/contracts/`
  - 19 command contracts defined
  - 5 global contracts defined (cross-command)
  - Task plan ensures tests written before fixes

- **Observability & Determinism**: ✅ PASS
  - No observability changes in design
  - CLI behavior remains deterministic (same inputs → same outputs)

- **Behavioral Parity**: ✅ PASS
  - All contracts reference Sqitch pod files
  - Quickstart scenarios validate parity
  - No intentional deviations documented (pure parity feature)

- **Simplicity-First**: ✅ PASS
  - Design is straightforward: test → audit → fix → validate
  - No complex abstractions introduced
  - Leverages existing Click framework patterns
  - ~35-40 simple, independent tasks

- **Documented Interfaces**: ✅ PASS
  - Contract specifications serve as API documentation
  - Quickstart provides user-facing validation scenarios
  - Help text updates (if any) maintain Sqitch compatibility

### Conclusion
No constitutional violations detected. Feature aligns with all principles.

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
│   ├── commands/         # All 19 command implementations
│   │   ├── add.py
│   │   ├── bundle.py
│   │   ├── checkout.py
│   │   ├── config.py
│   │   ├── deploy.py
│   │   ├── engine.py
│   │   ├── help.py
│   │   ├── init.py
│   │   ├── log.py
│   │   ├── plan.py
│   │   ├── rebase.py
│   │   ├── revert.py
│   │   ├── rework.py
│   │   ├── show.py
│   │   ├── status.py
│   │   ├── tag.py
│   │   ├── target.py
│   │   ├── upgrade.py
│   │   └── verify.py
│   ├── options.py        # Global options (--chdir, --quiet, --verbose)
│   └── main.py           # CLI dispatcher

tests/
├── cli/
│   └── commands/         # Contract tests for each command
│       ├── test_add.py
│       ├── test_bundle.py
│       ├── test_checkout.py
│       ├── test_config.py
│       ├── test_deploy.py
│       ├── test_engine.py
│       ├── test_help.py
│       ├── test_init.py
│       ├── test_log.py
│       ├── test_plan.py
│       ├── test_rebase.py
│       ├── test_revert.py
│       ├── test_rework.py
│       ├── test_show.py
│       ├── test_status.py
│       ├── test_tag.py
│       ├── test_target.py
│       ├── test_upgrade.py
│       └── test_verify.py
└── regression/
    └── test_command_parity.py  # Cross-command consistency tests

sqitch/                   # Reference Perl implementation
└── lib/
    └── sqitch*.pod       # Command documentation source
```

**Structure Decision**: Single project structure (Option 1). This is a CLI tool with command modules under `sqlitch/cli/commands/` and corresponding contract tests under `tests/cli/commands/`. The feature focuses on the CLI layer only, not the underlying engine implementations.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
1. **Load task template**: Use `.specify/templates/tasks-template.md` as base
2. **Generate from contracts**: Create contract test tasks for each command
   - Each command contract (19 total) → one contract test task
   - Mark [P] for parallel execution (commands are independent)
3. **Generate audit tasks**: Create tasks to audit existing implementations
   - Global options audit task (check all commands)
   - Exit code audit task (verify 0/1/2 consistency)
   - Stub validation audit task (ensure stubs validate args)
4. **Generate fix tasks**: Create implementation tasks for gaps found during audits
   - Add missing global option support
   - Fix exit code inconsistencies
   - Improve stub argument validation
5. **Generate validation tasks**: Create tasks to run quickstart scenarios
   - Command discovery validation
   - Help text validation
   - Required argument enforcement validation

**Ordering Strategy**:
1. **Test-First**: All contract test tasks before implementation tasks
2. **Audit-First**: Audit tasks before fix tasks (need to find gaps first)
3. **Dependency Order**:
   - Contract tests (Phase 1) - can run in parallel [P]
   - Audit tasks (Phase 2) - sequential, build on each other
   - Fix tasks (Phase 3) - depend on audit findings
   - Validation tasks (Phase 4) - run quickstart after fixes

**Estimated Task Breakdown**:
- Contract tests: 19 tasks (one per command) [P]
- Global contract tests: 5 tasks (help, global options, exit codes, errors, unknown options) [P]
- Audit tasks: 3 tasks (global options, exit codes, stub validation)
- Fix tasks: Variable (depends on audit findings, estimate 5-10)
- Validation tasks: 8 tasks (one per quickstart scenario)
- **Total**: ~35-40 tasks

**Test Execution Order** (TDD):
```
Phase 1: Write Contract Tests (Tasks T001-T024)
  - T001-T019: Individual command contract tests [P]
  - T020-T024: Cross-command contract tests [P]
  
Phase 2: Run Audits (Tasks T025-T027)
  - T025: Audit global options support
  - T026: Audit exit code usage
  - T027: Audit stub argument validation
  
Phase 3: Implement Fixes (Tasks T028-T03X)
  - T028: Add missing global options
  - T029: Fix exit code inconsistencies
  - T030: Improve stub validation
  - T03X: Additional fixes based on audit
  
Phase 4: Validate (Tasks T03Y-T040)
  - Run quickstart scenarios
  - Confirm all contract tests pass
  - Update documentation
```

**Complexity Note**: This feature has many tasks but low complexity per task. Each command contract test is simple and independent. The audit tasks are straightforward code inspection. Fix tasks should be small, targeted changes.

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
- [x] Complexity deviations documented (none needed)

---
*Based on Constitution v1.7.0 - See `/memory/constitution.md`*
