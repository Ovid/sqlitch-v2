# Command Contract: `sqlitch bundle`

## Purpose
Create a distributable archive containing plan files, deploy scripts, dependencies, and metadata required to deploy SQLitch changes without VCS access, mirroring Sqitch bundling semantics.

## Inputs
- **Invocation**: `sqlitch bundle [<dir>] [--dest <path>] [--plan <plan_file>] [--from <tag>] [--to <tag>] [--tag <name>] [--no-plan]`
- **Environment**: inherits `SQLITCH_PLAN_FILE`, `SQLITCH_BUNDLE_DIR`, and `SQITCH_BUNDLE_DIR` equivalents.
- **Files**: reads existing plan, scripts, and config scope directories.

## Behavior
1. Resolve bundle destination (defaults to `./bundle`), creating directories as needed.
2. Copy plan, deploy/revert/verify scripts, and supporting files, preserving relative paths and file permissions.
3. Apply filters (`--from`, `--to`, `--tag`) exactly as Sqitch does, ensuring consistent subset selection.
4. Include registry deployment metadata (if applicable) using Sqitch-compatible JSON.
5. Honor `--no-plan` by omitting plan file while still copying scripts.

## Outputs
- **STDOUT**: `Bundled project to <dest>` style message identical to Sqitch.
- **STDERR**: warnings about skipped files match Sqitch output.
- **Exit Code**: `0` on success; `1` with descriptive error otherwise.

## Error Conditions
- Destination unwritable → exit 1 with message `Cannot create directory <dest>`.
- Plan missing → exit 1 `Cannot read plan file <path>`.
- Invalid range selection (`--from` newer than `--to`) → exit 1 replicating Sqitch wording.

## Parity Checks
- Directory structure of bundle matches Sqitch reference archive (validated via integration test diff).
- Timestamps preserved on copied files (to limits of OS).
- Options and help text consistent with `sqitch bundle`.
