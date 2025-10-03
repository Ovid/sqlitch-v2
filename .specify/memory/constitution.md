# SQLitch Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)
- Tests MUST be written before implementation (Red→Green→Refactor).
- Every new feature/bugfix PR MUST include failing tests that define behavior.
- Contract/integration tests MUST cover user-visible flows and CLI contracts.
- Unused or untested code MUST NOT be merged.
	Rationale: Defining behavior in tests first creates living specifications and prevents regressions while enabling safe refactors.

- Mocks and stubs SHOULD be avoided. Tests MUST exercise real interfaces (CLI
	commands and library entry points) with real files/process boundaries whenever
	feasible.
- Test doubles are permitted ONLY for non-deterministic or external boundaries
	(e.g., network, system time, randomness, external services) and MUST be
	confined behind clear abstraction seams.
- Prefer invoking the actual CLI with temp directories and verifying stdout,
	stderr, and exit codes for end-to-end realism.

### II. CLI-First, Text I/O Contracts
- All functionality MUST be accessible via CLI commands (thin wrappers over libs).
- Inputs: stdin/args; Outputs: stdout; Errors: stderr; Use process exit codes.
- Commands MUST offer human-readable output by default and a `--json` mode.
- CLI commands MUST be composable (no hidden global state, deterministic I/O).
	Rationale: Text I/O maximizes composability, scriptability, and debuggability.

### III. Library-First, Single-Responsibility Modules
- Core logic MUST live in importable libraries; CLI remains a thin shell.
- Libraries MUST be self-contained, independently testable, and documented.
- Cross-module coupling MUST be minimized; avoid "organizational-only" libraries.
	Rationale: Separation improves reuse, testing, and long-term maintenance.

### IV. Semantic Versioning and Compatibility
- Follow SemVer: MAJOR.MINOR.PATCH for public contracts (CLI flags/format/APIs).
- Breaking changes REQUIRE a MAJOR bump and a documented migration plan.
- Additive, backward-compatible changes are MINOR; fixes/clarifications are PATCH.
- Deprecations SHOULD provide at least one MINOR release of overlap when feasible.
	Rationale: Predictable versioning builds trust and reduces upgrade risk.

### V. Observability and Determinism
- Structured logging REQUIRED; `--verbose`/`--quiet` flags MUST be supported.
- `--json` logging mode MUST emit machine-parseable records.
- Given identical inputs and environment, outputs MUST be reproducible.
- Commands SHOULD emit run IDs to correlate logs across tools.
	Rationale: Deterministic behavior and useful telemetry make issues diagnosable.

### VI. Behavioral Parity with Sqitch (Guiding Star)
- The `sqitch/` directory in this repository is the authoritative reference for
	behavior, interfaces, flags, messages, and semantics.
- SQLitch MUST match Sqitch behavior 1:1 unless a documented deviation exists
	with rationale and a migration path.
- Parity includes: plan semantics, deploy/revert/verify behavior, exit codes,
	CLI syntax and help text, and output formats (human and JSON when applicable).
- Tests MUST be derived from or validated against the upstream Sqitch behavior
	to ensure 100% compliance.
	Rationale: Treating Sqitch as a golden source guarantees predictable behavior and
	user familiarity while reducing ambiguity.

### VII. Simplicity-First, No Duplication
- Each change MUST be the simplest thing that can possibly work while maintaining
	100% compatibility with Sqitch behavior and test coverage.
- Features MUST NOT exceed what upstream Sqitch supports; do not add extra flags,
	modes, or behaviors unless a documented deviation exists with migration.
- Simplicity MUST NOT introduce code duplication; prefer reuse, extraction, or
	refactoring over copy-paste.
- Any necessary complexity MUST be justified in Complexity Tracking with rejected
	simpler alternatives.
	Rationale: Simplicity reduces risk and maintenance cost while preserving parity
	and clarity of intent.

## Additional Constraints

- Security: Never log secrets or PII; redact by default and require `--allow-secrets`
	only for explicit debugging use-cases.
- Portability: Tools MUST run on macOS and Linux; avoid OS-specific behavior unless
	guarded and documented.
- Performance: For typical inputs, core commands SHOULD complete in <200ms; long-
	running operations MUST stream progress or provide `--no-progress` for CI.
- Configuration: Respect environment variables and config files under
	`$XDG_CONFIG_HOME/sqlitch/` or `~/.config/sqlitch/`.
- Advisory Clarity: When recommending an approach, explicitly call out any
	potential risks, uncertainties, or reasons it might be a bad idea, and explain
	the rationale so reviewers can evaluate the trade-offs.
- Skip Lifecycle Discipline: Tests for unimplemented features MAY be committed
	with skip markers, but removing those skips is a mandatory pre-implementation
	gate. Before any implementation task begins, the responsible engineer MUST
	delete the related skip marker(s), confirm the test fails, and treat the
	unskipped failure as part of the Red→Green→Refactor loop.

## Development Workflow & Quality Gates

- Workflow: Spec → Plan → Design (contracts, data model, quickstart) → Tasks →
	Implementation → Validation.
- Constitution Check: Plans MUST document an initial and post-design constitution
	check. Violations MUST be justified in Complexity Tracking or removed.
- PR Gate: CI MUST run tests and enforce formatting/linting; reviewers MUST check
	compliance with principles and governance.
- Test Realism: Tests SHOULD prefer real CLI invocation and real filesystem
	operations; avoid mocking unless covering non-deterministic/external boundaries.
- Simplicity Gate: Implementation MUST be minimal, avoid duplication, and add no
	capability beyond Sqitch unless explicitly justified and approved.
- Documentation: Each feature MUST update quickstart and, when applicable,
	contracts and data-model docs.

## Governance

- Authority: This constitution supersedes other conventions in this repository.
- Amendment Procedure: Amend via PR updating `.specify/memory/constitution.md`.
	The PR MUST include a Sync Impact Report (as an HTML comment) summarizing the
	version change, modified/added/removed sections, template update status, and
	any deferred TODOs.
- Versioning Policy: Use SemVer for the constitution itself.
	• MAJOR: Backward-incompatible governance/principle removals or redefinitions.
	• MINOR: Add or materially expand a principle/section.
	• PATCH: Clarifications, wording, or non-semantic refinements.
- Compliance: All specs, plans, tasks, and PRs MUST reference and adhere to this
	document. Non-compliance is a change request, not a discretionary choice.

**Version**: 1.3.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date unknown | **Last Amended**: 2025-10-03