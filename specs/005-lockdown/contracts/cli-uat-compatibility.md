# CLI Contract: UAT Compatibility Scripts

## Command Matrix
| Script | Step Source | Next Step Runner | Command Pattern | Expected Exit | Notes |
|--------|-------------|------------------|-----------------|---------------|-------|
| `uat/side-by-side.py` | Parallel (sqitch & sqlitch for same step) | Parallel | `python uat/side-by-side.py [--continue] [--out <file>] [--ignore <steps>]` | 0 | Sanitizes timestamps/SHA1, compares user tables only |
| `uat/forward-compat.py` | sqlitch | sqitch | `python uat/forward-compat.py [--out <file>]` | 0 | After each sqlitch action, sqitch repeats the next tutorial step |
| `uat/backward-compat.py` | sqitch | sqlitch | `python uat/backward-compat.py [--out <file>]` | 0 | After each sqitch action, sqlitch repeats the next tutorial step |

## Acceptance Criteria
1. Each script exits with code 0 under the standard SQLite tutorial workflow.
2. Sanitized outputs produce no behavioral diffs (only cosmetic differences allowed and documented).
3. SQLite user-facing tables (`users`, `flips`, `userflips`, `hashtags`) remain byte-equivalent across tools after each step.
4. Logs capture the command sequence, sanitized output, and any ignored steps.
5. Manual execution evidence is posted in the release PR comment with links to sanitized logs.

## Failure Handling Expectations
- On behavioral divergence, scripts must halt with non-zero exit code and retain working directories for inspection.
- `--continue` flag allows the run to finish while marking failure; exit code remains non-zero if any step failed.
- Documentation must guide engineers to inspect `sqitch.log`, `sqlitch.log`, and the generated SQLite databases inside `sqitch_results/` and `sqlitch_results/`.
