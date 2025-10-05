# Feature Specification: Complete Sqitch Command Surface Parity

**Feature Branch**: `[003-ensure-all-commands]`  
**Created**: 2025-10-05  
**Status**: Draft  
**Input**: User description: "ensure all commands from sqitch are available for sqlitch"

## Execution Flow (main)
```
1. Audit the Sqitch command surface from sqitchcommands.pod to identify all commands
2. Verify that each Sqitch command has a corresponding SQLitch CLI module
3. Document the complete command inventory with parity requirements
4. Ensure each command accepts the same arguments, options, and flags as Sqitch
5. Validate that help text, usage messages, and error outputs match Sqitch formatting
6. Confirm that stub implementations (commands not yet fully implemented) are properly marked and tested
7. Define acceptance criteria for each command's parity status
```

---

## ⚡ Quick Guidelines
- SQLitch MUST expose all Sqitch commands with identical CLI signatures to maintain drop-in compatibility
- Command help text and usage messages MUST match Sqitch formatting to avoid breaking existing automation
- Stub implementations (not yet feature-complete) MUST accept all expected arguments without error and emit clear "not implemented" messages
- Each command MUST validate its arguments and options exactly as Sqitch does (same error messages for invalid inputs)
- Global options (`--chdir`, `--no-pager`, `--quiet`, `--verbose`) MUST be supported consistently across all commands
- Exit codes MUST match Sqitch behavior (0 for success, 1 for user error, 2 for system error)
- Reference the Constitution Principle V: default output stays human-readable without structured log noise unless opted in via explicit flags

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
Database release engineers and automation scripts need SQLitch to expose the complete Sqitch command surface so existing workflows, documentation, and tooling continue to function without modification.

### Acceptance Scenarios
1. **Given** a user runs `sqlitch help` or `sqlitch --help`, **When** the help output is displayed, **Then** it MUST list all 19 Sqitch commands (add, bundle, checkout, config, deploy, engine, help, init, log, plan, rebase, revert, rework, show, status, tag, target, upgrade, verify) with descriptions matching Sqitch.

2. **Given** a user invokes any SQLitch command with `--help` (e.g., `sqlitch deploy --help`), **When** the command-specific help is displayed, **Then** it MUST show the same options, arguments, and usage patterns as the equivalent Sqitch command.

3. **Given** a user runs a fully implemented SQLitch command with valid arguments, **When** the command executes, **Then** it MUST produce output, exit codes, and side effects identical to Sqitch for the same inputs.

4. **Given** a user runs a stub SQLitch command (not yet feature-complete) with valid arguments, **When** the command executes, **Then** it MUST accept the arguments without error, emit a clear "not implemented" message, and exit with code 1.

5. **Given** a user runs any SQLitch command with invalid arguments or options, **When** the command validates its inputs, **Then** it MUST emit the same error messages and exit codes as Sqitch for the same invalid inputs.

6. **Given** a user invokes a SQLitch command with global options (`--chdir`, `--no-pager`, `--quiet`, `--verbose`), **When** the command executes, **Then** it MUST honor those options consistently across all commands as Sqitch does.

### Edge Cases
- How does SQLitch behave when a user misspells a command name (e.g., `sqlitch depoy` instead of `sqlitch deploy`)?
- What happens when a user tries to run a command in a directory without a SQLitch/Sqitch project?
- How does the system respond when a command is invoked with conflicting global options (e.g., `--quiet --verbose`)?
- What error message appears when a command expects a target but none is provided?
- How does SQLitch handle commands that depend on features not yet implemented (e.g., `checkout` depending on VCS integration)?

## Requirements *(mandatory)*

### Functional Requirements

#### Core Command Surface
- **FR-001**: SQLitch MUST implement all 19 Sqitch commands identified in sqitchcommands.pod: `add`, `bundle`, `checkout`, `config`, `deploy`, `engine`, `help`, `init`, `log`, `plan`, `rebase`, `revert`, `rework`, `show`, `status`, `tag`, `target`, `upgrade`, `verify`.

- **FR-002**: Each SQLitch command MUST accept the same positional arguments, required options, and optional flags as its Sqitch equivalent, validating inputs with identical error messages and exit codes.

- **FR-003**: Command help output (invoked via `sqlitch <command> --help`) MUST match Sqitch formatting, including synopsis, description, options list, and examples where applicable.

