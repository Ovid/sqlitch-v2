# Command Contract: `sqlitch rework`

## Purpose
Duplicate an existing change, allowing edits to deploy/revert scripts while preserving dependency graph, mirroring `sqitch rework`.

## Inputs
- **Invocation**: `sqlitch rework <change_name> [--requires <dep>]... [--note <text>] [--deploy <path>] [--revert <path>] [--verify <path>]`
- **Environment**: same as `sqlitch add`, including template lookup paths.

## Behavior
1. Copy existing change metadata and scripts to new timestamped files, appending `_rework` suffix per Sqitch precedent.
2. Update plan entry in place, preserving order and dependencies.
3. Optionally replace dependencies, notes, or tags if provided.
4. Ensure original change remains in history for audit (matching Sqitch semantics).

## Outputs
- **STDOUT**: `Created rework deploy script ...`, `Copied revert script ...`, `Reworked <change>` identical to Sqitch messaging.
- **STDERR**: error details.
- **Exit Code**: `0` on success; `1` otherwise.

## Error Conditions
- Change not found → exit 1 `Unknown change "<name>"`.
- Existing rework files present without `--force` (if supported) → exit 1 similar to Sqitch.
- Template resolution failure → exit 1.

## Parity Checks
- Script naming, timestamps, and plan formatting match Sqitch.
- Dependencies remain consistent; tests compare plan diffs after rework operation.
