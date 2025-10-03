# Command Contract: `sqlitch rebase`

## Purpose
Revert and redeploy changes to align with the latest plan state, mirroring `sqitch rebase` semantics.

## Inputs
- **Invocation**: `sqlitch rebase [--target <target>] [--onto <change|tag>] [--from <change|tag>] [--mode latest|all] [--log-only]`
- **Environment**: uses `SQLITCH_TARGET`, `SQITCH_TARGET`, config root overrides.

## Behavior
1. Determine divergence between registry state and plan head.
2. Revert newer changes back to `--onto` (default latest deployed change), respecting dependencies.
3. Redeploy necessary changes in order, emitting same progress output as Sqitch.
4. Dry-run mode prints actions without executing when `--log-only` set.

## Outputs
- **STDOUT**: stepwise log matching Sqitch phrases.
- **STDERR**: errors from revert/deploy operations.
- **Exit Code**: `0` on success; propagate first failure otherwise.

## Error Conditions
- Incompatible options (e.g., `--onto` and `--mode all`) → exit 1 replicating Sqitch validation.
- Revert failure aborts redeploy phase and exits 1 with identical messaging.
- Registry/plan mismatch (missing change) → exit 1 `Registry missing change <name>`.

## Parity Checks
- Sequence of operations identical; integration tests compare command transcripts.
- Supports same confirmation prompts as Sqitch for destructive operations.
