# Sqitch Parity Golden Fixtures

These fixtures capture canonical Sqitch outputs that we will diff against the Python implementation during parity tests (FR-007). The data was collected from the upstream Sqitch project to avoid invoking the Perl toolchain at test time.

## Layout

- `plans/` – Reference plan files with pragmas, dependencies, tags, and whitespace edge cases.
- `registry/` – Text snapshots of Sqitch registry-driven commands (`status`, `verify`, `log`). Each engine has its own subdirectory (currently only `sqlite/`). The SQLite directory also contains a structured logging sample (`deploy_structured_log.jsonl`) that captures the JSON payloads emitted during an atomic deploy, including the resolved registry URI and `transaction_scope` metadata required for parity checks.
- `tutorial_parity/` – Canonical outputs from the Sqitch SQLite tutorial after each major command (`deploy`, `status`, `log`, `verify`, `revert`, `tag`, `rework`). Each command snapshot preserves the tutorial plan (`*.plan`), registry dump (`*.sql`), and stdout capture so parity regressions can diff SQLitch output byte-for-byte.

## Provenance

Plan fixtures are adapted directly from Sqitch's test plans under `sqitch/t/plans/`. Registry snapshots were transcribed from the official Sqitch SQLite tutorial (`sqitch/lib/sqitchtutorial-sqlite.pod`) to preserve real command output formatting and timestamps.

## Regenerating Fixtures

1. Install the Perl-based Sqitch CLI.
2. Re-run the commands documented alongside each fixture, capturing stdout.
3. Overwrite the corresponding file in this directory.
4. Keep trailing whitespace, indentation, and blank lines intact so parity comparisons stay stable.

### Tutorial Parity Refresh Checklist

The `tutorial_parity/` tree mirrors the SQLite tutorial from `sqitch/lib/sqitchtutorial-sqlite.pod`. To refresh the fixtures:

1. Create a fresh working directory and run the tutorial exactly as documented (init → add → deploy → verify → status → revert → log → tag → rework), targeting SQLite.
2. After each command of interest, capture:
	- **stdout**: pipe the command output to the matching `stdout.txt` file (e.g., `sqitch status db:sqlite:flipr.db | tee stdout.txt`).
	- **plan**: copy the full `sqitch.plan` (including pragmas such as `%default_engine`) into the relevant `*.plan` fixture.
	- **registry**: dump the Sqitch registry (`sqlite3 sqitch.db .dump`) and trim it to the schema relevant for the snapshot (`registry.sql` or `registry_before.sql`).
3. Keep the capture order consistent with directory names so regression tests can locate the correct fixtures without extra metadata.
4. Commit the refreshed files together with a short note referencing the Sqitch release or tutorial revision used as the source.

## Usage Notes

Test helpers will load these files verbatim and compare SQLitch output byte-for-byte. Avoid normalizing whitespace when reading them, and treat the files as immutable until new upstream Sqitch releases require updated expectations.
