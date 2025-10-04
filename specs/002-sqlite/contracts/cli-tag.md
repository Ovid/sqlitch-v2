# Command Contract: `sqlitch tag`

## Purpose
Add or list tags in the deployment plan, aligning exactly with `sqitch tag` behavior.

## Inputs
- **Invocation**:
  - Add: `sqlitch tag <tag_name> [<change>] [--note <text>]`
  - List: `sqlitch tag [--list] [--project <name>]`
- **Environment**: `SQLITCH_PLAN_FILE`, `SQITCH_PLAN_FILE`, config root overrides.

## Behavior
1. For addition, append tag entry to plan referencing specified change (default latest change).
2. Enforce uniqueness and consistent ordering; tags attach to existing changes only.
3. Listing displays plan tags with same formatting as Sqitch, including `@` prefix and notes.

## Outputs
- **STDOUT**: success messages or tag list identical to Sqitch.
- **STDERR**: validation errors.
- **Exit Code**: `0` on success; `1` on failure.

## Error Conditions
- Tag already exists → exit 1 `Tag "<name>" already exists`.
- Change not found → exit 1 `Unknown change "<name>"`.
- Both `sqlitch.plan` and `sqitch.plan` present → exit 1 conflict message.

## Parity Checks
- Tag serialization matches Sqitch (ordering, spacing, timestamp formatting).
- Listing output validated against Sqitch for sample plans.
