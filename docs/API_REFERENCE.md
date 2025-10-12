# SQLitch API Reference

**Version**: Pre-1.0 (Lockdown Phase)  
**Last Updated**: 2025-10-11  
**Target Audience**: Developers extending SQLitch or integrating it as a library

---

## Overview

This document provides a reference for SQLitch's public Python API. While SQLitch is primarily a CLI tool, its modules can be imported and used programmatically for custom database migration workflows.

**Important**: The API is not yet stable. Breaking changes may occur before v1.0.

---

## Core Modules

### `sqlitch.config`

Configuration loading and resolution with Sqitch-compatible precedence.

#### `sqlitch.config.loader`

**`load_config(root_dir, scope_dirs, config_filenames=None) -> ConfigProfile`**

Load configuration across scopes and merge with precedence.

- **Parameters:**
  - `root_dir`: The primary project directory
  - `scope_dirs`: Mapping of ConfigScope to directories containing config files
  - `config_filenames`: Optional tuple of config filenames to search (defaults to `("sqitch.conf", "sqlitch.conf")`)
- **Returns:** ConfigProfile with merged configuration
- **Raises:** `ConfigConflictError` if multiple config files exist in same scope

#### `sqlitch.config.resolver`

**`resolve_config(root_dir, config_root=None, env=None, home=None, system_path=None, config_filenames=None) -> ConfigProfile`**

Resolve configuration scope directories and load a profile.

- **Parameters:**
  - `root_dir`: Project root directory
  - `config_root`: Optional config root override
  - `env`: Optional environment mapping
  - `home`: Optional home directory override
  - `system_path`: Optional system config path
  - `config_filenames`: Optional config filename sequence
- **Returns:** Resolved ConfigProfile

**`resolve_registry_uri(engine, workspace_uri, project_root, registry_override=None) -> str`**

Return the canonical registry URI for the given engine target.

**`resolve_credentials(target=None, profile=None, env=None, cli_overrides=None) -> CredentialResolution`**

Resolve credential values using CLI overrides, environment, and config in order.

---

### `sqlitch.plan`

Plan file parsing, validation, and formatting.

#### `sqlitch.plan.parser`

**`parse_plan(plan_path, project_root=None) -> Plan`**

Parse a sqitch.plan file into a Plan object.

- **Parameters:**
  - `plan_path`: Path to the plan file
  - `project_root`: Optional project root for resolving script paths
- **Returns:** Plan object with changes, tags, and metadata
- **Raises:** `PlanParseError` on syntax errors

#### `sqlitch.plan.model`

**`Change`** (dataclass)

Represents a single database change with metadata.

- **Attributes:** `name`, `id`, `timestamp`, `planner_name`, `planner_email`, `note`, `requires`, `conflicts`, `suffix`, `deploy_script`, `revert_script`, `verify_script`
- **Factory:** `Change.create(...)` - Create change with validation

**`Plan`** (dataclass)

Represents a complete migration plan.

- **Attributes:** `project`, `uri`, `default_engine`, `items`
- **Methods:** 
  - `changes() -> list[Change]`: All changes in order
  - `tags() -> list[Tag]`: All tags in order
  - `get_change(name) -> Change`: Retrieve change by name
  - `has_change(name) -> bool`: Check if change exists

#### `sqlitch.plan.formatter`

**`format_plan(plan) -> str`**

Render a Plan object back to Sqitch plan file format.

**`compute_checksum(plan_content) -> str`**

Calculate SHA1 checksum of plan content.

**`write_plan(plan, output_path)`**

Write plan to file with proper formatting.

---

### `sqlitch.engine`

Database engine adapters and registry management.

#### `sqlitch.engine.base`

**`ENGINE_REGISTRY`** (dict)

Global registry of available engine adapters.

**`get_engine(engine_name) -> EngineAdapter`**

Retrieve engine adapter by name.

**`register_engine(name, adapter_class, replace=False)`**

Register a new engine adapter.

**`EngineAdapter`** (ABC)

Base class for all engine adapters.

- **Abstract Methods:**
  - `initialize_registry(registry_uri)`: Create registry schema
  - `deploy_change(change, workspace_uri)`: Deploy a change
  - `revert_change(change, workspace_uri)`: Revert a change
  - `verify_change(change, workspace_uri)`: Verify a change
  - `get_deployed_changes(registry_uri) -> list[RegistryEntry]`: Query registry

#### `sqlitch.engine.sqlite`

**`SQLiteEngine`**

SQLite-specific engine implementation.

- **Methods:** All EngineAdapter methods plus SQLite-specific helpers

---

### `sqlitch.registry`

Registry state management and migrations.

#### `sqlitch.registry.state`

**`RegistryEntry`** (dataclass)

Represents a single deployed change in the registry.

- **Attributes:** `project`, `change_id`, `change_name`, `committed_at`, `committer_name`, `committer_email`, `planned_at`, `planner_name`, `planner_email`, `script_hash`, `note`

**`RegistryState`**

In-memory view of registry entries.

- **Methods:**
  - `record_deploy(entry)`: Add deployment record
  - `remove_change(change_id)`: Remove change (after revert)
  - `get_record(change_id) -> RegistryEntry`: Retrieve entry
  - `records() -> Sequence[RegistryEntry]`: All entries in order

**`deserialize_registry_rows(rows) -> Sequence[RegistryEntry]`**

