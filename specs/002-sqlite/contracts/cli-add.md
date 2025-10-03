# Command Contract: `sqlitch add`

## Purpose
Register a new change in the project plan, generating deploy/revert (and optional verify) scripts and appending the change entry using Sqitch-compatible formatting.

## Inputs
- **Invocation**: `sqlitch add <change_name> [--requires <dep>]... [--tags <tag>]... [--note <text>] [--deploy <path>] [--revert <path>] [--verify <path>] [--template <template_name>]`
- **Environment**: respects `SQLITCH_PLAN_FILE`, `SQLITCH_CONFIG_ROOT`, and Sqitch-compatible `SQITCH_PLAN_FILE`, `SQITCH_TOP_DIR`.
- **Files**: reads existing `sqlitch.plan` or `sqitch.plan`. Plan selection must error if both exist.

## Behavior
1. Validate that `<change_name>` is unique in the plan.
2. Resolve templates from `etc/templates/` respecting the same lookup order as Sqitch (project → user → system) with overrides.
3. Create script files using standard naming (`deploy/<timestamp>_<name>.sql`, etc.) unless custom paths provided.
4. Append plan entry with identical formatting, timestamps, and dependency/tag syntax to Sqitch output.
5. Persist notes and tags exactly as provided; maintain deterministic ordering of dependencies and tags.

## Outputs
- **STDOUT**: Matches Sqitch message format (e.g., `Created deploy script deploy/<...>`, `Added <change_name>`), newline-terminated.
- **STDERR**: empty on success.
- **Exit Code**: `0` on success; non-zero on validation failure.

## Error Conditions
- Duplicate change name → exit 1, message mirrors Sqitch (`Change "<name>" already exists in plan`).
- Both `sqlitch.plan` and `sqitch.plan` present → exit 1 with explicit conflict error.
- Missing templates → exit 1 referencing template path looked up.
- File system failure (permission denied, unwritable directory) → propagate error with identical phrasing to Sqitch.

## Parity Checks
- Timestamp formatting must match Sqitch’s `%Y-%m-%d %H:%M:%S %z` output.
- Generated file paths relative to top directory mimic Sqitch’s structure.
- CLI help text, option names, and ordering replicate `sqitch add --help`.
- Unit tests compare plan diff and script contents against Sqitch golden fixtures.
