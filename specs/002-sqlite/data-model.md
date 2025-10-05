# Data Model: SQLitch Python Parity Fork MVP

## Overview
SQLitch mirrors Sqitch’s file-based plan semantics and registry tables while exposing them through Python domain objects. This document defines the core entities, their attributes, and lifecycle transitions that must hold true across SQLite, MySQL, and PostgreSQL engines.

## Entities

### Change
- **Attributes**:
  - `change_id` (UUID v4): unique deployment identifier generated at `sqlitch add`
  - `name` (string): human-readable change name (must be unique within plan)
  - `script_paths` (dict): `{"deploy": Path, "revert": Path, "verify": Optional[Path]}` referencing on-disk scripts
  - `dependencies` (list[str]): change names that must precede this change
  - `tags` (list[str]): tag names applied at creation time
  - `planner` (string): username/email captured at creation
  - `planned_at` (datetime, UTC): timestamp formatted identical to Sqitch (ISO 8601 with TZ)
  - `notes` (Optional[str]): textual description copied into plan file
- **Relationships**: belongs to exactly one `Plan`; may reference `Tag` entities by name
- **Invariants**:
  - `change_id` uniqueness enforced per registry
  - Deploy/revert scripts must exist and be executable; verify optional but tracked

### Plan
- **Attributes**:
  - `project_name` (string): canonical name pulled from plan header
  - `file_path` (Path): location of `plan` file (supports `sqitch.plan` and `sqlitch.plan`)
  - `entries` (list[PlanEntry]): ordered union of `Change` and `Tag` entries
  - `checksum` (string): hashed representation used for drift detection
  - `default_engine` (string): engine alias resolved from config/CLI
  - `syntax_version` (string): semantic version from `%syntax-version` header (defaults to `1.0.0`)
  - `missing_dependencies` (list[str]): forward references captured as `"{change}->{dependency}"` when a compact Sqitch entry depends on a change that appears later in the file
- **Relationships**: aggregates `Change` and `Tag`; associated with `EngineTarget`
- **State Transitions**:
  - Created by `sqlitch init`
  - Mutated by `sqlitch add|rework|tag`
  - Verified during deploy/revert operations for parity

### Tag
- **Attributes**:
  - `name` (string): tag label (unique within plan)
  - `change_ref` (string): change name the tag references
  - `planner` (string)
  - `tagged_at` (datetime, UTC)
- **Relationships**: attaches to a `Change`; persisted in plan & registry
- **Constraints**: Tag cannot exist without corresponding change; duplicates invalid

### RegistryRecord
- **Attributes**:
  - `engine_target` (string)
  - `change_id` (UUID)
  - `change_name` (string)
  - `deployed_at` (datetime, engine timezone preserved)
  - `planner` (string)
  - `verify_status` (enum: success|failed|skipped)
  - `reverted_at` (Optional[datetime])
- **Relationships**: persisted per engine in backend database (registry tables)
- **Lifecycle**:
  - Added on successful deploy
  - Updated on verify/revert
  - Removal happens via `sqlitch revert --hard`

### EngineTarget
- **Attributes**:
  - `name` (string): friendly alias (e.g., `db:pg`
  - `engine` (enum: sqlite|mysql|pg)
  - `uri` (URL/DSN)
  - `registry_uri` (URL/DSN) (supports overrides)
  - `config_scope` (enum: local|user|system)
  - `env` (dict): resolved environment variables (e.g., passwords)
- **Relationships**: referenced by Plan; used to establish connections for registry & scripts
- **State**:
  - Created or updated by `sqlitch target`
  - Validated during CLI invocation by connection checks

### ConfigProfile
- **Attributes**:
  - `root_dir` (Path): base directory (overrideable for tests)
  - `files` (Ordered list[Path]): resolved file precedence (`sqlitch.conf`, `sqitch.conf`, etc.)
  - `settings` (dict): merged configuration values
  - `active_engine` (str): default target key
- **Usage**: ensures CLI uses deterministic config while supporting drop-in compatibility with existing Sqitch installations

## Relationships Diagram (Textual)
- **Plan** 1..1 — contains —> n **Change**
- **Plan** 1..1 — contains —> n **Tag**
- **Change** 1..n — depends on —> n **Change** (DAG enforced)
- **EngineTarget** 1..n — referenced by —> n **RegistryRecord**
- **ConfigProfile** 1..n — resolves —> n **EngineTarget**

## Validation Rules
- Plan entries must alternate logically (change or tag) following Sqitch semantics; duplicate change names invalid.
- Forward-referenced dependencies encountered while parsing Sqitch-compact entries are preserved in `Plan.missing_dependencies` for downstream commands to surface as warnings instead of hard errors.
- Registry schema identical to Sqitch reference; SQL migrations must match per-engine DDL ordering.
- Credential resolution follows Sqitch precedence: CLI flag → environment → configuration file, with secrets never persisted back to disk or echoed in logs.
- When both `sqitch.plan` and `sqlitch.plan` exist, CLI aborts with explicit error (implemented via config/profile validator).
- Configuration roots default to `$XDG_CONFIG_HOME/sqlitch` (or `~/.config/sqlitch`) but allow override via `SQLITCH_CONFIG_ROOT` env and CLI `--config-root` flag.

## State Transitions Summary
1. `sqlitch init` → creates ConfigProfile, Plan, EngineTargets as defined.
2. `sqlitch add` → appends Change, writes scripts, updates Plan checksum.
3. `sqlitch deploy` → processes Changes in order, writing RegistryRecords, verifying scripts, handling Docker-engine connections when needed.
4. `sqlitch revert`/`rework` → manipulates Plan entries and registry state, ensuring dependencies remain consistent.
5. `sqlitch status|log|show` → read-only operations relying on Plan + Registry data with no mutations.

## Data Volume & Scale Assumptions
- Plans typically <5k entries; operations must handle at least 10k entries efficiently.
- Registry tables expected to grow to millions of rows; SQLAlchemy Core interactions must stream results to avoid loading entire history into memory.
- Dockerized MySQL/PostgreSQL containers provisioned with default resource limits (512MB RAM) for CI parity testing.
