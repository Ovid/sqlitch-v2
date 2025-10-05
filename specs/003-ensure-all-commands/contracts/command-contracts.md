# Command Contract Specifications

**Date**: 2025-10-05  
**Feature**: 003-ensure-all-commands

## Overview
These contract specifications define the expected CLI behavior for each SQLitch command. Each command has a corresponding contract test file that validates its signature, help output, argument validation, and error handling.

## Contract Testing Principles

1. **Black Box Testing**: Tests invoke commands via `CliRunner`, treating the CLI as an opaque interface
2. **No Mocks**: Tests use real CLI entry points, not mocked internals
3. **Sqitch Parity**: Expected behaviors derived from Sqitch documentation and observed behavior
4. **TDD Ready**: Contracts written before implementation changes, tests should fail initially

## Global Contract (All Commands)

### GC-001: Help Flag Support
**Given** any SQLitch command  
**When** invoked with `--help`  
**Then** it must:
- Exit with code 0
- Print help text to stdout
- Include command name in first line
- Include synopsis/usage line
- List all options with descriptions
- Not execute the command's main logic

### GC-002: Global Options Recognition
**Given** any SQLitch command  
**When** invoked with global options (`--chdir`, `--no-pager`, `--quiet`, `--verbose`)  
**Then** it must:
- Accept the options without error
- Not fail due to "unknown option"
- Apply the option semantics (may be no-op for stubs)

### GC-003: Exit Code Convention
**Given** any SQLitch command  
**When** it completes execution  
**Then** it must exit with:
- 0 for successful operation
- 1 for user errors (bad arguments, expected failures)
- 2 for system errors (database unavailable, internal errors)

### GC-004: Error Output Channel
**Given** any SQLitch command  
**When** an error occurs  
**Then** it must:
- Write error messages to stderr
- Not write errors to stdout
- Include descriptive error message
- Exit with non-zero code