Convert registry query rows into RegistryEntry instances.

**`serialize_registry_entries(entries) -> list[dict]`**

Render entries as dictionaries matching Sqitch schema.

#### `sqlitch.registry.migrations`

**`get_registry_migrations(engine) -> tuple[RegistryMigration, ...]`**

Return ordered registry migrations for the given engine.

**`list_registry_engines() -> tuple[str, ...]`**

Return canonical list of engines with registry migrations.

---

### `sqlitch.utils`

Shared utilities for identity, time, templates, and logging.

#### `sqlitch.utils.identity`

**`generate_change_id(project, change, timestamp, planner_name, planner_email, note="", requires=(), conflicts=()) -> str`**

Generate a unique change ID using Git-style SHA1 hash.

**`get_current_user() -> tuple[str, str]`**

Return current user's name and email from Git config or system.

#### `sqlitch.utils.time`

**`ensure_timezone(dt) -> datetime`**

Ensure datetime has timezone info (assumes UTC if missing).

**`parse_iso_datetime(text) -> datetime`**

Parse ISO8601 datetime string.

**`isoformat_utc(dt) -> str`**

Format datetime as ISO8601 in UTC.

#### `sqlitch.utils.templates`

**`resolve_template_path(template_name, project_root, config) -> Path`**

Resolve template file path from configured directories.

**`render_template(template_path, context) -> str`**

Render template with given context variables.

**`write_default_templates(target_dir, script_type)`**

Write default deploy/revert/verify templates to directory.

#### `sqlitch.utils.logging`

**`create_logger(name, level="INFO") -> StructuredLogger`**

Create a logger with structured output support.

**`StructuredLogger`**

Logger with JSON-structured output methods.

- **Methods:** `trace()`, `debug()`, `info()`, `warning()`, `error()`, `critical()`

---

## CLI Entry Points

### `sqlitch.cli.main`

**`main()`**

Main CLI entry point (invoked via `sqlitch` command).

- Uses Click for command routing
- Loads configuration and context
- Dispatches to command handlers

---

## UAT Helper Modules

### `uat.sanitization`

**`sanitize_timestamps(text) -> str`**

Replace ISO8601 timestamps with `<TIMESTAMP>` placeholder.

**`sanitize_sha1(text) -> str`**

Replace 40-character SHA1 hashes with `<CHANGE_ID>` placeholder.

**`sanitize_output(text) -> str`**

Apply all sanitization rules for output comparison.

**`strip_ansi_codes(text) -> str`**

Remove ANSI color/formatting codes from text.

### `uat.comparison`

**`compare_command_output(sqitch_out, sqlitch_out) -> DiffResult`**

Compare sanitized command outputs.

**`compare_sqlite_tables(db1_path, db2_path, tables) -> bool`**

Validate data equivalence between SQLite databases.

**`is_cosmetic_difference(diff) -> bool`**

Classify differences as cosmetic vs behavioral.

### `uat.test_steps`

**`get_tutorial_steps() -> list[dict]`**

Return ordered list of Sqitch tutorial steps.

**`get_step_by_name(name) -> dict`**

Retrieve specific tutorial step configuration.

---

## Usage Examples

### Programmatic Plan Parsing

```python
from pathlib import Path
from sqlitch.plan.parser import parse_plan

# Parse a plan file
plan = parse_plan(Path("sqitch.plan"), project_root=Path("."))

# Access changes
for change in plan.changes():
    print(f"{change.name}: {change.note}")
```

### Configuration Resolution

```python
from sqlitch.config.resolver import resolve_config

# Resolve configuration with environment and precedence
config = resolve_config(
    root_dir=Path("."),
    env={"SQLITCH_USER_NAME": "Test User"}
)

# Access config values
user_name = config.get("user.name")
```

### Registry State Management

```python
from sqlitch.registry.state import RegistryState, RegistryEntry
from datetime import datetime, timezone

# Create registry state
state = RegistryState()

# Record deployment
entry = RegistryEntry(
    project="myproject",
    change_id="abc123...",
    change_name="users",
    committed_at=datetime.now(timezone.utc),
    committer_name="Test User",
    committer_email="test@example.com",
    planned_at=datetime.now(timezone.utc),
    planner_name="Test User",
    planner_email="test@example.com"
)
state.record_deploy(entry)

# Query state
all_entries = state.records()
```

---

## Notes for Library Users

1. **Import Stability**: Public APIs may change before v1.0. Pin specific versions.
2. **Testing**: Use `isolated_test_context()` from `tests.support.test_helpers` for isolated testing.
3. **Configuration**: Respect Sqitch precedence: CLI → environment → local → user → system.
4. **Registry Compatibility**: Registry schemas match Sqitch exactly; don't modify directly.
5. **Error Handling**: Most functions raise `ValueError` or custom exceptions on validation failures.

---

## Future API Plans

Post-1.0 enhancements:
- Stable versioned API with semantic versioning
- MySQL and PostgreSQL engine documentation
- Async/await support for concurrent deployments
- Plugin system for custom engines
- Webhook integrations for deployment notifications

---

## References

- **Module Source**: `sqlitch/` directory
- **Test Examples**: `tests/` directory
- **CLI Documentation**: Run `sqlitch --help` or `sqlitch <command> --help`
- **Architecture Docs**: `docs/architecture/`
- **Contributing Guide**: `CONTRIBUTING.md`
