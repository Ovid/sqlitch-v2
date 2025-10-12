# Data Model & Operational Artifacts

## Overview
No new persistent data structures are introduced during the lockdown effort. Work focuses on ensuring existing registries, tutorial databases, and log outputs remain parity-compatible between Sqitch and SQLitch.

## Existing Datastores
| Artifact | Type | Purpose | Notes |
|----------|------|---------|-------|
| `flipr_test.db`, `flipr_prod.db`, `dev/flipr.db` | SQLite databases | Tutorial deployment targets exercised by UAT scripts | Created/cleaned per script run; represent user-visible state comparisons |
| `sqitch.db`, `sqlitch.db` | SQLite registries | Track deployment plan history | Managed by respective tools; UAT ignores schema differences, focusing on user tables |
| `sqitch_results/`, `sqlitch_results/` | Directory trees | Contain working copies for each tool during side-by-side execution | Reused by forward/backward compatibility scripts |
| `sqitch.log`, `sqlitch.log` | Text logs | Record command output and diffs for audit | Sanitized for IDs/timestamps before comparison |

## Log & Evidence Artifacts
- Manual executions must upload or link sanitized logs in the release pull request comment thread (per clarification).
- Optional `--out` flag from `uat/side-by-side.py` produces ANSI-free transcript suitable for sharing with reviewers.

## Shared Helper Modules (Planned)
- `uat/sanitization.py`: timestamp and SHA masking utilities extracted from `side-by-side.py`.
- `uat/comparison.py`: diff helpers for command output and SQLite data snapshots.
- `uat/test_steps.py`: canonical list of tutorial steps to drive all compatibility scripts.

## No Schema Changes
- No migrations or plan changes are introduced; plan files continue using existing repositories under `sqitch/` and `deploy/`.
- All database assertions focus on user-facing tables (`users`, `flips`, `userflips`, `hashtags`) defined in the tutorial SQL files.
