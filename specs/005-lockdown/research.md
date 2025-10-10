# Research Notes: Quality Lockdown and Stabilization

## Decision Log

### UAT Compatibility Scope
- **Decision**: Limit all compatibility scripts (side-by-side, forward, backward) to the SQLite tutorial workflow documented in `sqitch/lib/sqitchtutorial-sqlite.pod`.
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
