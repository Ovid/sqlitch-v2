# Command Contract: `sqlitch log`

## Purpose
Display deployment history for a target database, mirroring `sqitch log` formatting, filtering, and pagination.

## Inputs
- **Invocation**: `sqlitch log [--target <target>] [--limit <n>] [--skip <n>] [--reverse] [--project <name>] [--format human|json] [--change <name>] [--event deploy|revert|fail|verify]`
- **Environment**: honors `SQLITCH_TARGET`, `SQITCH_LOG_FORMAT`, `PAGER`.

## Behavior
1. Query registry tables for change history ordered by timestamp (descending by default) with pagination options identical to Sqitch.
2. Render output in human-readable format (matching spacing and colorization) or JSON records when `--format json`.
3. Filter results by change name, event type, planner, or tag using identical semantics to Sqitch.
4. `--reverse` flips order while keeping deterministic pagination.

## Outputs
- **STDOUT**: log entries in requested format.
- **STDERR**: errors for unknown targets or query issues.
- **Exit Code**: `0` on success; `1` on failures.

## Error Conditions
- Registry unreachable → exit 1 with descriptive connection error.
- No matching records → still exit 0 but emit `No events found` identical to Sqitch.
- Unknown format option → exit 1 `Unknown format "<value>"`.

## Parity Checks
- Human output diffed against Sqitch for sample registries.
- JSON schema identical (fields: change_id, change, project, event, planner, deployed_at, tags).
- Pager integration mirrors Sqitch, falling back gracefully when PAGER missing.
