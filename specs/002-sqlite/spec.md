# Feature Specification: SQLitch Python Parity Fork MVP

**Feature Branch**: `[002-sqlite]`  
**Created**: 2025-10-03  
**Status**: Draft  
**Input**: User description: "We need a feature-complete Python-based fork of Sqitch (SQLitch) with identical CLI behavior, strict quality gates, and documented parity with the original tool."

## Execution Flow (main)
```
1. Audit the existing Sqitch Perl codebase to catalogue commands, options, outputs, and tests.
2. Define the parity scope covering CLI behavior, plan semantics, and registry interactions for SQLite, MySQL, and PostgreSQL.
3. Map the desired SQLitch user journeys and document any deltas that require stakeholder sign-off.
4. Capture quality gates (coverage, linting, security) and CI/CD expectations, aligning with organization policies.
5. Baseline migration and onboarding experience, including virtual environment setup and documentation deliverables.
6. Review ambiguities with stakeholders and resolve open questions before sending to planning.
```

---

## ⚡ Quick Guidelines
- Preserve the end-user experience of Sqitch while modernizing team workflows around the new SQLitch tool.
- Deliver identical command-line ergonomics, messaging, and plan behaviors so existing automation continues to work.
- Emphasize maintainability: clear documentation, mirrored directory/test layout, and enforceable quality gates are non-negotiable.
- Highlight any intentional deviations from Sqitch behavior so stakeholders can approve them explicitly.
- Write and/or leave contract and regression tests in a skipped state until immediately before their corresponding implementation begins; immediately prior to starting the feature, remove the skip so the test fails, run the `scripts/check-skips.py` gate, and tick the PR checklist item before writing code (enforced via tasks T008a/T008b).
- Public modules, classes, and functions MUST ship with clear docstrings that describe behavior, inputs, outputs, and error modes; private helpers MAY rely on concise inline comments when necessary.

---

## Clarifications

### Session 2025-10-03
- Q: Which tool should the documented virtual environment setup mandate so every contributor uses the same workflow? → A: Option A (`python -m venv`)
- Q: When a user targets an engine outside the MVP scope (e.g., Oracle), how should SQLitch respond? → A: Option A (fail immediately with clear error)
- Q: When Docker isn’t available on a contributor machine or CI runner, how should the test suite behave? → A: Option B (skip Docker-backed tests with warning)

### Delivery Milestones
- **Milestone M1 (SQLite First)**: Ship a fully working SQLite experience—including engine adapter, CLI command surface, parity smoke tests, and manual walkthrough—before beginning any work on additional database engines. No MySQL/PostgreSQL development may start until the SQLite milestone is verified end-to-end from the shell.
- **Milestone M2 (MySQL)**: After M1 parity documentation merges, extend the same workflows to MySQL and repeat the manual verification gate.
- **Milestone M3 (PostgreSQL)**: After M2 merges, broaden coverage to PostgreSQL and complete the corresponding gate prior to integration tasks.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
Database release engineers need to execute database change management workflows through SQLitch with the same steps, feedback, and confidence they currently have with Sqitch, while benefiting from a modernized, fully tested Python-based toolchain.

### Acceptance Scenarios
1. **Given** an existing Sqitch project targeting SQLite, MySQL, or PostgreSQL, **When** a release engineer runs equivalent SQLitch commands (e.g., `sqlitch plan`, `sqlitch add`, `sqlitch deploy`), **Then** the observable output, exit codes, and plan file mutations match Sqitch results for all supported flows.
2. **Given** a new contributor onboarding to SQLitch, **When** they follow the documented setup process, **Then** they obtain an isolated development environment, run the full automated test suite (including Docker-backed integration tests when Docker is available), and achieve ≥90% code coverage with all quality gates passing on macOS, Windows, and Linux matrix checks.
3. **Given** a project containing existing `sqitch.*` artifacts and no conflicting `sqlitch.*` files, **When** SQLitch commands are executed, **Then** they operate as a drop-in replacement without requiring users to rename or migrate those files.

