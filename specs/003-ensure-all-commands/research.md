# Research: Complete Sqitch Command Surface Parity

**Date**: 2025-10-05  
**Feature**: 003-ensure-all-commands

## Research Questions

### 1. What is the complete Sqitch command inventory?

**Decision**: 19 commands total from sqitchcommands.pod  
**Rationale**: Sqitch documentation lists these as the "common commands":
- add, bundle, checkout, config, deploy, engine, help, init, log, plan, rebase, revert, rework, show, status, tag, target, upgrade, verify

**Source**: `/sqitch/lib/sqitchcommands.pod`

**Verification**: Confirmed all 19 have corresponding modules in `sqlitch/cli/commands/`:
```
$ ls sqlitch/cli/commands/*.py | grep -v __ | wc -l
19
```

### 2. What are the global options that must be supported across all commands?

**Decision**: Four global options required  
**Rationale**: From sqitchusage.pod and sqitch.pod:
- `--chdir <path>`: Change working directory before executing
- `--no-pager`: Disable pager for output
- `--quiet`: Suppress normal output
- `--verbose`: Increase verbosity

**Source**: `/sqitch/lib/sqitchusage.pod` and `/sqitch/lib/sqitch.pod`

**Current State**: SQLitch already has `--quiet` and `--verbose` in `cli/options.py`. Need to verify `--chdir` and `--no-pager` coverage.

**Alternatives Considered**: Could implement only `--verbose`/`--quiet`, but this would break parity.

### 3. What are the exit code conventions?

**Decision**: Three-tier exit code system  
**Rationale**: Standard Sqitch convention documented in multiple pod files:
- 0: Success
- 1: User error (bad arguments, configuration issues, operational failures)
- 2: System error (database unavailable, missing dependencies, internal failures)

**Source**: Sqitch pod documentation and observed behavior

**Current State**: SQLitch uses Click's default behavior which may not distinguish between error types. Need to audit error handling.

**Alternatives Considered**: Could use only 0/1, but system vs user error distinction helps debugging.

### 4. What defines a "stub" implementation for commands not yet feature-complete?

**Decision**: Stub = accepts valid arguments + validates inputs + returns "not implemented" error  
**Rationale**: Enables testing command signatures without blocking CLI development
- Must parse all expected arguments/options
- Must validate arguments as if fully implemented
- Must emit clear "command X is not implemented yet" message
- Must exit with code 1 (user-facing limitation, not system error)

**Example**: Current `verify.py` implementation accepts `target_args` and emits "sqlitch verify is not implemented yet; Sqitch parity pending"

**Alternatives Considered**:
- Return "command not found" → Rejected: breaks help system and command discovery
- Accept no arguments → Rejected: prevents contract testing
- Exit code 2 → Rejected: not a system error, just incomplete feature

### 5. How should command help text be validated for parity?

**Decision**: Direct comparison against Sqitch pod documentation  
**Rationale**: Pod files are the source of truth for help text
- Synopsis section → Click command signature
- Options section → Click options/arguments
- Description → Click command docstring
- Examples → Not required but helpful

**Validation Approach**:
1. Extract help text from pod files (e.g., `sqitch-add.pod`)
2. Generate SQLitch help: `sqlitch add --help`
3. Compare structure: command name, synopsis, options list, descriptions
4. Flag: missing options, wrong descriptions, incorrect syntax

**Tools**: Manual comparison for MVP, could automate with pod parser

**Alternatives Considered**: Ignore help text → Rejected: breaks user experience and documentation

### 6. What argument parsing patterns are used in existing commands?

**Decision**: Click decorators with consistent patterns  
**Rationale**: Analysis of existing commands shows:
- Positional arguments: `@click.argument("name", nargs=-1)` for variable-length
- Required options: `@click.option("--option", required=True)`
- Optional flags: `@click.option("--flag", is_flag=True)`
- Global options: Inherited from shared `@pass_context` decorator

**Pattern Examples**:
```python
# deploy.py - positional target
@click.argument("target_args", nargs=-1)

# add.py - required change name
@click.argument("change_name")

# config.py - operation + optional key/value
@click.argument("action")
@click.argument("name", required=False)
```

**Current Issue**: Some commands may be missing positional target support (e.g., verify was missing it, now fixed)

**Validation Strategy**: Audit each command's decorators against corresponding Sqitch pod usage examples

### 7. How do conflicting global options interact?

**Decision**: Follow Sqitch precedence rules  
**Rationale**: From Sqitch behavior observation:
- `--quiet` + `--verbose` → `--quiet` wins (silence takes precedence)
- `--json` + `--quiet` → `--json` wins (machine output overrides quiet)
- Multiple `--verbose` → increases verbosity level

**Implementation**: Need to verify SQLitch `cli/options.py` handles precedence correctly

**Source**: Empirical testing of Sqitch commands

**Alternatives Considered**: Error on conflicting options → Rejected: Sqitch allows it

### 8. What constitutes "matching error messages"?

**Decision**: Same error type + same key information, not byte-for-byte matching  
**Rationale**: Error messages should convey the same meaning but don't need identical wording
- "Missing required argument 'change_name'" ≈ "Error: change_name is required"
- "Unknown command 'depoy'" ≈ "Error: No such command 'depoy'"
- "Target database not specified" ≈ "Error: No target database"

**Acceptable Deviations**:
- Python vs Perl exception formatting
- Click's error message style vs Sqitch's
- Stack trace presence/absence

**Non-Negotiable**:
- Error category (user vs system)
- Exit code
- Information content (what went wrong)

**Alternatives Considered**: Exact byte matching → Rejected: overly brittle, implementation-dependent

## Summary of Findings

### Technical Decisions
1. **Command Inventory**: 19 commands confirmed present in SQLitch
2. **Global Options**: Four options (`--chdir`, `--no-pager`, `--quiet`, `--verbose`)
3. **Exit Codes**: 0 (success), 1 (user error), 2 (system error)
4. **Stub Pattern**: Validate args + emit "not implemented" + exit 1
5. **Help Validation**: Compare against pod documentation structure
6. **Argument Patterns**: Click decorators following consistent conventions
7. **Option Precedence**: Quiet > verbose, JSON > quiet
8. **Error Matching**: Same meaning + same exit code, not byte-identical

### Implementation Impact
- Audit needed: Global option support (`--chdir`, `--no-pager`)
- Audit needed: Exit code consistency across all commands
- Audit needed: Stub implementations validate args correctly
- Audit needed: Help text matches pod documentation structure
- Contract tests needed: Verify command signatures don't drift
- Regression tests needed: Cross-command option handling consistency

### No Outstanding Clarifications
All questions answered through:
- Sqitch source code review (pod files)
- SQLitch codebase audit
- Empirical Sqitch behavior testing
- Existing implementation patterns
