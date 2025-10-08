# CLI Command Contracts

**Feature**: 004-sqlitch-tutorial-parity  
**Date**: 2025-10-06

---

## Overview

This directory documents the CLI command contracts for SQLitch tutorial parity. Unlike API contracts (REST/GraphQL), CLI contracts define:
- Command signatures (positional arguments, options, flags)
- Input validation rules
- Output formats (human-readable and JSON)
- Exit codes
- Error messages

---

### Environment Variable Overrides *(Updated 2025-10-08)*

- SQLitch must recognize every Sqitch environment variable, preferring `SQLITCH_*` forms and falling back to `SQITCH_*` when absent.
- Contract tests cover overrides for:
    - Target selection: `SQLITCH_TARGET` → `SQITCH_TARGET`
    - Authentication: `SQLITCH_USERNAME` / `SQLITCH_PASSWORD`
    - Identity: `SQLITCH_FULLNAME`, `SQLITCH_EMAIL`, `SQLITCH_USER_NAME`, `SQLITCH_USER_EMAIL`, `SQLITCH_ORIG_*`
    - Tooling: `SQLITCH_EDITOR`, `SQLITCH_PAGER`
- Tests verify that CLI commands pick up overrides without explicit flags and record the resulting identity/target metadata in logs and registry events.

---

## Contract Test Coverage

CLI contracts are validated through contract tests in `tests/cli/commands/test_*_contract.py`. These tests ensure:

1. **Signature Parity**: All commands accept the same arguments and options as Sqitch
2. **Help Text**: `--help` output matches Sqitch format
3. **Global Options**: `--verbose`, `--quiet`, `--chdir`, `--no-pager` work consistently
4. **Error Handling**: Invalid inputs produce appropriate error messages and exit codes

---

## Command Contracts Summary

### 1. `sqitch init [project]`
**Status**: ✅ Implemented (Feature 003)

**Signature**:
```
sqitch init [project_name] [--uri URI] [--engine ENGINE] [options]
```

**Contract Tests**: `tests/cli/commands/test_init_contract.py`
- TestInitOptionalProjectName
- TestInitWithProjectName
- TestInitGlobalOptions
- TestInitErrorHandling
- TestInitHelp

---

### 2. `sqitch config <name> [value]`
**Status**: ⚠️ Partial (get/set operations needed)

**Signature**:
```
sqitch config <name> [value]
sqitch config --get <name>
sqitch config --set <name> <value>
sqitch config --user <name> <value>
sqitch config --local <name> <value>
sqitch config --list
```

**Contract Tests**: `tests/cli/commands/test_config_contract.py`
- TestConfigCommandContract
- TestConfigGlobalContracts

**Requirements**:
- Read from hierarchical config (system/user/local)
- Write to specified scope
- List all config values
- Error on missing or invalid keys
- Honor `SQITCH_CONFIG`, `SQITCH_USER_CONFIG`, and `SQITCH_SYSTEM_CONFIG` overrides while keeping config precedence (system→user→local)
- Never emit `core.uri` when `--uri` supplied during init (plan handles `%uri=` pragma)

---

### 3. `sqitch add <change>`
**Status**: ✅ Implemented (Feature 003)

**Signature**:
```
sqitch add <change> [-n|--note NOTE] [--requires CHANGE] [--conflicts CHANGE] [options]
```

**Contract Tests**: `tests/cli/commands/test_add_contract.py`
- TestAddCommandContract
- TestAddGlobalContracts

---

### 4. `sqitch deploy [target]`
**Status**: ✅ Functional (Feature 002 + recent user identity fix)

**Signature**:
```
sqitch deploy [db:engine:target] [--to-change CHANGE] [--to-tag TAG] [--mode MODE] [options]
```

**Contract Tests**: `tests/cli/commands/test_deploy_contract.py`
- TestDeployCommandContract
- TestDeployGlobalContracts

**Functional Tests**: `tests/cli/commands/test_deploy_functional.py`
- 20 tests covering registry creation, change deployment, dependencies, transactions

**Additional Requirements**:
- Respect `SQLITCH_TARGET`/`SQITCH_TARGET` overrides when no positional target supplied.
- Capture committer identity using the full precedence chain (config → SQLITCH_* → SQITCH_* → git/system).
- On script failure, roll back the workspace transaction, insert a `fail` event, and exit 1 (FR-010a).

---

### 5. `sqitch verify [target]`
**Status**: ✅ Functional (Feature 002)

**Signature**:
```
sqitch verify [db:engine:target] [options]
```

**Contract Tests**: `tests/cli/commands/test_verify_contract.py`
- TestVerifyCommandContract
- TestVerifyGlobalContracts

**Functional Tests**: `tests/cli/commands/test_verify_functional.py`
- TestVerifyExecution: 5 tests covering script execution, success/failure reporting

**Additional Requirements**:
- Continue executing remaining verify scripts after a failure, summarizing all results, and exit 1 if any failure occurred (FR-011a).
- Respect environment target overrides and identity precedence for emitted output.

---

### 6. `sqitch revert [target]`
**Status**: ⚠️ Stub (implementation needed)