### GC-005: Unknown Option Rejection
**Given** any SQLitch command  
**When** invoked with an unknown option (e.g., `--nonexistent`)  
**Then** it must:
- Exit with code 2 (Click's default for bad options)
- Print error message to stderr mentioning the unknown option
- Not execute the command's main logic

## Command-Specific Contracts

### add Command (CC-ADD)

#### CC-ADD-001: Required Change Name
**Given** `sqlitch add` without arguments  
**When** executed  
**Then** it must:
- Exit with code 2
- Print error indicating missing change_name

#### CC-ADD-002: Valid Change Name
**Given** `sqlitch add my_change`  
**When** executed  
**Then** it must:
- Accept the command without parsing error
- Either create change files (if implemented) or report "not implemented"

#### CC-ADD-003: Optional Note
**Given** `sqlitch add my_change --note "My note"`  
**When** executed  
**Then** it must:
- Accept both change name and note option
- Not report option parsing errors

### bundle Command (CC-BUNDLE)

#### CC-BUNDLE-001: No Required Arguments
**Given** `sqlitch bundle`  
**When** executed  
**Then** it must:
- Accept command without arguments
- Either create bundle (if implemented) or report "not implemented"

#### CC-BUNDLE-002: Optional Destination
**Given** `sqlitch bundle --dest /tmp/bundle`  
**When** executed  
**Then** it must:
- Accept the destination option
- Not report option parsing errors

### checkout Command (CC-CHECKOUT)

#### CC-CHECKOUT-001: Required Branch
**Given** `sqlitch checkout` without arguments  
**When** executed  
**Then** it must:
- Exit with code 2
- Print error indicating missing branch argument

### config Command (CC-CONFIG)

#### CC-CONFIG-001: Action Without Name
**Given** `sqlitch config --list`  
**When** executed  
**Then** it must:
- Accept the list action
- Either list config (if implemented) or report "not implemented"

#### CC-CONFIG-002: Get With Name
**Given** `sqlitch config --get user.name`  
**When** executed  
**Then** it must:
- Accept get action with name
- Either return config value or report "not implemented"

### deploy Command (CC-DEPLOY)

#### CC-DEPLOY-001: Optional Target
**Given** `sqlitch deploy`  
**When** executed  
**Then** it must:
- Accept command without explicit target (uses default)
- Either deploy (if implemented) or report "not implemented"

#### CC-DEPLOY-002: Positional Target
**Given** `sqlitch deploy db:sqlite:test.db`  
**When** executed  
**Then** it must:
- Accept positional target argument
- Parse target as `db:sqlite:test.db`

#### CC-DEPLOY-003: Target Option
**Given** `sqlitch deploy --target db:sqlite:test.db`  
**When** executed  
**Then** it must:
- Accept target via option
- Not conflict with positional form

#### CC-DEPLOY-004: Multiple Targets Conflict
**Given** `sqlitch deploy db:sqlite:a.db --target db:sqlite:b.db`  
**When** executed  
**Then** it must:
- Exit with code 1
- Print error about conflicting targets

### engine Command (CC-ENGINE)

#### CC-ENGINE-001: Action Required
**Given** `sqlitch engine`  
**When** executed  
**Then** it must:
- Either list engines (default action) or exit with error for missing action
- Follow Sqitch behavior exactly

### help Command (CC-HELP)

#### CC-HELP-001: No Arguments
**Given** `sqlitch help`  
**When** executed  
**Then** it must:
- Exit with code 0
- Print general help listing all commands

#### CC-HELP-002: Command Name
**Given** `sqlitch help deploy`  
**When** executed  
**Then** it must:
- Exit with code 0
- Print help specific to deploy command

### init Command (CC-INIT)

#### CC-INIT-001: Optional Project Name
**Given** `sqlitch init`  
**When** executed  
**Then** it must:
- Accept command without project name (uses directory name)
- Either initialize project or report "not implemented"

#### CC-INIT-002: With Project Name
**Given** `sqlitch init myproject`  
**When** executed  
**Then** it must:
- Accept project name argument
- Not report parsing errors

### log Command (CC-LOG)

#### CC-LOG-001: Optional Target
**Given** `sqlitch log`  
**When** executed  
**Then** it must:
- Accept command without explicit target
- Either show log or report "not implemented"

### plan Command (CC-PLAN)

#### CC-PLAN-001: Optional Target
**Given** `sqlitch plan`  
**When** executed  
**Then** it must:
- Accept command without target (uses default or project plan)
- Either show plan or report "not implemented"

### rebase Command (CC-REBASE)

#### CC-REBASE-001: Optional Target
**Given** `sqlitch rebase`  
**When** executed  
**Then** it must:
- Accept command without explicit target
- Either rebase or report "not implemented"

### revert Command (CC-REVERT)

#### CC-REVERT-001: Optional Target
**Given** `sqlitch revert`  
**When** executed  
**Then** it must:
- Accept command without explicit target
- Either revert or report "not implemented"

#### CC-REVERT-002: Positional Target
**Given** `sqlitch revert db:sqlite:test.db`  
**When** executed  
**Then** it must:
- Accept positional target argument
- Not report parsing errors

### rework Command (CC-REWORK)

#### CC-REWORK-001: Required Change Name
**Given** `sqlitch rework` without arguments  
**When** executed  
**Then** it must:
- Exit with code 2
- Print error indicating missing change name

#### CC-REWORK-002: Valid Change Name
**Given** `sqlitch rework my_change`  
**When** executed  
**Then** it must:
- Accept the change name
- Either rework change or report "not implemented"

### show Command (CC-SHOW)

#### CC-SHOW-001: Optional Change Name
**Given** `sqlitch show`  
**When** executed  
**Then** it must:
- Accept command without arguments (shows all changes)
- Either show output or report "not implemented"

#### CC-SHOW-002: With Change Name
**Given** `sqlitch show my_change`  
**When** executed  
**Then** it must:
- Accept change name argument
- Not report parsing errors

### status Command (CC-STATUS)

#### CC-STATUS-001: Optional Target
**Given** `sqlitch status`  
**When** executed  
**Then** it must:
- Accept command without explicit target
- Either show status or report "not implemented"

#### CC-STATUS-002: Positional Target
**Given** `sqlitch status db:sqlite:test.db`  
**When** executed  
**Then** it must:
- Accept positional target argument
- Not report parsing errors

### tag Command (CC-TAG)

#### CC-TAG-001: Optional Tag Name
**Given** `sqlitch tag`  
**When** executed  
**Then** it must:
- Accept command without tag name (lists tags)
- Either list tags or report "not implemented"

#### CC-TAG-002: With Tag Name
**Given** `sqlitch tag v1.0`  
**When** executed  
**Then** it must:
- Accept tag name argument
- Either create tag or report "not implemented"

### target Command (CC-TARGET)

#### CC-TARGET-001: Action Required
**Given** `sqlitch target`  
**When** executed  
**Then** it must:
- Either list targets (default) or exit with error
- Follow Sqitch behavior exactly

### upgrade Command (CC-UPGRADE)

#### CC-UPGRADE-001: Optional Target
**Given** `sqlitch upgrade`  
**When** executed  
**Then** it must:
- Accept command without explicit target
- Either upgrade or report "not implemented"

### verify Command (CC-VERIFY)

#### CC-VERIFY-001: Optional Target
**Given** `sqlitch verify`  
**When** executed  
**Then** it must:
- Accept command without explicit target
- Either verify or report "not implemented"

#### CC-VERIFY-002: Positional Target
**Given** `sqlitch verify db:sqlite:test.db`  
**When** executed  
**Then** it must:
- Accept positional target argument (FIXED in recent session)
- Not report parsing errors

## Test Implementation Mapping

Each contract maps to a pytest test function:

```python
# tests/cli/commands/test_deploy.py
def test_deploy_accepts_positional_target(cli_runner):
    """Contract CC-DEPLOY-002: Positional Target"""
    result = cli_runner.invoke(deploy, ["db:sqlite:test.db"])
    assert result.exit_code != 2  # Not a parsing error
    # May be 0 (implemented) or 1 (stub)
```

## Contract Validation Checklist

For each command, verify:
- [ ] Help flag works (`--help`)
- [ ] Global options accepted (`--quiet`, `--verbose`, `--chdir`, `--no-pager`)
- [ ] Required arguments enforced
- [ ] Optional arguments accepted
- [ ] Options parsed correctly
- [ ] Unknown options rejected
- [ ] Error messages descriptive
- [ ] Exit codes follow 0/1/2 convention
- [ ] Stub behavior (if applicable): validates args before "not implemented"
