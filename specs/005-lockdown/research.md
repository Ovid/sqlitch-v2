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
- Test coverage currently **91.33%** (see `BASELINE_ASSESSMENT.md`); key modules under 90% are `sqlitch/config/resolver.py`, `sqlitch/registry/state.py`, and `sqlitch/utils/identity.py`.
- Security tooling in scope: `pip-audit`, `bandit`, and targeted greps for risky patterns.
- Documentation inventory: README quickstart, CONTRIBUTING, CLI `--help` output, and additional UAT guidance to be generated.

## Shared Helper Extraction
- Plan to extract common sanitization, comparison, and step-definition helpers for reuse by all UAT scripts under `uat/` (see spec Implementation Details).
- Existing `uat/side-by-side.py` already contains sanitization logic that can be modularized with minimal refactoring.
