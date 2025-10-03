# Command Contract: `sqlitch verify`

## Purpose
Execute verification scripts against deployed changes to ensure database state matches expectations, mirroring `sqitch verify`.

## Inputs
- **Invocation**: `sqlitch verify [--target <target>] [--to-change <change>] [--to-tag <tag>] [--event deploy|revert|fail] [--mode all|change|tag] [--log-only]`
- **Environment**: `SQLITCH_TARGET`, `SQLITCH_REGISTRY`.

## Behavior
1. Determine scope of verification (default latest deployed change).
2. For each change, run verify script within transaction sandbox (where supported) without mutating registry.
3. Report success/failure per change; mark registry verification timestamp when successful.
4. Respect `--log-only` to print plan without running scripts.

## Outputs
- **STDOUT**: success/failure lines identical to Sqitch, including `ok` prefix and change name.
- **STDERR**: script errors.
- **Exit Code**: `0` when all verifications pass; `1` when any verification fails.

## Error Conditions
- Missing verify script → exit 1 `No verify script for change <name>`.
- Change not deployed → exit 1 `Change <name> not deployed`.
- Database errors propagate with same formatting as Sqitch.

## Parity Checks
- Output transcripts compared to Sqitch for sample projects (pass/fail cases).
- Registry updates mirror Sqitch verification metadata (e.g., `verified_at`).
