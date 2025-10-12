# Research Notes: Quality Lockdown and Stabilization

## Decision Log

### UAT Compatibility Scope
- **Decision**: Limit all compatibility scripts (side-by-side, forward, backward) to the SQLite tutorial workflow documented in `sqitch/lib/sqitchtutorial-sqlite.pod`.
- **Sqitch Version**: UAT validates against **Sqitch v1.5.3** (vendored in `sqitch/` directory at repository root).
- **Rationale**: Guarantees deterministic parity coverage with the canonical Sqitch tutorial and aligns with the clarified `Scope` requirement.
- **Alternatives Considered**:
  - Run across every supported engine (Postgres/MySQL) — deferred to post-lockdown due to setup cost and unclear parity fixtures.
  - Extend to regression suites beyond the tutorial — rejected for the lockdown milestone to avoid scope creep.

### Manual Execution Cadence
- **Decision**: Treat the compatibility scripts as manual gates executed via the documented release checklist instead of CI automation.
- **Rationale**: Scripts are long-running, rely on external binaries, and benefit from human review of diffs/logs before final approval.
- **Alternatives Considered**:
  - Run on every pull request — rejected for runtime cost and to keep PR feedback fast.
  - Schedule nightly CI jobs — deferred until we measure runtime and flake rate post-lockdown.

### Evidence Capture Channel
- **Decision**: Record each manual run by posting a summary comment on the release pull request, attaching or linking to sanitized logs.
- **Rationale**: Centralizes sign-off in the thread reviewers already monitor and avoids leaking large logs into git history.
- **Alternatives Considered**:
  - Commit logs under `tests/support/tutorial_parity/` — discarded to keep repo clean and avoid churn.
  - Store logs in release notes — lacks pre-merge visibility for reviewers.

## Baseline Quality Signals
- **Pytest + Coverage** (2025-10-10): `pytest --cov=sqlitch` passes with total coverage **91.33%** (report archived in `artifacts/baseline/coverage.xml`). Modules below 90% remain `sqlitch/cli/commands/revert.py` (92% branches but 82% statements), `sqlitch/registry/state.py` (statements 97% but 60% branches), `sqlitch/utils/identity.py` (89% statements) plus several CLI command modules hovering in the high 80s per branch metrics.
- **mypy --strict**: Fails with 40 diagnostics (see `artifacts/baseline/mypy.txt`). Hotspots include type-unsafe `configparser.optionxform` assignments, loose tuple typing in `registry/state.py`, optional handling in SQLite engine helpers, parser metadata variance, redundant casts in `cli/options.py`, and CLI command result typing (verify/target/status/deploy).
- **pydocstyle**: 90+ D202/D102/D105 violations across CLI/config/plan/utils modules (see `artifacts/baseline/pydocstyle.txt`). Docstring backlog largest in `sqlitch/utils/logging.py`, `sqlitch/plan/model.py`, and command registration helpers.
- **pip-audit -f json**: Flags `pip 25.2` with advisory `GHSA-4xh5-x5gv-qwph` (CVE-2025-8869) lacking fix release. JSON stored at `artifacts/baseline/pip-audit.json`; remediation pending upstream 25.3 drop.
- **bandit -r sqlitch**: Exits 1 with 29 findings (report in `artifacts/baseline/bandit.json`). High severity items concentrated in `sqlitch/cli/commands/deploy.py` (shell execution and temp file handling) and medium severities in log emission helpers.
- **pylint sqlitch**: Score blocked by 1300+ messages (see `artifacts/baseline/pylint.txt`). Primary themes: argument/branch counts in CLI commands, missing docstrings, broad exception catches in deploy/log modules, and Windows-specific identity helpers.
- **Tooling gaps**: `pydocstyle` and `pip-audit` were not bundled in `.[dev]`; installed ad hoc to complete baseline. Follow-up task needed to bake them into the dev extra or dedicated requirements file.
- Documentation inventory: README quickstart, CONTRIBUTING, CLI `--help` output, and new UAT workflow docs will require updates once helper modules are extracted (tracked in Phase 3.4).

## Shared Helper Extraction
- Plan to extract common sanitization, comparison, and step-definition helpers for reuse by all UAT scripts under `uat/` (see spec Implementation Details).
- Existing `uat/side-by-side.py` already contains sanitization logic that can be modularized with minimal refactoring.

## Pylint Analysis Baseline (2025-10-12)

### Summary Statistics
- **Total Issues**: 286
- **Pylint Score**: 9.29/10 (strong baseline)
- **Issue Breakdown by Type**:
  - Errors: 25 (most are false positives from Click decorators and conditional imports)
  - Warnings: 90 (primarily unused arguments, broad exception catches)
  - Refactor: 141 (mainly complexity metrics and duplicate code)
  - Convention: 30 (mostly docstring formatting issues)

