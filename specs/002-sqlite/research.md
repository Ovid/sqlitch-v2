# Research Log: SQLitch Python Parity Fork MVP

## Decision: Primary Language and CLI Toolkit
- **Outcome**: Adopt Python 3.11 with Click for top-level command orchestration.
- **Rationale**: Click offers nested command groups, rich help formatting, and straightforward parity with Sqitch’s option handling while remaining battle-tested across platforms.
- **Alternatives Considered**:
  - Typer: modern but introduces dependency on annotations and auto-help wording that diverges from Sqitch copy.
  - argparse: stdlib but would require extensive manual scaffolding to match Sqitch UX.

## Decision: Packaging & Layout
- **Outcome**: Mirror Sqitch directories (`bin/`, `docs/`, `etc/`, `xt/`) directly at the repository root while keeping the Python package rooted at a top-level `sqlitch/` directory.
- **Rationale**: Preserves developer muscle memory, avoids confusing double-nested paths, and still keeps parity-friendly cross-references between module subdirectories and the Perl codebase.
- **Alternatives Considered**: Consolidating under `src/sqlitch` (Pythonic default) would diverge from Sqitch layout and complicate parity reviews.

## Decision: Registry & Engine Connectors
- **Outcome**: Use stdlib `sqlite3`, `psycopg[binary]` for PostgreSQL, and `PyMySQL` for MySQL with SQLAlchemy Core for SQL generation/parity.
- **Rationale**: These drivers are synchronous (matching Sqitch flow), work with Docker-hosted databases, and—critically for contributor onboarding—`PyMySQL` installs without native client libraries on macOS/Linux CI.
- **Alternatives Considered**:
  - asyncpg / aiomysql: async models misalign with Sqitch synchronous execution.
  - mysqlclient: libmysql-backed and faster, but rejected after install failures on clean macOS machines due to missing headers; deemed too high-friction for collaborators.

## Decision: Configuration Management
- **Outcome**: Represent configuration via Pydantic models loading from `sqlitch.conf`, `sqitch.conf`, or environment variables with overrideable root directory support.
- **Rationale**: Typed models expose validation errors early and allow tests to swap configuration roots without mutating real home directories.
- **Alternatives Considered**: Raw dict parsing would duplicate validation logic and increase defect risk.

## Decision: Docker-Orchestrated Testing
- **Outcome**: Provide Docker Compose definitions and pytest fixtures that start containers for MySQL and PostgreSQL; skip with warning when Docker cannot be reached.
- **Rationale**: Ensures parity coverage with real engines while honoring environments without Docker access (per spec).
- **Alternatives Considered**: Service mocks would violate constitution’s realism guidance; full VM orchestration is heavier and slower for CI.

## Decision: Timestamp & Plan Semantics
- **Outcome**: Reuse Perl Sqitch plan parsing rules by porting logic verbatim into Python (with unit tests comparing sample plan files) and enforce identical timestamp formatting via `datetime` + `pytz` (or zoneinfo) utilities.
- **Rationale**: Timestamp fidelity is critical for parity; direct comparison tests reduce drift risk.
- **Alternatives Considered**: Relying on Python defaults risks locale/timezone divergence.

## Open Follow-Ups
- Document official PyPI publishing strategy post-MVP (out of current scope).
- Track potential performance regression tests for `PyMySQL` vs `mysqlclient`; initial manual parity shows acceptable latency, but integration benchmarks are still pending.
