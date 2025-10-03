# Sqitch Parity Golden Fixtures

These fixtures capture canonical Sqitch outputs that we will diff against the Python implementation during parity tests (FR-007). The data was collected from the upstream Sqitch project to avoid invoking the Perl toolchain at test time.

## Layout

- `plans/` – Reference plan files with pragmas, dependencies, tags, and whitespace edge cases.
- `registry/` – Text snapshots of Sqitch registry-driven commands (`status`, `verify`, `log`). Each engine has its own subdirectory (currently only `sqlite/`).

## Provenance

Plan fixtures are adapted directly from Sqitch's test plans under `sqitch/t/plans/`. Registry snapshots were transcribed from the official Sqitch SQLite tutorial (`sqitch/lib/sqitchtutorial-sqlite.pod`) to preserve real command output formatting and timestamps.

## Regenerating Fixtures

1. Install the Perl-based Sqitch CLI.
2. Re-run the commands documented alongside each fixture, capturing stdout.
3. Overwrite the corresponding file in this directory.
4. Keep trailing whitespace, indentation, and blank lines intact so parity comparisons stay stable.

## Usage Notes

Test helpers will load these files verbatim and compare SQLitch output byte-for-byte. Avoid normalizing whitespace when reading them, and treat the files as immutable until new upstream Sqitch releases require updated expectations.