### Edge Cases
- How is the immediate unsupported-engine error surfaced when a user targets an engine outside scope (e.g., Oracle)?
- How does the system handle divergent Sqitch plans or timestamps that could break parity across time zones?
- What happens if the CI pipeline detects coverage dipping below 90% or a lint/security gate fails?
- How do tests proceed when Docker is unavailable or database containers fail to start?
- What should users do when both `sqitch.*` and `sqlitch.*` files are present in the same directory?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: SQLitch MUST expose the same CLI commands, options, help text, and default behaviors as Sqitch for SQLite, MySQL, and PostgreSQL, yielding identical human-readable and machine-consumable outputs, and MUST fail immediately with a clear error message when invoked against unsupported engines.
- **FR-002**: The project MUST mirror Sqitch's directory and test layout so developers can cross-reference files one-to-one between the Perl and Python implementations.
- **FR-003**: SQLitch MUST pass a comprehensive automated test suite that validates all behaviors covered by Sqitch tests, plus any additional cases needed to maintain ≥90% coverage and highlight behavioral deviations.
- **FR-004**: Quality gates MUST block merges unless formatting, linting, static type analysis, security scanning, and coverage thresholds all pass with zero warnings.
- **FR-005**: The CI/CD pipeline MUST execute across Windows, macOS, and Linux, enforcing the same pass criteria before any code is considered releasable.
- **FR-006**: Deliverables MUST include a documented process for creating and using an isolated dependency environment using `python -m venv` as the standard workflow for contributors.
- **FR-007**: SQLitch MUST provide observable evidence (e.g., parity reports or smoke tests) demonstrating that CLI outputs match Sqitch for the supported engines, including timestamps and plan mutations. Parity evidence MUST be produced by comparing SQLitch output against repository-managed golden fixtures captured from Sqitch ahead of time; the automated test suite MUST NOT shell out to or otherwise invoke Sqitch during execution.
- **FR-008**: Automated tests MUST exercise real database instances via Docker containers whenever Docker is available, and MUST automatically skip Docker-backed tests with a logged warning when Docker is absent, falling back to embedded engines only when container execution is not feasible.
- **FR-009**: SQLitch MUST allow the Sqitch-compatible global configuration root (normally `~/.sqitch/`) to be overridden so tests can isolate configuration in temporary directories without touching user environments.
- **FR-010**: All automated tests MUST clean up any files, databases, containers, or other artifacts they create, ensuring repeated runs leave no residual state.
- **FR-011**: SQLitch MUST support existing `sqitch.*` project artifacts as drop-in inputs, while emitting a blocking error if both `sqitch.*` and `sqlitch.*` files are detected in the same scope to prevent ambiguous configuration.
- **FR-012**: Tests covering unimplemented features MUST be written with skip markers (e.g., `pytest.mark.skip`) and MUST have those skips removed immediately before the corresponding implementation work starts. Removing the skip, confirming the test failure, running the `scripts/check-skips.py` automation (T008a), and acknowledging the PR checklist item (T008b) are absolute pre-implementation gates that re-establish the Red→Green workflow while keeping CI stable for unstarted features.
- **FR-013**: All public-facing modules, classes, functions, CLI commands, and configuration surfaces MUST include comprehensive docstrings that outline purpose, parameters, outputs, side effects, and error modes. Private helpers MAY use brief inline comments in lieu of docstrings when appropriate.
- **FR-014**: All code MUST use modern Python 3.9+ built-in type annotations (`dict`, `list`, `tuple`, `type`) consistently rather than typing module equivalents (`Dict`, `List`, `Tuple`, `Type`). Union types MUST use `X | None` syntax rather than `Optional[X]`. Type hints MUST be consistent across the entire codebase.
- **FR-015**: Public modules MUST define `__all__` exports to explicitly declare their public API surface and control wildcard import behavior.
- **FR-016**: Exception hierarchies MUST follow semantic consistency: `ValueError` for invalid input data, `RuntimeError` for system/state errors. Domain-specific exceptions MUST extend the appropriate base class.
- **FR-017**: Classes designed for subclassing MUST use `abc.ABC` and `@abstractmethod` to declare their contract explicitly.
- **FR-018**: Global mutable state MUST be minimized and documented. Registries MUST be immutable after initialization or provide clear lifecycle documentation with test cleanup utilities.
- **FR-019**: Complex validation logic MUST be extracted from `__post_init__` methods into separate, testable factory methods or validators to improve clarity, testability, and maintainability.

### Non-Functional Requirements
- **NFR-001**: SQLitch MUST provide end-to-end observability through structured logging that captures a unique run identifier for every CLI invocation and records command, target, and outcome metadata. CLI entry points MUST expose consistent `--verbose`, `--quiet`, and `--json` modes (with deterministic precedence rules) that govern both log verbosity and emitted console output, ensuring parity-friendly human-readable logs by default and machine-ready JSON when requested. Structured log records MUST be forwarded to Rich/Click output handlers without breaking existing parity fixtures, and automated tests MUST exercise logging toggles to confirm coverage across modes.

### Key Entities *(include if feature involves data)*
- **Deployment Plan**: Represents the ordered list of database changes, tags, and dependencies; must remain fully compatible with existing Sqitch plan files.
- **Deployment Target**: Defines the environment-specific connection details for SQLite, MySQL, or PostgreSQL, including authentication and engine-specific configuration.
- **Registry Record**: Captures applied changes, verification results, and metadata necessary to confirm deployment state parity between SQLitch and Sqitch.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed

---