**Signature**:
```
sqitch revert [db:engine:target] [--to CHANGE] [--to-tag TAG] [options]
```

**Contract Tests**: `tests/cli/commands/test_revert_contract.py`
- TestRevertHelp
- TestRevertOptionalTarget
- TestRevertPositionalTarget
- TestRevertGlobalOptions
- TestRevertErrorHandling

**Requirements**:
- Revert changes in reverse order
- Update registry
- Support `--to` for partial reverts
- Validate no dependent changes exist
- Prompt before reverting unless `--yes`/`-y` provided (FR-012a)

---

### 7. `sqitch status [target]`
**Status**: ✅ Functional (Feature 002)

**Signature**:
```
sqitch status [db:engine:target] [--show-tags] [options]
```

**Contract Tests**: `tests/cli/commands/test_status_contract.py`
- TestStatusHelp
- TestStatusOptionalTarget
- TestStatusPositionalTarget
- TestStatusGlobalOptions
- TestStatusErrorHandling

**Functional Tests**: `tests/cli/commands/test_status_functional.py`
- 5 tests covering registry queries, deployed/pending changes display

---

### 8. `sqitch log [target]`
**Status**: ⚠️ Stub (implementation needed)

**Signature**:
```
sqitch log [db:engine:target] [--event TYPE] [--change CHANGE] [--format FORMAT] [options]
```

**Contract Tests**: `tests/cli/commands/test_log_contract.py` (via contracts/)
- Log command contract tests exist in `tests/cli/contracts/test_log_contract.py`

**Requirements**:
- Query events from registry
- Display in reverse chronological order
- Support filtering by event type and change
- Support human and JSON formats
- Display deploy failures (FR-010a) with recorded committer identity sourced from environment precedence

---

### 9. `sqitch tag <name>`
**Status**: ⚠️ Stub (implementation needed)

**Signature**:
```
sqitch tag [tag_name] [--change CHANGE] [-n|--note NOTE] [options]
```

**Contract Tests**: `tests/cli/commands/test_tag_contract.py`
- TestTagHelp
- TestTagOptionalName
- TestTagWithName
- TestTagGlobalOptions
- TestTagErrorHandling

**Requirements**:
- Add tag to plan file
- Associate with specific change or latest
- Support tag notes
- List tags when no name provided

---

### 10. `sqitch rework <change>`
**Status**: ⚠️ Stub (implementation needed)

**Signature**:
```
sqitch rework <change> [-n|--note NOTE] [options]
```

**Contract Tests**: `tests/cli/commands/test_rework_contract.py`
- TestReworkHelp
- TestReworkRequiredChangeName
- TestReworkValidChangeName
- TestReworkGlobalOptions
- TestReworkErrorHandling

**Requirements**:
- Create @tag versioned scripts
- Update plan file
- Copy existing scripts as starting point
- Preserve original scripts

---

### 11. `sqitch engine <action>`
**Status**: ⚠️ Partial (alias resolution missing)

**Key Behavior Update (2025-10-07)**:
- `engine add <engine> <target>` MUST accept either a URI or the name of a target defined via `target add`, resolving to `target.<name>.uri` exactly like Sqitch.
- `engine update` shares the same resolution rules; rejecting known aliases is a parity bug (see FR-022).
- `engine remove` MUST leave config clean and emit Sqitch-equivalent messaging.

---

## Exit Code Conventions

All commands follow these exit code conventions:

| Code | Meaning | Usage |
|------|---------|-------|
| 0 | Success | Command completed successfully |
| 1 | User error | Invalid arguments, missing files, validation failures |
| 2 | Parsing error | Plan file syntax error, config file error |

---

## Global Options

All commands support these global options (tested in contract tests):

- `--help` / `-h`: Display command help
- `--verbose` / `-v`: Increase verbosity (repeatable: -v, -vv, -vvv)
- `--quiet` / `-q`: Suppress non-error output
- `--chdir` / `-C`: Change to directory before executing
- `--no-pager`: Disable output paging

---

## Output Format Parity

**Default (Human-Readable)**:
- Must match Sqitch byte-for-byte (excluding timestamps/user-specific data)
- No ANSI colors or emojis
- Progress messages to stderr
- Results to stdout

**JSON Mode** (`--json` flag):
- Structured output with run identifiers
- Machine-parseable
- Complete event/change information

---

## Test Organization

```
tests/cli/
├── commands/                    # Command-specific tests
│   ├── test_add_contract.py    # CLI signature tests
│   ├── test_add_functional.py  # End-to-end behavior tests
│   ├── test_config_contract.py
│   ├── test_config_functional.py
│   └── ...
└── contracts/                   # Integration contract tests
    ├── test_add_contract.py     # Cross-command integration
    ├── test_deploy_contract.py
    └── ...
```

---

## References

- Feature 003 Spec: CLI Command Parity (established contract testing pattern)
- Sqitch Reference: `sqitch/bin/sqitch` and `sqitch/lib/sqitch-*.pod`
- Constitution: `.specify/memory/constitution.md` (Test-First Development, Behavioral Parity)
