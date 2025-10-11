# Changelog

All notable changes to this project will be documented in this file. The project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2025-10-11

### Highlights
- Achieved full SQLite tutorial parity with Sqitch, including support for reworked changes and byte-for-byte change ID compatibility.
- Delivered manual forward and backward compatibility harnesses that confirm Sqitch ↔ SQLitch interoperability using the official tutorial workflow.
- Raised core module coverage to 92% and refreshed documentation, security posture, and developer tooling in preparation for the 1.0.0 tag.

### Added
- Shared UAT helper modules (`uat/sanitization.py`, `uat/comparison.py`, `uat/test_steps.py`) with full unit test coverage.
- Forward (`uat/forward-compat.py`) and backward (`uat/backward-compat.py`) compatibility scripts, alongside sanitized log artifacts for release evidence.
- API reference (`docs/API_REFERENCE.md`) and architecture guidance for UAT parity flows (`docs/architecture/uat-compatibility-testing.md`).

### Changed
- CLI workflow now mirrors Sqitch messaging for deploy, revert, status, and rework commands, including target resolution and symbolic reference handling.
- Plan parser and registry flows accept duplicate change names, matching Sqitch rework semantics and dependency tracking.
- SQLite engine enables `PRAGMA foreign_keys = ON` consistently to match Sqitch cascade behavior during reverts and redeployments.

### Fixed
- Corrected change ID generation to include project URI and parent identifiers, eliminating interoperability gaps uncovered by UAT harnesses.
- Hardened CLI error handling during init/add/deploy flows and resolved regression gaps captured by new lockdown tests.
- Patched registry state transitions to remain deterministic across deploy/revert/rework cycles.

### Documentation
- README, CONTRIBUTING, and security guidance updated with lockdown workflow, manual UAT gates, and audit findings.
- Release collateral prepared in `docs/reports/v1.0.0-release-notes.md` and `docs/reports/v1.0.0-migration-guide.md`.
- Quickstart instructions refreshed to include compatibility script execution and evidence capture expectations.

### Quality & Security
- Test coverage sits at 92% with 1,066 tests passing; full suite validated via `pytest --cov=sqlitch`.
- Manual UAT evidence stored under `specs/005-lockdown/artifacts/uat/` (side-by-side, forward, backward logs) confirms behavioral parity.
- `pip-audit` and `bandit` findings triaged; outstanding pip advisory (CVE-2025-8869) documented pending upstream fix.
