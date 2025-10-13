# UAT Directory Structure

This directory contains User Acceptance Testing (UAT) infrastructure for validating Sqitch/SQLitch interoperability.

## Directory Layout

```
uat/
├── lib/                    # Reusable library modules
│   ├── comparison.py       # Output comparison utilities
│   ├── isolation.py        # Environment isolation for subprocess execution
│   ├── sanitization.py     # Output sanitization (timestamps, hashes, etc.)
│   └── test_steps.py       # Tutorial test step definitions
│
├── scripts/                # Executable UAT test scripts
│   ├── backward-compat.py  # SQLitch-first, then Sqitch compatibility test
│   ├── forward-compat.py   # Sqitch-first, then SQLitch compatibility test
│   └── side-by-side.py     # Parallel execution comparison test
│
├── artifacts/              # Test execution artifacts (git-ignored)
│   ├── sqitch_results/     # Sqitch execution results
│   └── sqlitch_results/    # SQLitch execution results
│
└── sqitchtutorial-sqlite.pod  # Reference SQLite tutorial documentation
```

## Running UAT Scripts

All scripts should be run from the **project root**:

```bash
# From project root (/Users/poecurt/projects/sqlitch)
python uat/scripts/forward-compat.py --out /tmp/forward.log
python uat/scripts/backward-compat.py --out /tmp/backward.log
python uat/scripts/side-by-side.py --out /tmp/side-by-side.log
```

## Environment Isolation

All UAT scripts use isolated environments to prevent pollution of user config files:

- **Project config**: `artifacts/{sqitch,sqlitch}_results/sqitch.conf` (shared between tools)
- **System config**: `artifacts/{sqitch,sqlitch}_results/.isolated/system/system.conf`
- **User config**: `artifacts/{sqitch,sqlitch}_results/.isolated/user/user.conf`

The isolation ensures that:
1. User's `~/.sqitch/sqitch.conf` is never modified
2. System `/etc/sqitch/sqitch.conf` is never read
3. Both tools can interoperate on the same test project

## Debugging Failed Tests

When tests fail, inspect the artifacts directory:

```bash
# View execution logs
cat uat/artifacts/sqitch_results/uat.log
cat uat/artifacts/sqlitch_results/uat.log

# View project config (shared between tools)
cat uat/artifacts/sqitch_results/sqitch.conf

# View isolated system/user configs (if needed)
cat uat/artifacts/sqitch_results/.isolated/system/system.conf
cat uat/artifacts/sqitch_results/.isolated/user/user.conf

# Inspect database state
sqlite3 uat/artifacts/sqitch_results/flipr_test.db ".dump"
sqlite3 uat/artifacts/sqitch_results/sqitch.db ".dump"
```

## Library Modules

### comparison.py
Utilities for comparing command outputs and database states:
- `compare_outputs()`: Compare sanitized command outputs
- `compare_user_databases()`: Compare user table contents
- `compare_database_schemas()`: Compare schema structures

### isolation.py
Environment isolation for subprocess execution:
- `create_isolated_environment()`: Creates isolated env vars for sqitch/sqlitch

### sanitization.py
Output sanitization for timestamp/hash stability:
- `sanitize_output()`: Remove timestamps, hashes, absolute paths
- Ensures outputs can be compared across runs

### test_steps.py
Tutorial test step definitions:
- `TUTORIAL_STEPS`: List of all tutorial steps with metadata
- `Step`: Dataclass defining a single test step

## Development Notes

- **Import paths**: Use `from uat.lib import ...` for library modules
- **Path resolution**: All paths are relative to project root
- **Config file names**: System/user configs use `.conf` extension for clarity
- **Artifact cleanup**: Artifacts are git-ignored but preserved for debugging
