# Command Contract: `sqlitch checkout`

## Purpose
Automate the sequence revert → VCS branch switch → deploy, keeping database state aligned with a new source control branch exactly as Sqitch performs.

## Inputs
- **Invocation**: `sqlitch checkout [--target <target>] [--engine <engine>] [--mode latest|tag:<tag>|change:<change>] [--to-change <change>] [--log-only]`
- **Environment**: uses `SQLITCH_TARGET`, `SQLITCH_PLAN_FILE`, and VCS environment variables identical to Sqitch.
- **Prerequisites**: Underlying VCS commands (git, etc.) available; plan and registry accessible.

## Behavior
1. Run `sqlitch revert` to unwind current deployment to the specified mode.
2. Execute VCS checkout command determined by configuration (mirrors Sqitch `core.vcs` integration hooks).
3. Run `sqlitch deploy` to redeploy up to desired change/tag.
4. Maintain parity in prompts, progress messages, and error flows, including `--log-only` dry run.

## Outputs
- **STDOUT**: multi-step log consistent with Sqitch (`Reverting to...`, `Checking out ...`, `Deploying changes ...`).
- **STDERR**: pass-through of underlying command errors.
- **Exit Code**: `0` on success; propagate non-zero from revert/deploy/VCS operations.

## Error Conditions
- Missing VCS configuration → exit 1 `No VCS configured` (mirrors Sqitch).
- Revert failure → exit 1 with revert error, aborting remaining steps.
- Deploy failure after checkout triggers revert rollback consistent with Sqitch (documented in integration tests).

## Parity Checks
- Execution order identical to Sqitch with same hooks.
- Support for interactive prompts, using Click confirmations identical to Sqitch messaging.
- Logging flags (`--quiet`, `--verbose`, `--log-only`) behave the same.