- **FR-004**: The global help command (`sqlitch help` and `sqlitch --help`) MUST list all available commands with descriptions matching sqitchcommands.pod.

#### Global Options
- **FR-005**: All SQLitch commands MUST support the global options `--chdir <path>`, `--no-pager`, `--quiet`, and `--verbose`, implementing behavior identical to Sqitch.

- **FR-006**: When conflicting global options are provided (e.g., `--quiet` and `--verbose`), SQLitch MUST follow Sqitch's precedence rules and emit the same warnings or errors.

#### Exit Codes
- **FR-007**: SQLitch commands MUST use the same exit code conventions as Sqitch: 0 for success, 1 for user errors (invalid arguments, configuration issues, operational failures), and 2 for system errors (database unavailable, missing dependencies, internal failures).

#### Stub Command Behavior
- **FR-008**: Commands that are implemented as stubs (not yet feature-complete) MUST accept all expected arguments and options without error, emit a clear message indicating the command is not yet implemented, and exit with code 1.

- **FR-009**: Stub implementations MUST validate their arguments and options as if they were fully implemented, rejecting invalid inputs with appropriate error messages before emitting the "not implemented" notice.

#### Command-Specific Requirements
- **FR-010**: The `add` command MUST generate change scripts with filenames matching the change name (no timestamp prefixes), following the layout `{deploy,revert,verify}/<change-name>.sql`.

- **FR-011**: The `bundle` command MUST package a SQLitch project for distribution, including plan file, change scripts, and configuration.

- **FR-012**: The `checkout` command MUST coordinate VCS operations with SQLitch state management (revert, branch switch, redeploy).

- **FR-013**: The `config` command MUST manage local, user, and system configuration scopes, honoring Sqitch-compatible config file locations and supporting both `sqitch.*` and `sqlitch.*` namespaces.

- **FR-014**: The `deploy` command MUST apply pending changes to the target database, recording registry metadata and respecting transaction boundaries.

- **FR-015**: The `engine` command MUST manage engine-specific configuration for SQLite, MySQL, PostgreSQL, and provide clear errors for unsupported engines.

- **FR-016**: The `help` command MUST display command help, conceptual guides, and tutorial links matching Sqitch's help system.

- **FR-017**: The `init` command MUST initialize a new SQLitch project, creating directory structure, plan file, and default configuration.

- **FR-018**: The `log` command MUST display deployment history from the registry, supporting filtering and formatting options.

- **FR-019**: The `plan` command MUST display the deployment plan with changes, tags, and dependencies.

- **FR-020**: The `rebase` command MUST revert and redeploy changes in a single operation, maintaining registry consistency.

- **FR-021**: The `revert` command MUST roll back deployed changes, executing revert scripts and updating registry state.

- **FR-022**: The `rework` command MUST duplicate an existing change for modification, generating new scripts with `_rework` suffix.

- **FR-023**: The `show` command MUST display information about changes, tags, and script contents, supporting multiple output formats.

- **FR-024**: The `status` command MUST report the current deployment state, comparing plan to registry and identifying pending or undeployed changes.

- **FR-025**: The `tag` command MUST add or list tags in the plan, supporting tag dependencies and annotations.

- **FR-026**: The `target` command MUST manage target database configurations, including connection strings and engine-specific settings.

- **FR-027**: The `upgrade` command MUST migrate the registry schema to the current version, preserving existing deployment history.

- **FR-028**: The `verify` command MUST execute verification scripts to confirm deployed changes meet expectations.

#### Testing & Validation
- **FR-029**: Each command MUST have contract tests that validate argument parsing, option handling, and error messaging against Sqitch behavior.

- **FR-030**: Regression tests MUST confirm that command outputs (stdout, stderr, exit codes) match Sqitch for equivalent invocations.

- **FR-031**: The test suite MUST exercise all commands with valid inputs, invalid inputs, and missing required arguments to ensure error handling parity.

### Key Entities *(include if feature involves data)*
- **Command Module**: Represents a SQLitch CLI command implementation with argument parsing, validation, execution logic, and help text.
- **Command Registry**: The central inventory of available commands loaded from `sqlitch/cli/commands/`, exposed through the CLI dispatcher.
- **Global Options**: Configuration flags (`--chdir`, `--no-pager`, `--quiet`, `--verbose`) that must be consistently handled across all commands.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (none found)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed

---
