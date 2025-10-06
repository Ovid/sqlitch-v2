# Data Model: Complete Sqitch Command Surface Parity

**Date**: 2025-10-05  
**Feature**: 003-ensure-all-commands

## Overview
This feature operates on the CLI interface layer and does not introduce new data entities. The "data" in this context is the command metadata and validation rules that define the CLI contract.

## Command Metadata Entity

### Entity: Command
Represents a SQLitch CLI command with its signature and validation rules.

**Attributes**:
- `name`: str - Command name (e.g., "add", "deploy", "verify")
- `arguments`: list[Argument] - Positional arguments the command accepts
- `options`: list[Option] - Named options/flags the command accepts
- `global_options`: list[str] - Global options inherited from CLI (--chdir, --quiet, --verbose, --no-pager)
- `help_text`: str - Description shown in help output
- `synopsis`: str - Usage pattern (e.g., "sqlitch add [options] <change_name>")
- `exit_codes`: dict[int, str] - Mapping of exit codes to their meaning
- `is_stub`: bool - Whether command is a stub implementation

**Relationships**:
- None (standalone CLI contract definition)

**Validation Rules**:
- Command name must match Sqitch command name exactly
- All Sqitch arguments must be present
- All Sqitch options must be present with same names and types
- Help text structure must match pod documentation
- Exit codes must follow 0=success, 1=user error, 2=system error

### Sub-Entity: Argument
Represents a positional command-line argument.

**Attributes**:
- `name`: str - Argument name (e.g., "change_name", "target_args")
- `position`: int - Order in argument list
- `required`: bool - Whether argument is mandatory
- `multiple`: bool - Whether argument accepts multiple values (nargs=-1)
- `description`: str - Help text for this argument

**Validation Rules**:
- Name must match Sqitch argument name
- Required status must match Sqitch
- Multiple value support must match Sqitch

### Sub-Entity: Option
Represents a named command-line option or flag.

**Attributes**:
- `name`: str - Option name (e.g., "--target", "--verify")
- `short_name`: str | None - Short form (e.g., "-t")
- `type`: str - Value type (string, int, bool/flag)
- `required`: bool - Whether option is mandatory
- `default`: Any - Default value if not specified
- `multiple`: bool - Whether option can be repeated
- `description`: str - Help text for this option

**Validation Rules**:
- Name must match Sqitch option name
- Type must match Sqitch (e.g., --limit is int, --verify is flag)
- Default value must match Sqitch
- Required status must match Sqitch

## State Model

### Command Execution States
Commands progress through these states during execution:

1. **Parsing**: Click parses arguments and options
   - Exit if parsing fails (invalid syntax, missing required args)
   
2. **Validation**: Command validates argument values
   - Exit if validation fails (e.g., target doesn't exist)
   
3. **Execution**: Command performs its operation
   - Stub commands: emit "not implemented" and exit 1
   - Implemented commands: execute business logic
   
4. **Completion**: Command returns exit code
   - 0 for success
   - 1 for user error (bad input, expected failure)
   - 2 for system error (database down, internal error)

### Global Option Precedence
When conflicting global options are provided:

```
--quiet + --verbose → --quiet wins (silence takes precedence)
--json + --quiet → --json wins (machine output overrides)
--verbose (multiple) → increases verbosity level
```

## Consistency Rules

### Cross-Command Invariants
Rules that must hold across all 19 commands:

1. **Global Options**: All commands must accept `--chdir`, `--no-pager`, `--quiet`, `--verbose`
2. **Help Flag**: All commands must respond to `--help` with formatted help text
3. **Exit Codes**: All commands must use 0/1/2 convention consistently
4. **Target Arguments**: Commands operating on databases must accept target via positional arg or `--target` option
5. **Error Format**: All commands must emit errors to stderr, success output to stdout

### Validation Consistency
Commands with similar argument types should validate similarly:

- **Change names**: Must match pattern `[a-zA-Z0-9_-]+` (alphanumeric, underscore, hyphen)
- **Target strings**: Must match pattern `engine:target_spec` (e.g., `db:sqlite:test.db`)
- **File paths**: Must be valid paths (exist for read operations, writable for write operations)
- **Tags**: Must match pattern `@tag_name` when specified

## Contract Test Requirements

### Per-Command Contracts
Each command must have tests verifying:

1. **Signature Test**: Command accepts all required arguments/options
2. **Help Test**: `--help` returns formatted help with synopsis, options, description
3. **Required Args Test**: Missing required arguments causes exit 1 with error message
4. **Invalid Args Test**: Invalid argument values cause exit 1 with descriptive error
5. **Global Options Test**: `--quiet`, `--verbose`, etc. are recognized (may be no-op for stubs)
6. **Stub Behavior Test** (if stub): Validates args then emits "not implemented" and exits 1

### Cross-Command Contracts
Tests that validate consistency across all commands:

1. **Help Format Test**: All help outputs follow same structure
2. **Exit Code Test**: All commands use 0/1/2 convention
3. **Error Output Test**: All commands emit errors to stderr
4. **Global Options Test**: All commands accept global options without error
5. **Unknown Option Test**: All commands reject unknown options with exit 1

## Implementation Notes

### Existing State (as of UAT session)
- 19 command modules exist in `sqlitch/cli/commands/`
- Recent fix: `verify.py` now accepts positional `target_args`
- Global options defined in `cli/options.py`
- Command registration in `cli/commands/__init__.py`

### Known Gaps (from research)
- Need to audit `--chdir` and `--no-pager` support across all commands
- Need to audit exit code usage (may not distinguish 1 vs 2 consistently)
- Need to verify stub implementations validate arguments before returning "not implemented"
- Need contract tests for all 19 commands

### Non-Goals for This Feature
- Full implementation of stub commands (separate features)
- Engine-specific behavior validation (covered by engine features)
- Performance optimization (CLI parsing is already fast)
- Additional commands beyond the 19 Sqitch commands (out of scope)
