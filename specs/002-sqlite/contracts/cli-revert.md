# Command Contract: `sqlitch revert`

## Purpose
Roll back applied changes from the target database registry in reverse order, matching `sqitch revert` semantics.

## Inputs
- **Invocation**: `sqlitch revert [--target <target>] [--to-change <change>] [--to-tag <tag>] [--mode change|tag|all] [--log-only] [--verify] [--no-verify] [--set <name=value>]...`
- **Environment**: inherits `SQLITCH_TARGET`, `SQLITCH_REGISTRY`, `SQITCH_TARGET`.

## Behavior
1. Determine revert boundary based on `--to-*` flags or `--mode` default (last deployed change).
2. Execute revert scripts for each change in reverse order, respecting dependency invariants.
3. Update registry entries to mark reverts, including `reverted_at` timestamp.
4. If `--verify` specified, run verify scripts after revert to confirm state.
5. Dry-run mode prints actions without executing for `--log-only`.

## Outputs
- **STDOUT**: progress log identical to Sqitch.
- **STDERR**: script errors bubbled through.
- **Exit Code**: `0` on success; non-zero otherwise.

## Error Conditions
- Missing revert script → exit 1 `No revert script for change <name>`.
- Attempt to revert beyond deployed history → exit 1 `Change <name> was never deployed`.
- Conflicting options (both `--to-change` and `--to-tag`) → exit 1 parity message.

## Parity Checks
- Registry mutations identical to Sqitch (verified via database assertions).
- Logging respects `--quiet`, `--verbose`, JSON modes.