### Top Issue Symbols
1. **unused-argument (67)**: Function parameters not used, often in command handlers where Click/context provides them
2. **duplicate-code (56)**: Similar code blocks across multiple files, primarily in CLI command modules
3. **too-many-locals (33)**: Functions with >15 local variables, concentrated in config loader and CLI commands
4. **missing-kwoa (20)**: False positives from Click decorator parameter handling
5. **too-many-arguments (16)**: Functions with >5 arguments, mostly in CLI command implementations
6. **import-outside-toplevel (13)**: Dynamic imports needed for engine/platform-specific modules
7. **broad-exception-caught (13)**: Generic exception handlers in deployment and logging code

### Files with Highest Issue Density
Top 10 files by total issue count:
1. `sqlitch/engine/mysql.py` - 56 issues (all duplicate-code from postgres engine similarity)
2. `sqlitch/cli/commands/deploy.py` - 26 issues (6W, 18R, 2C)
3. `sqlitch/cli/commands/revert.py` - 26 issues (11W, 11R, 4C)
4. `sqlitch/cli/commands/verify.py` - 14 issues
5. `sqlitch/cli/commands/status.py` - 14 issues
6. `sqlitch/cli/main.py` - 13 issues (11E false positives from Click)
7. `sqlitch/utils/identity.py` - 12 issues (2E from Windows conditional imports)
8. `sqlitch/cli/__main__.py` - 11 issues (all E false positives)
9. `sqlitch/cli/commands/rebase.py` - 11 issues
10. `sqlitch/cli/commands/plan.py` - 10 issues

### Error-Level Issues Analysis
**25 errors identified, categorized as follows:**

#### False Positives (23 errors - 92%)
1. **Click decorator parameter handling (22 errors)**:
   - `sqlitch/cli/main.py:307` - 11 errors about missing kwargs in `main()` call
   - `sqlitch/cli/__main__.py:8` - 11 errors about missing kwargs in `main()` call
   - **Rationale**: Click decorators (@click.command, @click.option) inject these parameters at runtime
   - **Action**: Suppress with inline comments documenting Click's parameter injection

2. **Conditional Windows imports (2 errors)**:
   - `sqlitch/utils/identity.py:237` - `win32api` possibly used before assignment
   - `sqlitch/utils/identity.py:384` - `win32net` possibly used before assignment
   - **Rationale**: These modules are conditionally imported at module level with `sys.platform == "win32"` guard
   - **Action**: Suppress with inline comments documenting platform-specific import pattern

#### Legitimate Issues (1 error - 4%)
1. **Type safety issue (1 error)**:
   - `sqlitch/plan/parser.py:70` - Invalid sequence index (not int, slice, or has __index__)
   - **Description**: Using `entries[last_change_index]` where type checker cannot verify index safety
   - **Action**: Add proper type guard or assertion to validate index before use

### Recommended Pylint Configuration
Based on baseline analysis, recommended suppressions for `.pylintrc`:
- Disable `missing-kwoa` globally (Click framework false positives)
- Disable `no-value-for-parameter` for CLI entry points (Click decorator injection)
- Increase `max-locals` threshold to 20 (config/loader legitimately complex)
- Increase `max-args` threshold to 7 (CLI commands have many options)
- Allow platform-specific imports for `import-outside-toplevel` in identity.py
- Configure `duplicate-code` minimum lines to 10 (reduce noise from short similar blocks)

### Priority Areas for Improvement
1. **High Priority**: Fix legitimate error in `plan/parser.py:70` (type safety)
2. **Medium Priority**: Reduce duplicate code between mysql.py and postgres.py engines (56 violations)
3. **Medium Priority**: Address broad exception catches in deploy.py and logging modules (13 violations)
4. **Low Priority**: Refactor complex functions with too many locals/arguments (cosmetic improvements)
5. **Documentation**: Add docstrings for 11 missing function docstrings

### Pylint Integration Plan
1. **Baseline Captured**: `pylint_report.json` saved to repository root (3720 lines)
2. **Configuration Task**: Create `.pylintrc` with recommended suppressions (separate task)
3. **Tracking Strategy**: Document legitimate issues as separate tasks in tasks.md
4. **CI Integration**: Defer until baseline issues addressed (avoid failing CI on known issues)
5. **Improvement Cadence**: Address issues in batches by category during post-alpha cleanup

### Notes
- Pylint analysis is **supplemental** to the core lockdown effort (not blocking alpha release)
- High score (9.29/10) indicates generally good code quality
- Most errors are tool false positives, not code defects
- Focus on **legitimate issues** (1 type safety error) and **high-impact warnings** (duplicate code, broad exceptions)
- Full pylint integration can be phased in post-alpha to avoid scope creep

```
