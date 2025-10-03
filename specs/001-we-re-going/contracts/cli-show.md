# Command Contract: `sqlitch show`

## Purpose
Display information about changes, tags, or script contents exactly as `sqitch show` does.

## Inputs
- **Invocation**: `sqlitch show <change|tag> [--format human|json] [--script deploy|revert|verify] [--project <name>]`
- **Environment**: honors `SQLITCH_PLAN_FILE`, `SQLITCH_TOP_DIR`.

## Behavior
1. Resolve target change or tag from plan file and registry.
2. When `--script` specified, output contents of the associated script file.
3. Default human format prints metadata (name, dependencies, planner, note, tags) identical to Sqitch ordering.
4. JSON format returns structured object for automation.

## Outputs
- **STDOUT**: change details or script content exactly matching Sqitch output (including blank line separation).
- **STDERR**: error messages for unknown change/tag.
- **Exit Code**: `0` on success; `1` for missing change/tag.

## Error Conditions
- Change/tag not found → exit 1 `Unknown change "<name>"`.
- Script file missing → exit 1 `Cannot find <script> script for <change>`.

## Parity Checks
- Output order and labeling identical to Sqitch (tested via fixture snapshots).
- Script output preserves file encoding and newline endings.
