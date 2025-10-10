# Status and Log Command Parity Report

**Date**: 2025-10-09  
**Feature**: 004-sqlitch-tutorial-parity  
**Scope**: SQLite registry target normalization and output formatting

## Overview

This document describes the implementation changes made to achieve Sqitch parity for the `status` and `log` commands, particularly focusing on how SQLite database targets are resolved and displayed.

## Problem Statement

The `status` command needed to:
1. Accept relative database paths (e.g., `db:sqlite:./db/target.db`)
2. Resolve them to absolute filesystem paths internally
3. Display the normalized target path in output while maintaining Sqitch compatibility
4. Handle missing registry databases gracefully (fresh projects with no deployments)

The `log` command needed to:
1. Match Sqitch's event output formatting exactly
2. Display committer identity with proper spacing
3. Maintain reverse chronological ordering

## Key Changes

### 1. Registry Target Resolution (`_resolve_registry_target`)

**Location**: `sqlitch/cli/commands/status.py`

The function now:
- Parses database URIs with proper scheme handling (`db:sqlite:`)
- Resolves relative paths against the project root
- Maintains separate display and internal representations of targets
- Derives registry database location from workspace database location (sibling `sqitch.db`)

**Example**:
```python
# Input: "db:sqlite:./db/target.db" 
# Internal URI: "db:sqlite:/absolute/path/to/db/target.db"
# Display target: "db:sqlite:./db/target.db" (preserves original)
# Registry URI: "db:sqlite:/absolute/path/to/db/sqitch.db"
```

### 2. Missing Database Handling (`_load_registry_state`)

**Location**: `sqlitch/cli/commands/status.py`

The implementation was corrected to understand that:
- SQLite **creates** database files automatically on connection
- Status should succeed on fresh projects (no registry = "not deployed" state)
- Missing schema (no tables) is caught by `_registry_schema_missing()`
- Empty registry returns empty rows, not errors

**Previous incorrect behavior**: Checked if registry file existed and raised `CommandError`  
**Correct behavior**: Let SQLite create the file, catch "no such table" errors, return empty state

### 3. Human Output Formatting (`_render_human_output`)

**Location**: `sqlitch/cli/commands/status.py`

The function emits Sqitch-compatible output:
```
# On database <target>
# Project:  <project_name>
# Change:   <most_recent_change_id>
# Name:     <most_recent_change_name>
# Deployed: <timestamp>
# By:       <committer_name> <committer_email>
#
# Status: <up-to-date|behind|ahead>
```

For fresh projects:
```
# On database <target>
# Project:  <project_name>
# Status: No changes deployed
```

### 4. JSON Payload Construction (`_build_json_payload`)

**Location**: `sqlitch/cli/commands/status.py`

The JSON output includes:
- `target`: Display target string
- `project`: Project name from plan
- `status`: State enum (in_sync, behind, ahead, not_deployed)
- `deployed_changes`: Array of deployed change metadata
- `pending_changes`: Array of change names not yet deployed
- `last_failure`: Optional failure event metadata

### 5. Log Output Formatting (`_render_human_output` in log.py)

**Location**: `sqlitch/cli/commands/log.py`

The log command matches Sqitch's output format:
```
On <database> <target>
<change_name> <timestamp>
Name:      <change_name>
Project:   <project_name>
Committer: <name> <<email>>
Date:      <iso_timestamp>

    <note>
```

## Testing Strategy

### Unit Tests
- `tests/cli/test_status_unit.py`: Target resolution, registry state loading
- Updated `test_load_registry_rows_missing_database` to expect empty rows, not errors

### Functional Tests
- `tests/cli/commands/test_status_functional.py`: End-to-end status command behavior
- `tests/cli/commands/test_log_functional.py`: End-to-end log command behavior
- `tests/cli/commands/test_target_functional.py`: Environment variable overrides

### Integration Tests
- `tests/regression/test_tutorial_parity.py`: Byte-for-byte comparison with Sqitch output
- `tests/integration/test_tutorial_workflows.py`: Multi-step scenarios

## Compatibility Notes

### Sqitch Parity
- ✅ Fresh projects (no registry) show "No changes deployed"
- ✅ Relative paths in URIs are resolved correctly
- ✅ Display target matches user input format
- ✅ Registry is auto-created as sibling to workspace DB
- ✅ Log output matches Sqitch formatting exactly

### Deviations
None. Full behavioral parity achieved.

## Performance Considerations

- Registry path resolution adds minimal overhead (path normalization)
- SQLite auto-creation has no performance impact (happens once per project)
- Target string normalization is done once per command invocation

## Future Work

None required for this feature. The implementation is complete and all tests pass.

## References

- Feature Spec: `specs/004-sqlitch-tutorial-parity/spec.md`
- Implementation Plan: `specs/004-sqlitch-tutorial-parity/plan.md`
- Task List: `specs/004-sqlitch-tutorial-parity/tasks.md`
- Constitution: `.specify/memory/constitution.md`
- Sqitch Reference: `sqitch/lib/sqitchtutorial-sqlite.pod`
